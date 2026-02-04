#!/usr/bin/env python3
"""
Standalone Gold Tracker for Home Assistant Server
No external dependencies - uses only Python standard library

Usage:
    python3 standalone_analyzer.py              # Run once
    python3 standalone_analyzer.py --daemon     # Run as daemon (daily at 08:00)
"""

import json
import os
import sys
import time
import base64
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# Configuration - edit these or use environment variables
CONFIG = {
    "homeassistant": {
        "url": os.getenv("HA_URL", "http://127.0.0.1:8123"),
        "token": os.getenv("HA_TOKEN", ""),
        "device_name": os.getenv("HA_DEVICE", "my_oneplus")
    },
    "trading212": {
        "api_key": os.getenv("T212_API_KEY", ""),
        "api_secret": os.getenv("T212_API_SECRET", ""),
        "environment": os.getenv("T212_ENV", "live")
    },
    "goals": {
        "target_gold_grams": int(os.getenv("TARGET_GOLD", "100")),
        "target_date": os.getenv("TARGET_DATE", "2027-06-30"),
        "monthly_investment": int(os.getenv("MONTHLY_INVEST", "400"))
    },
    "thresholds": {
        "gold_price_drop_percent": 5,
        "gold_price_spike_percent": 10,
        "days_between_summary": 7
    }
}

STATE_FILE = Path(__file__).parent / ".analyzer_state.json"

CURRENCY_SYMBOLS = {
    "EUR": "\u20ac", "USD": "$", "GBP": "\u00a3", "CHF": "CHF ",
    "SEK": "kr", "NOK": "kr", "DKK": "kr", "PLN": "z\u0142",
    "CZK": "K\u010d", "RON": "lei ", "BGN": "лв", "HUF": "Ft",
}


class Trading212API:
    """Minimal Trading 212 API client using only stdlib."""

    def __init__(self, api_key: str, api_secret: str, environment: str = "live"):
        self.base_url = f"https://{environment}.trading212.com/api/v0"
        credentials = f"{api_key}:{api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 Trading212-MCP/1.0"
        }

    def _get(self, endpoint: str) -> dict:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"API error: {e}")
            return {}

    def get_account_info(self) -> dict:
        return self._get("/equity/account/info")

    def get_account_cash(self) -> dict:
        return self._get("/equity/account/cash")

    def get_pies(self) -> list:
        return self._get("/equity/pies")

    def get_pie(self, pie_id: int) -> dict:
        return self._get(f"/equity/pies/{pie_id}")

    def get_orders(self) -> list:
        """Fetch active orders (limit, stop, etc.)."""
        result = self._get("/equity/orders")
        return result if isinstance(result, list) else []


class HomeAssistantNotifier:
    """Send notifications via Home Assistant."""

    def __init__(self, url: str, token: str, device_name: str):
        self.url = url.rstrip("/")
        self.token = token
        self.device = device_name

    def send(self, title: str, message: str, extra: dict = None) -> bool:
        url = f"{self.url}/api/services/notify/mobile_app_{self.device}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {"title": title, "message": message}
        if extra:
            payload["data"] = extra
        data = json.dumps(payload).encode()

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent: {title}")
                return True
        except Exception as e:
            print(f"Notification error: {e}")
            return False


