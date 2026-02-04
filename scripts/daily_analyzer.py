"""
Daily Portfolio Analyzer for Trading 212.

Analyzes your gold investment progress and sends alerts only when:
- Gold price drops significantly (buying opportunity)
- Gold price spikes (consider taking profit)
- Weekly summary of progress toward your goal
- Major market news affecting gold

Usage:
    # Run once (one-shot analysis)
    python daily_analyzer.py

    # Run as daemon (continuous, runs daily at 8 AM)
    python daily_analyzer.py --daemon

    # Run as daemon at custom time
    python daily_analyzer.py --daemon --time 09:30
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request
import urllib.error

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.client import Trading212Client

# Try to import notifiers - use whichever is configured
try:
    from ha_notifier import HomeAssistantNotifier, build_trading_notification
    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False

try:
    from email_notifier import EmailNotifier, build_alert_email
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False


class DailyAnalyzer:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "alert_config.json"

        with open(config_path) as f:
            self.config = json.load(f)

        self.state_file = Path(__file__).parent / ".analyzer_state.json"
        self.state = self._load_state()

        # Initialize Trading 212 client
        os.environ["TRADING212_API_KEY"] = self.config["trading212"]["api_key"]
        os.environ["TRADING212_API_SECRET"] = self.config["trading212"]["api_secret"]
        os.environ["ENVIRONMENT"] = self.config["trading212"]["environment"]

        self.client = Trading212Client()

        # Initialize notifier based on config
        self.notifier = None
        self.notifier_type = None

        if "homeassistant" in self.config and HA_AVAILABLE:
            self.notifier = HomeAssistantNotifier(self.config["homeassistant"])
            self.notifier_type = "homeassistant"
            print("Using Home Assistant notifications")
        elif "email" in self.config and EMAIL_AVAILABLE:
            self.notifier = EmailNotifier(self.config["email"])
            self.notifier_type = "email"
            print("Using email notifications")
        else:
            print("WARNING: No notification method configured!")

        self.goals = self.config["goals"]
        self.thresholds = self.config["alert_thresholds"]

    def _load_state(self) -> dict:
        """Load previous state from file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "last_gold_price": None,
            "last_alert_date": None,
            "last_summary_date": None,
            "price_history": [],
            "alerts_sent_today": 0
        }

    def _save_state(self):
        """Save current state to file."""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def get_gold_price_eur(self) -> float:
        """Fetch current gold price in EUR per gram from multiple sources."""

        # Try multiple APIs in order of preference
        apis = [
            self._fetch_from_frankfurter,
            self._fetch_from_goldpricez,
        ]

        for api_func in apis:
            try:
                price = api_func()
                if price and price > 0:
                    return price
            except Exception as e:
                print(f"API failed: {e}")
                continue

        # Fallback to last known price or estimate
        fallback = self.state.get("last_gold_price", 134.0)
        print(f"Using fallback gold price: EUR {fallback}/gram")
        return fallback

    def _fetch_from_frankfurter(self) -> float:
        """
        Approximate gold price using USD gold and EUR/USD exchange rate.
        Gold is ~$4700/oz as of Feb 2026.
        """
        try:
            # Get EUR/USD rate
            url = "https://api.frankfurter.app/latest?from=USD&to=EUR"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                eur_rate = data.get("rates", {}).get("EUR", 0.92)

            # Approximate gold price in USD per oz (update this periodically)
            gold_usd_per_oz = 4700  # ~$4700/oz as of Feb 2026
            gold_eur_per_oz = gold_usd_per_oz * eur_rate
            gold_eur_per_gram = gold_eur_per_oz / 31.1035
            return gold_eur_per_gram
        except Exception:
            return None

    def _fetch_from_goldpricez(self) -> float:
        """Fetch from goldpricez.com API."""
        try:
            url = "https://goldpricez.com/api/rates/currency/eur/measure/gram"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Extract gold price per gram in EUR
                return float(data.get("gold_gram", 0))
        except Exception:
            return None

    def get_portfolio_data(self) -> dict:
        """Fetch current portfolio data from Trading 212."""
        try:
            cash = self.client.get_account_cash()
            pies = self.client.get_pies()

            portfolio_value = cash.total if hasattr(cash, 'total') else 0
            pie_value = 0

            for pie in pies:
                pie_cash = pie.cash if hasattr(pie, 'cash') else 0
                pie_value += pie_cash

                # Get detailed pie info
                try:
                    detailed = self.client.get_pie_by_id(pie.id)
                    if detailed.instruments:
                        for inst in detailed.instruments:
                            if hasattr(inst, 'result') and inst.result:
                                pie_value += getattr(inst.result, 'priceAvgValue', 0)
                except Exception:
                    pass

            return {
                "total_value": portfolio_value,
                "pie_value": pie_value,
                "free_cash": getattr(cash, 'free', 0)
            }
        except Exception as e:
            print(f"Error fetching portfolio: {e}")
            return {"total_value": 0, "pie_value": 0, "free_cash": 0}

    def calculate_progress(self, gold_price: float, portfolio_value: float) -> dict:
        """Calculate progress toward gold accumulation goal."""
        target_grams = self.goals["target_gold_grams"]
        current_grams = self.goals["current_gold_grams"]
        target_date = datetime.strptime(self.goals["target_date"], "%Y-%m-%d")
        monthly_investment = self.goals["monthly_investment"]

        # Calculate equivalent gold from portfolio
        equivalent_grams = portfolio_value / gold_price if gold_price > 0 else 0
        total_grams = current_grams + equivalent_grams

        # Calculate months remaining
        today = datetime.now()
        months_remaining = max(0, (target_date.year - today.year) * 12 + (target_date.month - today.month))

        # Project future accumulation
        future_investment = months_remaining * monthly_investment
        projected_grams = total_grams + (future_investment / gold_price) if gold_price > 0 else total_grams

        # Calculate gap
        grams_needed = target_grams - current_grams
        gap = (grams_needed * gold_price) - portfolio_value - future_investment

        return {
            "target_grams": target_grams,
            "current_grams": current_grams,
            "equivalent_grams": equivalent_grams,
            "total_grams": total_grams,
            "months_remaining": months_remaining,
            "projected_grams": projected_grams,
            "gap_eur": max(0, gap),
            "on_track": projected_grams >= target_grams
        }

    def analyze_price_movement(self, current_price: float) -> dict:
        """Analyze gold price movement and determine if alert needed."""
        last_price = self.state.get("last_gold_price")
        price_history = self.state.get("price_history", [])

        # Add current price to history
        price_history.append({
            "date": datetime.now().isoformat(),
            "price": current_price
        })

        # Keep only last 30 days
        cutoff = datetime.now() - timedelta(days=30)
        price_history = [p for p in price_history
                        if datetime.fromisoformat(p["date"]) > cutoff]
        self.state["price_history"] = price_history

        result = {
            "current_price": current_price,
            "change_1d": 0,
            "change_7d": 0,
            "alert_type": None
        }

        if last_price:
            result["change_1d"] = ((current_price - last_price) / last_price) * 100

        # Calculate 7-day change
        if len(price_history) >= 7:
            week_ago_price = price_history[-7]["price"]
            result["change_7d"] = ((current_price - week_ago_price) / week_ago_price) * 100

        # Determine if alert needed
        drop_threshold = self.thresholds["gold_price_drop_percent"]
        spike_threshold = self.thresholds["gold_price_spike_percent"]

        if result["change_7d"] <= -drop_threshold:
            result["alert_type"] = "gold_opportunity"
        elif result["change_7d"] >= spike_threshold:
            result["alert_type"] = "take_profit"

        self.state["last_gold_price"] = current_price
        return result

    def should_send_summary(self) -> bool:
        """Check if weekly summary should be sent."""
        last_summary = self.state.get("last_summary_date")
        if not last_summary:
            return True

        last_date = datetime.fromisoformat(last_summary)
        days_since = (datetime.now() - last_date).days
        return days_since >= self.thresholds["days_between_summary"]

    def _send_notification(self, alert_type: str, data: dict) -> bool:
        """Send notification using configured notifier."""
        if not self.notifier:
            print("No notifier configured!")
            return False

        if self.notifier_type == "homeassistant":
            title, message, extra = build_trading_notification(alert_type, data)
            return self.notifier.send_alert(title, message, extra)
        elif self.notifier_type == "email":
            subject, html = build_alert_email(alert_type, data)
            return self.notifier.send_alert(subject, html)
        return False

    def run(self):
        """Run the daily analysis."""
        print(f"\n{'='*50}")
        print(f"Trading 212 Daily Analyzer - {datetime.now()}")
        print(f"{'='*50}\n")

        # Get current data
        gold_price = self.get_gold_price_eur()
        portfolio = self.get_portfolio_data()

        print(f"Gold Price: EUR {gold_price:.2f}/gram")
        print(f"Portfolio Value: EUR {portfolio['total_value']:.2f}")

        # Analyze price movement
        price_analysis = self.analyze_price_movement(gold_price)
        print(f"1-day change: {price_analysis['change_1d']:+.2f}%")
        print(f"7-day change: {price_analysis['change_7d']:+.2f}%")

        # Calculate progress
        progress = self.calculate_progress(gold_price, portfolio['pie_value'])
        print(f"\nGold Progress: {progress['total_grams']:.2f}g / {progress['target_grams']}g")
        print(f"Months remaining: {progress['months_remaining']}")
        print(f"Projected at target: {progress['projected_grams']:.1f}g")
        print(f"On track: {'Yes' if progress['on_track'] else 'No'}")

        alerts_sent = 0

        # Send price alert if needed
        if price_analysis["alert_type"] == "gold_opportunity":
            data = {
                "current_price": gold_price,
                "drop_percent": abs(price_analysis["change_7d"]),
                "grams_per_400": 400 / gold_price,
                "current_grams": progress["current_grams"],
                "target_grams": progress["target_grams"]
            }
            if self._send_notification("gold_opportunity", data):
                alerts_sent += 1
                print("\n[SENT] Gold buying opportunity alert")

        elif price_analysis["alert_type"] == "take_profit":
            data = {
                "current_price": gold_price,
                "gain_percent": price_analysis["change_7d"],
                "reason": "Gold has risen significantly in the past week. Consider if the risk/reward still favors holding."
            }
            if self._send_notification("take_profit", data):
                alerts_sent += 1
                print("\n[SENT] Take profit alert")

        # Send weekly summary if due
        if self.should_send_summary():
            projection_note = ""
            on_track = progress["on_track"]
            if on_track:
                projection_note = "You're on track to meet your goal!"
            else:
                gap_grams = progress["target_grams"] - progress["projected_grams"]
                extra_monthly = (gap_grams * gold_price) / max(1, progress["months_remaining"])
                projection_note = f"You're about {gap_grams:.1f}g short. Consider increasing monthly investment by EUR {extra_monthly:.0f}."

            data = {
                "current_grams": progress["current_grams"],
                "target_grams": progress["target_grams"],
                "portfolio_value": portfolio["pie_value"],
                "current_price": gold_price,
                "weekly_change": price_analysis["change_7d"],
                "equivalent_grams": progress["equivalent_grams"],
                "target_date": self.goals["target_date"],
                "months_remaining": progress["months_remaining"],
                "projected_grams": progress["projected_grams"],
                "projection_note": projection_note,
                "on_track": on_track
            }
            if self._send_notification("weekly_summary", data):
                alerts_sent += 1
                self.state["last_summary_date"] = datetime.now().isoformat()
                print("\n[SENT] Weekly summary")

        # Save state
        self.state["last_alert_date"] = datetime.now().isoformat()
        self.state["alerts_sent_today"] = alerts_sent
        self._save_state()

        print(f"\n{'='*50}")
        print(f"Analysis complete. Alerts sent: {alerts_sent}")
        print(f"{'='*50}\n")

        return alerts_sent