def get_gold_price_eur() -> float:
    """Get approximate gold price in EUR per gram."""
    try:
        # Use frankfurter for EUR/USD rate
        url = "https://api.frankfurter.app/latest?from=USD&to=EUR"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            eur_rate = data.get("rates", {}).get("EUR", 0.92)

        # Gold ~$4700/oz as of Feb 2026
        gold_usd_oz = 4700
        return (gold_usd_oz * eur_rate) / 31.1035
    except Exception as e:
        print(f"Gold price error: {e}")
        return 134.0  # Fallback


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_price": None, "last_summary": None, "price_history": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def run_analysis():
    """Run the gold tracking analysis."""
    print(f"\n{'='*50}")
    print(f"Gold Tracker - {datetime.now()}")
    print(f"{'='*50}\n")

    cfg = CONFIG
    state = load_state()

    # Initialize clients
    t212 = Trading212API(
        cfg["trading212"]["api_key"],
        cfg["trading212"]["api_secret"],
        cfg["trading212"]["environment"]
    )
    notifier = HomeAssistantNotifier(
        cfg["homeassistant"]["url"],
        cfg["homeassistant"]["token"],
        cfg["homeassistant"]["device_name"]
    )

    # Fetch account currency
    account_info = t212.get_account_info()
    currency_code = account_info.get("currencyCode", "EUR")
    sym = CURRENCY_SYMBOLS.get(currency_code, currency_code + " ")

    # Fetch all data
    gold_price = get_gold_price_eur()
    cash = t212.get_account_cash()
    orders = t212.get_orders()
    pies = t212.get_pies()

    # Account values (handle None from API)
    total_value = cash.get("total", 0) or 0
    free_cash = cash.get("free", 0) or 0
    invested = cash.get("invested", 0) or 0
    pie_cash = cash.get("pieCash", 0) or 0
    ppl = cash.get("ppl", 0) or 0

    # Get invested value and dividends from pies
    invested_from_pies = 0
    total_dividends = 0
    for pie in (pies if isinstance(pies, list) else []):
        result = pie.get("result") or {}
        invested_from_pies += result.get("priceAvgValue", 0) or 0
        div = pie.get("dividendDetails") or {}
        total_dividends += div.get("gained", 0) or 0

    # Determine display values
    # actual_invested: what's actually in instruments
    # pending_pie: cash sitting in pie, not yet bought
    actual_invested = invested_from_pies or invested
    pending_pie = pie_cash if (pie_cash > 0 and actual_invested == 0) else 0

    # Active orders (limit, stop, etc.)
    active_orders = [o for o in orders
                     if o.get("status") in ("NEW", "CONFIRMED", "UNCONFIRMED", "LOCAL")]
    orders_count = len(active_orders)
    orders_value = sum(
        o.get("value") or abs(o.get("quantity", 0)) * (o.get("limitPrice") or o.get("stopPrice") or 0)
        for o in active_orders
    )

    print(f"Gold Price: {sym}{gold_price:.2f}/gram")
    print(f"Account Total: {sym}{total_value:.2f}")
    print(f"  Invested: {sym}{actual_invested:.2f}")
    if pending_pie > 0:
        print(f"  Pending (pie): {sym}{pending_pie:.2f}")
    if orders_count > 0:
        print(f"  Active orders: {orders_count} ({sym}{orders_value:.2f})")
    if free_cash > 0:
        print(f"  Free cash: {sym}{free_cash:.2f}")

    # Calculate progress
    goals = cfg["goals"]
    target_grams = goals["target_gold_grams"]
    target_date = datetime.strptime(goals["target_date"], "%Y-%m-%d")
    monthly = goals["monthly_investment"]

    # Gold equivalents - only actually invested holdings count
    invested_grams = (actual_invested + ppl) / gold_price if actual_invested > 0 and gold_price > 0 else 0
    total_grams = invested_grams

    months_left = max(0, (target_date.year - datetime.now().year) * 12 +
                      (target_date.month - datetime.now().month))
    future_invest = months_left * monthly
    projected = total_grams + (future_invest / gold_price) if gold_price > 0 else total_grams

    # Gold vault progress (10 coins @ 10g each)
    pct = min(100, (total_grams / target_grams) * 100) if target_grams > 0 else 0
    filled = round(pct / 10)
    vault = "\U0001FA99" * filled + "\u26AB" * (10 - filled) + "\U0001F451"

    print(f"\n{vault}")
    print(f"   {total_grams:.1f}g \u2192 {target_grams}g ({pct:.1f}%)")
    print(f"Projected: {projected:.1f}g by {goals['target_date']}")

    # Track price history
    history = state.get("price_history", [])
    history.append({"date": datetime.now().isoformat(), "price": gold_price})
    history = history[-30:]  # Keep 30 days

    # Calculate 7-day change
    change_7d = 0
    if len(history) >= 7:
        old_price = history[-7]["price"]
        change_7d = ((gold_price - old_price) / old_price) * 100

    # Determine alerts
    alerts_sent = 0
    thresholds = cfg["thresholds"]

    # Gold buying opportunity
    if change_7d <= -thresholds["gold_price_drop_percent"]:
        msg = (f"Gold dropped {abs(change_7d):.1f}% to {sym}{gold_price:.2f}/g\n"
               f"Your {sym}{monthly} now buys {monthly/gold_price:.1f}g")
        if notifier.send("Gold Buying Opportunity", msg):
            alerts_sent += 1

    # Take profit signal
    elif change_7d >= thresholds["gold_price_spike_percent"]:
        msg = f"Gold up {change_7d:.1f}% to {sym}{gold_price:.2f}/g\nConsider risk/reward."
        if notifier.send("Consider Taking Profit", msg):
            alerts_sent += 1

    # Weekly summary
    last_summary = state.get("last_summary")
    should_summarize = (not last_summary or
                        (datetime.now() - datetime.fromisoformat(last_summary)).days >= 7)

    if should_summarize:
        status = "On track" if projected >= target_grams else "Behind target"

        lines = []

        # Total (mandatory)
        lines.append(f"Total: {sym}{total_value:.2f}")

        # Invested (mandatory)
        if actual_invested > 0:
            lines.append(f"Invested: {sym}{actual_invested:.2f} ({invested_grams:.1f}g)")
        else:
            lines.append(f"Invested: {sym}0.00")

        # Active orders (conditional)
        if orders_count > 0:
            lines.append(f"Active Orders: {orders_count}")

        # Pending (conditional)
        if pending_pie > 0:
            lines.append(f"Pending: {sym}{pending_pie:.2f}")

        # Show orders value only if it differs from pending
        if orders_count > 0 and abs(orders_value - pending_pie) > 1.0:
            lines.append(f"Orders Value: {sym}{orders_value:.2f}")

        # Free cash (conditional)
        if free_cash > 0:
            lines.append(f"Cash: {sym}{free_cash:.2f}")

        if ppl and round(ppl, 2) != 0:
            sign = "+" if ppl > 0 else ""
            lines.append(f"Return: {sign}{sym}{ppl:.2f}")
        if total_dividends > 0:
            lines.append(f"Dividends: {sym}{total_dividends:.2f}")

        # Gold price with daily change
        gold_line = f"Gold Price: {sym}{gold_price:.2f}/g"
        last_price = state.get("last_price")
        if last_price and last_price > 0:
            daily_chg = ((gold_price - last_price) / last_price) * 100
            arrow = "\u2191" if daily_chg >= 0 else "\u2193"
            gold_line += f" {arrow}{abs(daily_chg):.1f}%"
        lines.append(gold_line)
        lines.append("")
        lines.append(vault)
        lines.append(f"{total_grams:.1f}g \u2192 {target_grams}g ({pct:.1f}%)")

        msg = "\n".join(lines)
        if notifier.send(f"Weekly Gold Report - {status}", msg,
                         extra={"color": "#FFD700"}):
            alerts_sent += 1
            state["last_summary"] = datetime.now().isoformat()

    # Save state
    state["last_price"] = gold_price
    state["price_history"] = history
    save_state(state)

    print(f"\nAlerts sent: {alerts_sent}")
    print(f"{'='*50}\n")


def run_daemon(run_time: str = "08:00"):
    """Run as daemon, executing daily at specified time."""
    print(f"Daemon started - daily run at {run_time}")

    last_run_date = None
    while True:
        now = datetime.now()
        if now.strftime("%H:%M") >= run_time and now.date() != last_run_date:
            try:
                run_analysis()
                last_run_date = now.date()
            except Exception as e:
                print(f"Error: {e}")
        time.sleep(60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gold Tracker")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run as daemon")
    parser.add_argument("--time", "-t", default="08:00", help="Daily run time (HH:MM)")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(args.time)
    else:
        run_analysis()


if __name__ == "__main__":
    main()