def run_once():
    """Run analysis once and exit."""
    config_path = Path(__file__).parent / "alert_config.json"

    if not config_path.exists():
        print("ERROR: alert_config.json not found!")
        print("Copy alert_config.example.json to alert_config.json and fill in your details.")
        sys.exit(1)

    analyzer = DailyAnalyzer(str(config_path))
    return analyzer.run()


def run_daemon(run_time: str = "08:00"):
    """
    Run as a daemon, executing analysis daily at specified time.

    Args:
        run_time: Time to run daily analysis in HH:MM format (24h)
    """
    import time

    config_path = Path(__file__).parent / "alert_config.json"
    if not config_path.exists():
        print("ERROR: alert_config.json not found!")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"Trading 212 Analyzer Daemon Started")
    print(f"Scheduled daily run at: {run_time}")
    print(f"{'='*50}\n")

    # Send startup notification
    analyzer = DailyAnalyzer(str(config_path))
    if analyzer.notifier:
        analyzer.notifier.send_alert(
            "Gold Tracker Started",
            f"Daily analysis scheduled at {run_time}",
            {"group": "trading", "tag": "startup"}
        )

    last_run_date = None

    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.date()

        # Check if it's time to run and we haven't run today
        if current_time >= run_time and last_run_date != current_date:
            print(f"\n[{now}] Running scheduled analysis...")
            try:
                analyzer = DailyAnalyzer(str(config_path))
                analyzer.run()
                last_run_date = current_date
            except Exception as e:
                print(f"Error during analysis: {e}")
                # Try to notify about the error
                if analyzer.notifier:
                    analyzer.notifier.send_alert(
                        "Gold Tracker Error",
                        f"Analysis failed: {str(e)[:100]}",
                        {"group": "trading", "tag": "error", "color": "#ef4444"}
                    )

        # Sleep for 1 minute before checking again
        time.sleep(60)


def main():
    """Main entry point with argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Trading 212 Gold Tracker - Daily Portfolio Analyzer"
    )
    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Run as daemon (continuous background service)"
    )
    parser.add_argument(
        "--time", "-t",
        default="08:00",
        help="Time to run daily analysis in HH:MM format (default: 08:00)"
    )

    args = parser.parse_args()

    if args.daemon:
        run_daemon(args.time)
    else:
        run_once()


if __name__ == "__main__":
    main()
