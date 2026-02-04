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
import xml.etree.ElementTree as ET
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
    },
    "ai_analyst": {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "fred_api_key": os.getenv("FRED_API_KEY", ""),
        "finnhub_api_key": os.getenv("FINNHUB_API_KEY", ""),
        "enabled": os.getenv("AI_ANALYST_ENABLED", "true").lower() == "true",
    }
}

STATE_FILE = Path(__file__).parent / ".analyzer_state.json"

CURRENCY_SYMBOLS = {
    "EUR": "\u20ac", "USD": "$", "GBP": "\u00a3", "CHF": "CHF ",
    "SEK": "kr", "NOK": "kr", "DKK": "kr", "PLN": "z\u0142",
    "CZK": "K\u010d", "RON": "lei ", "BGN": "лв", "HUF": "Ft",
}


def calculate_technicals(prices: list) -> dict:
    """Calculate SMA(50), SMA(200), RSI(14) from a list of closing prices.

    Args:
        prices: List of floats (closing prices), ordered oldest-first.

    Returns:
        dict with sma_50, sma_200, rsi_14, price_vs_sma50, price_vs_sma200,
        golden_cross, trend. None values for indicators with insufficient data.
    """
    result = {
        "sma_50": None, "sma_200": None, "rsi_14": None,
        "price_vs_sma50": None, "price_vs_sma200": None,
        "golden_cross": None, "trend": None,
    }
    if not prices or len(prices) < 2:
        return result

    current = prices[-1]

    # SMA
    if len(prices) >= 50:
        result["sma_50"] = sum(prices[-50:]) / 50
        result["price_vs_sma50"] = ((current - result["sma_50"]) / result["sma_50"]) * 100
    if len(prices) >= 200:
        result["sma_200"] = sum(prices[-200:]) / 200
        result["price_vs_sma200"] = ((current - result["sma_200"]) / result["sma_200"]) * 100

    if result["sma_50"] is not None and result["sma_200"] is not None:
        result["golden_cross"] = result["sma_50"] > result["sma_200"]
        if current > result["sma_50"] > result["sma_200"]:
            result["trend"] = "bullish"
        elif current < result["sma_50"] < result["sma_200"]:
            result["trend"] = "bearish"
        else:
            result["trend"] = "neutral"

    # RSI (Wilder's smoothing)
    if len(prices) >= 15:
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        period = 14
        gains = [max(0, d) for d in deltas[:period]]
        losses = [abs(min(0, d)) for d in deltas[:period]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        for d in deltas[period:]:
            avg_gain = (avg_gain * (period - 1) + max(0, d)) / period
            avg_loss = (avg_loss * (period - 1) + abs(min(0, d))) / period
        if avg_loss == 0:
            result["rsi_14"] = 100.0
        else:
            rs = avg_gain / avg_loss
            result["rsi_14"] = 100 - (100 / (1 + rs))

    return result


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

    def write_html_report(self, portfolio: dict, ai_text: str = "",
                          grams: float = 0, target: float = 100, pct: float = 0,
                          projection: str = "") -> bool:
        """Write the full report as an HTML file served by HA at /local/gold_tracker.html."""
        html_path = Path("/config/www/gold_tracker.html")
        html_path.parent.mkdir(parents=True, exist_ok=True)

        now = datetime.now().strftime("%A, %d %B %Y at %H:%M")

        # Build portfolio rows
        rows = ""
        for label, value in portfolio.get("rows", []):
            rows += f"<tr><td>{label}</td><td>{value}</td></tr>\n"

        # Escape AI text for HTML
        ai_html = ""
        if ai_text:
            ai_escaped = ai_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            ai_escaped = ai_escaped.replace("\u2022", "&#8226;").replace("\u2192", "&#8594;")
            ai_html = f"""
    <div class="section">
        <h2>&#128202; AI Market Analysis</h2>
        <pre>{ai_escaped}</pre>
    </div>"""

        # Clamp percentage for bar width
        bar_pct = min(pct, 100)
        fox_end = min(max(bar_pct - 12, -5), 72)
        arrived = " arrived" if bar_pct >= 100 else ""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gold Tracker Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 20px; }}
  .container {{ max-width: 600px; margin: 0 auto; }}
  h1 {{ color: #ffd700; font-size: 1.4em; margin-bottom: 4px; }}
  .date {{ color: #888; font-size: 0.85em; margin-bottom: 20px; }}
  .section {{ background: #16213e; border-radius: 12px; padding: 16px; margin-bottom: 16px; }}
  h2 {{ color: #ffd700; font-size: 1.1em; margin-bottom: 12px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 8px 4px; border-bottom: 1px solid #1a1a2e; }}
  td:first-child {{ color: #aaa; }}
  td:last-child {{ text-align: right; font-weight: 600; }}
  pre {{ white-space: pre-wrap; word-wrap: break-word; font-family: inherit; line-height: 1.6; color: #ccc; }}

  /* ============ 3D VAULT PROGRESS BAR ============ */
  .progress-scene {{ position: relative; padding: 60px 0 8px; }}
  .vault-frame {{
    position: relative; height: 36px; border-radius: 8px;
    background: linear-gradient(180deg, #5a4a2a 0%, #3d2e14 40%, #2a1f0a 100%);
    box-shadow: 0 2px 8px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,215,0,.15), 0 0 20px rgba(255,215,0,.05);
    padding: 3px; margin: 0 0 8px; overflow: visible;
  }}
  .vault-inner {{
    position: relative; height: 100%; border-radius: 5px;
    background: linear-gradient(180deg, #0a0a14 0%, #141428 50%, #0d0d1a 100%);
    box-shadow: inset 0 3px 8px rgba(0,0,0,.8), inset 0 -1px 3px rgba(0,0,0,.4);
    overflow: hidden;
  }}
  .vault-fill {{
    position: absolute; top: 0; left: 0; height: 100%; border-radius: 5px;
    background:
      radial-gradient(circle 6px at 8px 10px, rgba(255,235,100,.4) 0%, transparent 100%),
      radial-gradient(circle 5px at 22px 18px, rgba(255,235,100,.3) 0%, transparent 100%),
      radial-gradient(circle 7px at 40px 8px, rgba(255,235,100,.35) 0%, transparent 100%),
      radial-gradient(circle 5px at 55px 20px, rgba(255,235,100,.3) 0%, transparent 100%),
      radial-gradient(circle 6px at 70px 12px, rgba(255,235,100,.35) 0%, transparent 100%),
      radial-gradient(circle 5px at 85px 6px, rgba(255,235,100,.25) 0%, transparent 100%),
      linear-gradient(180deg, #ffed6a 0%, #ffd700 15%, #e6ac00 35%, #cc9900 50%, #b8860b 65%, #daa520 80%, #ffd700 95%, #ffed6a 100%);
    box-shadow: inset 0 2px 4px rgba(255,255,200,.5), inset 0 -2px 6px rgba(139,101,8,.6), 0 0 12px rgba(255,215,0,.3);
    animation: vaultFill 2.2s cubic-bezier(.25,.1,.25,1) forwards;
  }}
  .vault-fill::after {{
    content: ''; position: absolute; top: 0; left: -60px; width: 60px; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent);
    animation: vaultGlint 3s ease-in-out infinite 2.5s;
  }}
  @keyframes vaultFill {{ from {{ width: 0%; }} to {{ width: var(--fill-pct, 4%); }} }}
  @keyframes vaultGlint {{ 0% {{ left: -60px; }} 50% {{ left: calc(100% + 60px); }} 50.01%,100% {{ left: -60px; }} }}

  /* Rivets */
  .vault-frame::before, .vault-frame::after {{
    content: ''; position: absolute; width: 8px; height: 8px; border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #c9a84c, #5a4a2a);
    box-shadow: inset 0 1px 2px rgba(255,215,0,.4), 0 1px 2px rgba(0,0,0,.5);
    top: 50%; transform: translateY(-50%); z-index: 5;
  }}
  .vault-frame::before {{ left: 6px; }}
  .vault-frame::after {{ right: 6px; }}

  /* Spilling coins — fall inward (left), never past bar edge */
  .coin-spill-anchor {{
    position: absolute; top: 50%; z-index: 4;
    animation: spillAnchor 2.2s cubic-bezier(.25,.1,.25,1) forwards;
  }}
  @keyframes spillAnchor {{ from {{ left: 0%; }} to {{ left: var(--fill-pct, 4%); }} }}
  .spill-coin {{
    position: absolute; width: 7px; height: 7px; border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #ffed6a, #daa520, #b8860b);
    box-shadow: 0 1px 2px rgba(0,0,0,.5), inset 0 1px 1px rgba(255,255,200,.4);
    opacity: 0;
  }}
  .spill-coin:nth-child(1) {{ animation: coinPop 2.8s ease-out infinite 2.6s; top: -3px; left: -4px; }}
  .spill-coin:nth-child(2) {{ animation: coinPop 2.8s ease-out infinite 3.4s; top: 1px; left: -1px; }}
  .spill-coin:nth-child(3) {{ animation: coinPop 2.8s ease-out infinite 4.2s; top: -5px; left: -6px; }}
  .spill-coin:nth-child(4) {{ animation: coinPop 2.8s ease-out infinite 3.0s; top: 3px; left: -3px; }}
  .spill-coin:nth-child(5) {{ animation: coinPop 2.8s ease-out infinite 3.8s; top: -1px; left: -5px; }}
  @keyframes coinPop {{
    0%   {{ opacity: .9; transform: translate(0, 0) scale(1) rotate(0deg); }}
    20%  {{ opacity: .9; transform: translate(-2px, -12px) scale(1) rotate(40deg); }}
    60%  {{ opacity: .6; transform: translate(-6px, 2px) scale(.8) rotate(120deg); }}
    100% {{ opacity: 0; transform: translate(-8px, 14px) scale(.4) rotate(200deg); }}
  }}

  /* At 100%: coins burst out of the bank gate */
  .arrived ~ .coin-spill-anchor {{
    animation: none;
    left: auto; right: 10px; top: -18px;
    z-index: 10;
  }}
  .arrived ~ .coin-spill-anchor .spill-coin {{
    animation-name: coinBurst;
    width: 8px; height: 8px;
  }}
  @keyframes coinBurst {{
    0%   {{ opacity: 1; transform: translate(0, 0) scale(.8); }}
    30%  {{ opacity: 1; transform: translate(var(--cx), var(--cy)) scale(1.1); }}
    100% {{ opacity: 0; transform: translate(var(--cx2), var(--cy2)) scale(.4); }}
  }}
  .arrived ~ .coin-spill-anchor .spill-coin:nth-child(1) {{ --cx:-8px; --cy:-14px; --cx2:-12px; --cy2:8px; }}
  .arrived ~ .coin-spill-anchor .spill-coin:nth-child(2) {{ --cx:6px; --cy:-12px; --cx2:10px; --cy2:10px; }}
  .arrived ~ .coin-spill-anchor .spill-coin:nth-child(3) {{ --cx:-4px; --cy:-18px; --cx2:-6px; --cy2:6px; }}
  .arrived ~ .coin-spill-anchor .spill-coin:nth-child(4) {{ --cx:2px; --cy:-16px; --cx2:8px; --cy2:12px; }}
  .arrived ~ .coin-spill-anchor .spill-coin:nth-child(5) {{ --cx:-10px; --cy:-10px; --cx2:-14px; --cy2:4px; }}

  .bar-label {{
    position: absolute; width: 100%; text-align: center; line-height: 30px;
    font-weight: 700; font-size: 0.8em; color: #fff;
    text-shadow: 0 1px 4px rgba(0,0,0,.9), 0 0 8px rgba(0,0,0,.5); z-index: 3;
  }}

  /* ====== KYUBI FOX ====== */
  .kyubi-fox {{
    position: absolute; bottom: 100%; z-index: 6;
    margin-bottom: 2px;
    animation: kyubiWalk 2.2s cubic-bezier(.25,.1,.25,1) forwards;
  }}
  @keyframes kyubiWalk {{ from {{ left: -12%; }} to {{ left: var(--fox-end, 0%); }} }}
  .kyubi-fox .fox-run {{
    width: 85px; height: auto;
    filter: drop-shadow(0 2px 8px rgba(0,255,200,.3));
  }}
  .kyubi-fox .fox-face {{
    display: none; width: 55px; height: 55px;
    filter: drop-shadow(0 0 12px rgba(0,255,200,.5));
    animation: faceBounce 1.5s ease-in-out infinite;
  }}
  @keyframes faceBounce {{
    0%,100% {{ transform: translateY(0) scale(1); }}
    50% {{ transform: translateY(-5px) scale(1.03); }}
  }}
  .kyubi-fox.arrived .fox-run {{ display: none; }}
  .kyubi-fox.arrived .fox-face {{ display: block; }}

  .sparkle {{ position: absolute; opacity: 0; }}
  .kyubi-fox.arrived .sparkle {{ animation: sparkle 2s ease-in-out infinite; }}
  .sparkle:nth-child(3) {{ top: -8px; left: 10px; animation-delay: 0s; }}
  .sparkle:nth-child(4) {{ top: 2px; right: -6px; animation-delay: 0.7s; }}
  .sparkle:nth-child(5) {{ bottom: 4px; left: -4px; animation-delay: 1.3s; }}
  @keyframes sparkle {{
    0%,100% {{ opacity: 0; transform: scale(.5); }}
    50% {{ opacity: 1; transform: scale(1.2); }}
  }}

  .vault-door {{
    position: absolute; right: -4px; top: -34px; z-index: 5;
    font-size: 1.5em;
    filter: drop-shadow(0 0 10px rgba(255,215,0,.3));
    animation: doorGlow 3s ease-in-out infinite;
  }}
  @keyframes doorGlow {{
    0%,100% {{ filter: drop-shadow(0 0 8px rgba(255,215,0,.2)); transform: scale(1); }}
    50% {{ filter: drop-shadow(0 0 16px rgba(255,215,0,.5)); transform: scale(1.05); }}
  }}

  .bar-ends {{ display: flex; justify-content: space-between; font-size: 0.8em; color: #888; }}
  .bar-ends .current {{ color: #ffd700; font-weight: 600; }}
  .projection {{ text-align: center; color: #888; font-size: 0.85em; margin-top: 10px; }}

  .t212-btn {{ display: block; text-align: center; background: linear-gradient(135deg, #ffd700, #f0c000);
              color: #1a1a2e; padding: 14px; border-radius: 12px; font-weight: 700; text-decoration: none;
              font-size: 1.05em; margin-top: 16px; box-shadow: 0 4px 15px rgba(255,215,0,.3);
              transition: transform .15s, box-shadow .15s; }}
  .t212-btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255,215,0,.4); }}
  .t212-btn:active {{ transform: translateY(0); }}
</style>
</head>
<body>
<div class="container">
    <h1>&#x1FA99; Gold Tracker</h1>
    <p class="date">{now}</p>

    <div class="section">
        <h2>Portfolio</h2>
        <table>{rows}</table>
    </div>
{ai_html}
    <div class="section">
        <h2 style="text-align:center">Progress to {target:.0f}g</h2>
        <div class="progress-scene" style="--fill-pct:{bar_pct}%; --fox-end:{fox_end}%;">
            <div class="vault-frame">
                <div class="kyubi-fox{arrived}">
                    <img class="fox-run" src="/local/kyubi_fox.gif" alt="Kyubi">
                    <svg class="fox-face" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                      <defs>
                        <filter id="glow">
                          <feGaussianBlur stdDeviation="3" result="blur"/>
                          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                        </filter>
                        <radialGradient id="faceGrad" cx="50%" cy="45%" r="50%">
                          <stop offset="0%" stop-color="#33ffcc" stop-opacity=".9"/>
                          <stop offset="60%" stop-color="#00ddaa" stop-opacity=".8"/>
                          <stop offset="100%" stop-color="#009988" stop-opacity=".6"/>
                        </radialGradient>
                      </defs>
                      <ellipse cx="50" cy="55" rx="32" ry="30" fill="url(#faceGrad)" filter="url(#glow)" stroke="#66ffdd" stroke-width="1.5"/>
                      <polygon points="22,38 10,8 35,30" fill="#00ccaa" filter="url(#glow)" stroke="#66ffdd" stroke-width="1"/>
                      <polygon points="24,35 16,14 33,30" fill="#115544" opacity=".5"/>
                      <polygon points="78,38 90,8 65,30" fill="#00ccaa" filter="url(#glow)" stroke="#66ffdd" stroke-width="1"/>
                      <polygon points="76,35 84,14 67,30" fill="#115544" opacity=".5"/>
                      <path d="M34,48 Q38,42 42,48" stroke="#ffffff" stroke-width="2.5" fill="none" stroke-linecap="round"/>
                      <path d="M58,48 Q62,42 66,48" stroke="#ffffff" stroke-width="2.5" fill="none" stroke-linecap="round"/>
                      <ellipse cx="50" cy="58" rx="4" ry="3" fill="#115544"/>
                      <ellipse cx="50" cy="57.5" rx="3" ry="2" fill="#44ffcc" opacity=".6"/>
                      <path d="M44,63 Q50,69 56,63" stroke="#115544" stroke-width="1.5" fill="none" stroke-linecap="round"/>
                      <line x1="26" y1="54" x2="20" y2="52" stroke="#66ffdd" stroke-width="1" opacity=".5"/>
                      <line x1="26" y1="57" x2="20" y2="56" stroke="#66ffdd" stroke-width="1" opacity=".5"/>
                      <line x1="74" y1="54" x2="80" y2="52" stroke="#66ffdd" stroke-width="1" opacity=".5"/>
                      <line x1="74" y1="57" x2="80" y2="56" stroke="#66ffdd" stroke-width="1" opacity=".5"/>
                      <path d="M45,38 L50,33 L55,38" stroke="#aaffee" stroke-width="1" fill="none" opacity=".6"/>
                    </svg>
                    <span class="sparkle" style="font-size:10px">&#10022;</span>
                    <span class="sparkle" style="font-size:8px;color:#ffd700">&#10022;</span>
                    <span class="sparkle" style="font-size:9px;color:#66ffdd">&#10022;</span>
                </div>
                <div class="vault-inner">
                    <div class="bar-label">{pct:.1f}%</div>
                    <div class="vault-fill"></div>
                </div>
                <div class="coin-spill-anchor">
                    <span class="spill-coin"></span>
                    <span class="spill-coin"></span>
                    <span class="spill-coin"></span>
                    <span class="spill-coin"></span>
                    <span class="spill-coin"></span>
                </div>
                <div class="vault-door">&#x1F3E6;</div>
            </div>
        </div>
        <div class="bar-ends">
            <span class="current">{grams:.1f}g</span>
            <span>&#x1F451; {target:.0f}g</span>
        </div>
        <div class="projection">{projection}</div>
    </div>

    <a class="t212-btn" id="t212-link" href="https://app.trading212.com/">Open Trading 212 &#8594;</a>
</div>
<script>
if (/Android|iPhone|iPad/i.test(navigator.userAgent)) {{
    document.getElementById('t212-link').href = 'app://com.avuscapital.trading212';
}}
</script>
</body>
</html>"""

        try:
            html_path.write_text(html, encoding="utf-8")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Report written: {html_path}")
            return True
        except Exception as e:
            print(f"HTML report error: {e}")
            return False


class MarketDataCollector:
    """Fetches market data from free external APIs. All stdlib, no dependencies."""

    def __init__(self, fred_api_key: str = "", finnhub_api_key: str = ""):
        self.fred_key = fred_api_key
        self.finnhub_key = finnhub_api_key
        self._timeout = 15

    def _fetch_url(self, url: str, headers: dict = None) -> bytes:
        """Fetch raw bytes from URL. Returns None on failure."""
        hdrs = {"User-Agent": "Mozilla/5.0 GoldTracker/1.0"}
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.read()
        except Exception as e:
            print(f"  Fetch error ({url[:60]}...): {e}")
            return None

    def _fetch_json(self, url: str, headers: dict = None) -> dict:
        data = self._fetch_url(url, headers)
        if data:
            try:
                return json.loads(data.decode())
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"  JSON parse error: {e}")
        return None

    def _fetch_xml(self, url: str) -> ET.Element:
        data = self._fetch_url(url)
        if data:
            try:
                return ET.fromstring(data)
            except ET.ParseError as e:
                print(f"  XML parse error: {e}")
        return None

    def _fred_latest(self, series_id: str) -> float:
        """Get the most recent value from a FRED series."""
        if not self.fred_key:
            return None
        url = (f"https://api.stlouisfed.org/fred/series/observations"
               f"?series_id={series_id}&api_key={self.fred_key}"
               f"&file_type=json&sort_order=desc&limit=5")
        data = self._fetch_json(url)
        if data and "observations" in data:
            for obs in data["observations"]:
                if obs.get("value", ".") != ".":
                    try:
                        return float(obs["value"])
                    except (ValueError, TypeError):
                        pass
        return None

    def fetch_gold_price_history(self) -> list:
        """Get 250+ trading days of gold prices from FRED for technical analysis."""
        if not self.fred_key:
            return None
        start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        url = (f"https://api.stlouisfed.org/fred/series/observations"
               f"?series_id=NASDAQQGLDI&api_key={self.fred_key}"
               f"&file_type=json&sort_order=asc&observation_start={start}")
        data = self._fetch_json(url)
        if not data or "observations" not in data:
            return None
        prices = []
        for obs in data["observations"]:
            if obs.get("value", ".") != ".":
                try:
                    prices.append({"date": obs["date"], "close": float(obs["value"])})
                except (ValueError, TypeError):
                    pass
        return prices if len(prices) >= 15 else None

    def fetch_macro_indicators(self) -> dict:
        """Fetch DXY, 10Y yield, VIX from FRED."""
        if not self.fred_key:
            return None
        series = {
            "dxy": "DTWEXBGS",
            "us10y": "DGS10",
            "vix": "VIXCLS",
        }
        result = {}
        for key, sid in series.items():
            val = self._fred_latest(sid)
            if val is not None:
                result[key] = val
        return result if result else None

    def fetch_fear_greed(self) -> dict:
        """Fetch CNN Fear & Greed Index."""
        data = self._fetch_json(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://www.cnn.com/markets/fear-and-greed",
            },
        )
        if data and "fear_and_greed" in data:
            fg = data["fear_and_greed"]
            return {
                "score": round(fg.get("score", 0)),
                "rating": fg.get("rating", "Unknown"),
                "previous_close": round(fg.get("previous_close", 0)),
            }
        return None

    def fetch_gold_news(self) -> list:
        """Fetch gold news from GoldBroker RSS + Google News RSS."""
        items = []

        # GoldBroker — gold-specific journalism
        root = self._fetch_xml("https://goldbroker.com/news.rss")
        if root is not None:
            for item in root.findall(".//item")[:3]:
                title = (item.findtext("title") or "").strip()
                if title:
                    items.append({"title": title, "source": "GoldBroker"})

        # Google News — broader/breaking gold news
        root = self._fetch_xml(
            "https://news.google.com/rss/search?q=gold+price+market&hl=en&gl=US&ceid=US:en"
        )
        if root is not None:
            for item in root.findall(".//item")[:3]:
                title = (item.findtext("title") or "").strip()
                if title:
                    items.append({"title": title, "source": "Google News"})

        return items if items else None

    def fetch_economic_calendar(self) -> list:
        """Fetch upcoming economic releases from FRED (uses same FRED key)."""
        if not self.fred_key:
            return None
        url = (f"https://api.stlouisfed.org/fred/releases/dates"
               f"?api_key={self.fred_key}&file_type=json"
               f"&include_release_dates_with_no_data=false&limit=50")
        data = self._fetch_json(url)
        if not data:
            return None

        releases = data.get("release_dates", [])
        keywords = ("FOMC", "CPI", "Employment", "Non-Farm", "Unemployment",
                     "GDP", "PCE", "PPI", "Fed", "Interest Rate", "Inflation",
                     "Consumer Price", "Producer Price", "Retail Sales")
        filtered = []
        for rel in releases:
            name = rel.get("release_name", "")
            if any(kw.lower() in name.lower() for kw in keywords):
                filtered.append({
                    "event": name,
                    "date": rel.get("date", ""),
                    "impact": "high",
                })
            if len(filtered) >= 5:
                break
        return filtered if filtered else None

    def collect_all(self) -> dict:
        """Orchestrate all data fetches. Returns dict with None for failed sources."""
        result = {
            "gold_history": None, "technicals": None, "macro": None,
            "fear_greed": None, "news": None, "calendar": None, "errors": [],
        }

        print("  Fetching market data...")

        history = self.fetch_gold_price_history()
        if history:
            result["gold_history"] = history
            closes = [p["close"] for p in history]
            result["technicals"] = calculate_technicals(closes)
            print(f"    Gold history: {len(history)} data points")
        else:
            result["errors"].append("gold_history")
            print("    Gold history: unavailable")

        macro = self.fetch_macro_indicators()
        if macro:
            result["macro"] = macro
            print(f"    Macro: DXY={macro.get('dxy')}, 10Y={macro.get('us10y')}, VIX={macro.get('vix')}")
        else:
            result["errors"].append("macro")
            print("    Macro: unavailable")

        fg = self.fetch_fear_greed()
        if fg:
            result["fear_greed"] = fg
            print(f"    Fear & Greed: {fg['score']} ({fg['rating']})")
        else:
            result["errors"].append("fear_greed")
            print("    Fear & Greed: unavailable")

        news = self.fetch_gold_news()
        if news:
            result["news"] = news
            print(f"    News: {len(news)} headlines")
        else:
            result["errors"].append("news")
            print("    News: unavailable")

        cal = self.fetch_economic_calendar()
        if cal:
            result["calendar"] = cal
            print(f"    Calendar: {len(cal)} upcoming events")
        else:
            result["errors"].append("calendar")
            print("    Calendar: unavailable")

        return result


class AIAnalyst:
    """Calls Claude Haiku API for gold investment analysis. Stdlib only."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-opus-4-20250514"
        self.max_tokens = 500

    def _build_prompt(self, market_data: dict, portfolio: dict) -> tuple:
        """Build system prompt and user message from collected data."""
        sym = portfolio.get("sym", "\u20ac")
        system = (
            "You are a gold investment analyst for a European investor "
            "accumulating physical gold via an ETF (iShares Physical Gold ETC). "
            "Give concise, actionable analysis. No markdown formatting — "
            "use plain text with line breaks, bullets (•), and arrows (→). "
            "Keep response under 250 words."
        )

        sections = []

        # Portfolio context (always available)
        sections.append(
            f"## Current Portfolio\n"
            f"- Invested: {sym}{portfolio['invested']:.2f} ({portfolio['grams']:.1f}g)\n"
            f"- Goal: {portfolio['target_grams']}g by {portfolio['target_date']} "
            f"({portfolio['months_left']} months left)\n"
            f"- Progress: {portfolio['pct']:.1f}%\n"
            f"- Monthly SIP: {sym}{portfolio['monthly']}\n"
            f"- Current P&L: {sym}{portfolio.get('ppl', 0):.2f}"
        )

        # Gold price + technicals
        tech = market_data.get("technicals")
        history = market_data.get("gold_history")
        if history:
            current_usd = history[-1]["close"]
            gold_section = f"## Gold Price\n- Current: ${current_usd:.2f}/oz (approx {sym}{portfolio['gold_price_eur']:.2f}/g)"
            if tech:
                if tech["sma_50"] is not None:
                    gold_section += f"\n- SMA(50): ${tech['sma_50']:.2f} ({tech['price_vs_sma50']:+.1f}%)"
                if tech["sma_200"] is not None:
                    gold_section += f"\n- SMA(200): ${tech['sma_200']:.2f} ({tech['price_vs_sma200']:+.1f}%)"
                if tech["rsi_14"] is not None:
                    rsi_label = ""
                    if tech["rsi_14"] > 70:
                        rsi_label = " (overbought)"
                    elif tech["rsi_14"] < 30:
                        rsi_label = " (oversold)"
                    gold_section += f"\n- RSI(14): {tech['rsi_14']:.1f}{rsi_label}"
                if tech["trend"] is not None:
                    gold_section += f"\n- Trend: {tech['trend']}"
                    if tech["golden_cross"] is not None:
                        gold_section += f" | Golden Cross: {'Yes' if tech['golden_cross'] else 'No'}"
            sections.append(gold_section)
        else:
            sections.append(f"## Gold Price\n- EUR price: {sym}{portfolio['gold_price_eur']:.2f}/g\n- [Historical data unavailable]")

        # Macro environment
        macro = market_data.get("macro")
        fg = market_data.get("fear_greed")
        if macro or fg:
            macro_section = "## Macro Environment"
            if macro:
                if "dxy" in macro:
                    macro_section += f"\n- Dollar Index (DXY): {macro['dxy']:.1f}"
                if "us10y" in macro:
                    macro_section += f"\n- US 10Y Yield: {macro['us10y']:.2f}%"
                if "vix" in macro:
                    macro_section += f"\n- VIX: {macro['vix']:.1f}"
            if fg:
                macro_section += f"\n- Fear & Greed: {fg['score']} ({fg['rating']})"
            sections.append(macro_section)

        # News
        news = market_data.get("news")
        if news:
            news_section = "## Recent Gold News"
            for item in news:
                news_section += f"\n- [{item['source']}] {item['title']}"
            sections.append(news_section)

        # Economic calendar
        cal = market_data.get("calendar")
        if cal:
            cal_section = "## Upcoming Economic Events"
            for ev in cal:
                cal_section += f"\n- {ev['date']}: {ev['event']} (impact: {ev['impact']})"
            sections.append(cal_section)

        user_msg = "\n\n".join(sections)
        user_msg += (
            "\n\n---\n"
            "Based on all the data above, provide:\n"
            "1. Market assessment (2-3 sentences)\n"
            "2. Action: BUY / HOLD / SELL (with brief rationale)\n"
            "3. Key factors (3-4 bullet points using • character)\n"
            "4. Risk level: LOW / MEDIUM / HIGH\n"
            "5. One-line verdict starting with → in one of these exact formats:\n"
            "   → HOLD\n"
            f"   → BUY {sym}<amount> at {sym}<price>/g\n"
            f"   → SELL {sym}<amount> at {sym}<price>/g\n"
            "   Use the investor's monthly SIP amount as reference for BUY amounts.\n"
            "Format for easy reading on a phone screen."
        )

        return system, user_msg

    def analyze(self, market_data: dict, portfolio: dict) -> dict:
        """Send data to Claude Haiku and get investment recommendation."""
        if not self.api_key:
            return None

        system, user_msg = self._build_prompt(market_data, portfolio)

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_msg}],
        }

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        data = json.dumps(payload).encode()
        req = urllib.request.Request(self.api_url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                text = result["content"][0]["text"]
                return {"raw_text": text, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            print(f"  AI Analyst error: {e}")
            return None

    def get_prompt_preview(self, market_data: dict, portfolio: dict) -> str:
        """Return the full prompt for debugging (--test-ai mode)."""
        system, user_msg = self._build_prompt(market_data, portfolio)
        return f"=== SYSTEM ===\n{system}\n\n=== USER MESSAGE ===\n{user_msg}"


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


def run_analysis(dry_run: bool = False):
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

    # Summary: send on significant changes or weekly routine
    last_summary = state.get("last_summary")
    days_since_summary = ((datetime.now() - datetime.fromisoformat(last_summary)).days
                          if last_summary else 999)
    weekly_due = days_since_summary >= 7

    # Detect significant portfolio changes
    last_invested = state.get("last_invested", 0)
    invested_changed = abs(actual_invested - last_invested) > 1.0
    last_orders = state.get("last_orders_count", 0)
    orders_changed = orders_count != last_orders

    # Detect significant daily price move (>2%)
    last_price = state.get("last_price")
    daily_price_move = False
    if last_price and last_price > 0:
        daily_chg = abs((gold_price - last_price) / last_price) * 100
        daily_price_move = daily_chg >= 2.0

    should_summarize = weekly_due or invested_changed or orders_changed or daily_price_move

    # --- AI Analyst (only when notification will fire) ---
    ai_full_text = ""     # Full analysis for HA persistent notification
    ai_verdict = ""       # One-line verdict for push notification
    ai_cfg = cfg.get("ai_analyst", {})

    if should_summarize and ai_cfg.get("enabled") and ai_cfg.get("anthropic_api_key"):
        # Check cooldown — don't re-analyze within 20 hours
        last_ai_date = state.get("last_ai_date")
        cached_full = state.get("last_ai_analysis", "")
        cached_verdict = state.get("last_ai_verdict", "")
        skip_ai = False
        if last_ai_date:
            try:
                hours_since = (datetime.now() - datetime.fromisoformat(last_ai_date)).total_seconds() / 3600
                skip_ai = hours_since < 20
            except Exception:
                pass

        if skip_ai and cached_full:
            ai_full_text = cached_full
            ai_verdict = cached_verdict
            print("  Reusing cached AI analysis")
        else:
            print("  Running AI market analysis...")
            collector = MarketDataCollector(
                fred_api_key=ai_cfg.get("fred_api_key", ""),
                finnhub_api_key=ai_cfg.get("finnhub_api_key", ""),
            )
            market_data = collector.collect_all()

            portfolio_context = {
                "invested": actual_invested,
                "grams": invested_grams,
                "target_grams": target_grams,
                "target_date": goals["target_date"],
                "months_left": months_left,
                "pct": pct,
                "monthly": monthly,
                "gold_price_eur": gold_price,
                "ppl": ppl,
                "sym": sym,
            }

            analyst = AIAnalyst(ai_cfg["anthropic_api_key"])
            result = analyst.analyze(market_data, portfolio_context)

            if result:
                ai_full_text = result["raw_text"]
                # Extract one-line verdict (line starting with →)
                for line in ai_full_text.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("\u2192") or stripped.startswith("->"):
                        ai_verdict = stripped
                        break
                # Fallback: if no → line, grab first sentence
                if not ai_verdict:
                    first_line = ai_full_text.strip().split("\n")[0]
                    ai_verdict = first_line[:80]
                state["last_ai_analysis"] = ai_full_text
                state["last_ai_verdict"] = ai_verdict
                state["last_ai_date"] = datetime.now().isoformat()
                if market_data.get("errors"):
                    print(f"  Data gaps: {', '.join(market_data['errors'])}")
            else:
                print("  AI analysis failed — sending without it")

    if should_summarize:
        # Determine notification title
        if invested_changed and last_invested == 0:
            title_event = "Order Filled"
        elif invested_changed:
            title_event = "Portfolio Changed"
        elif orders_changed and orders_count > last_orders:
            title_event = "New Order"
        elif orders_changed and orders_count < last_orders:
            title_event = "Order Completed"
        elif daily_price_move:
            title_event = "Price Alert"
        else:
            title_event = "Weekly Report"
        status = "On track" if projected >= target_grams else "Behind target"

        # --- Build PUSH notification (short, fits on phone) ---
        lines = []
        lines.append(f"Total: {sym}{total_value:.2f}")
        if actual_invested > 0:
            lines.append(f"Invested: {sym}{actual_invested:.2f} ({invested_grams:.1f}g)")
        else:
            lines.append(f"Invested: {sym}0.00")
        if orders_count > 0:
            lines.append(f"Active Orders: {orders_count}")
        if pending_pie > 0:
            lines.append(f"Pending: {sym}{pending_pie:.2f}")
        if orders_count > 0 and abs(orders_value - pending_pie) > 1.0:
            lines.append(f"Orders Value: {sym}{orders_value:.2f}")
        if free_cash > 0:
            lines.append(f"Cash: {sym}{free_cash:.2f}")
        if ppl and round(ppl, 2) != 0:
            sign = "+" if ppl > 0 else ""
            lines.append(f"Return: {sign}{sym}{ppl:.2f}")
        if total_dividends > 0:
            lines.append(f"Dividends: {sym}{total_dividends:.2f}")

        gold_line = f"Gold Price: {sym}{gold_price:.2f}/g"
        last_price = state.get("last_price")
        if last_price and last_price > 0:
            daily_chg = ((gold_price - last_price) / last_price) * 100
            arrow = "\u2191" if daily_chg >= 0 else "\u2193"
            gold_line += f" {arrow}{abs(daily_chg):.1f}%"
        lines.append(gold_line)

        # AI one-liner in push (between price and vault)
        if ai_verdict:
            lines.append(f"\U0001F4CA {ai_verdict}")

        lines.append("")
        lines.append(vault)
        lines.append(f"{total_grams:.1f}g \u2192 {target_grams}g ({pct:.1f}%)")

        if ai_full_text:
            lines.append("Tap for full AI report \u2197")

        push_msg = "\n".join(lines)
        title = f"Gold Tracker - {title_event}"

        # --- Build portfolio data for HTML report ---
        portfolio_rows = []
        portfolio_rows.append(("Total Value", f"{sym}{total_value:.2f}"))
        if actual_invested > 0:
            portfolio_rows.append(("Invested", f"{sym}{actual_invested:.2f} ({invested_grams:.1f}g)"))
        else:
            portfolio_rows.append(("Invested", f"{sym}0.00"))
        if orders_count > 0:
            portfolio_rows.append(("Active Orders", str(orders_count)))
        if pending_pie > 0:
            portfolio_rows.append(("Pending", f"{sym}{pending_pie:.2f}"))
        if free_cash > 0:
            portfolio_rows.append(("Cash", f"{sym}{free_cash:.2f}"))
        if ppl and round(ppl, 2) != 0:
            sign = "+" if ppl > 0 else ""
            portfolio_rows.append(("Return", f"{sign}{sym}{ppl:.2f}"))
        if total_dividends > 0:
            portfolio_rows.append(("Dividends", f"{sym}{total_dividends:.2f}"))
        gold_line_report = f"{sym}{gold_price:.2f}/g"
        if daily_chg is not None:
            arrow = "\u2191" if daily_chg >= 0 else "\u2193"
            gold_line_report += f" {arrow}{abs(daily_chg):.1f}%"
        portfolio_rows.append(("Gold Price", gold_line_report))

        progress_text = f"{total_grams:.1f}g \u2192 {target_grams}g ({pct:.1f}%)"
        projection_text = f"Projected: {projected:.1f}g by {goals['target_date']} \u2014 {status}"

        if dry_run:
            print(f"\n--- DRY RUN: PUSH NOTIFICATION ---")
            print(f"Title: {title}")
            print(f"Message:\n{push_msg}")
            print(f"\n--- DRY RUN: HTML REPORT ---")
            for label, val in portfolio_rows:
                print(f"  {label}: {val}")
            if ai_full_text:
                print(f"  AI: {ai_full_text[:100]}...")
            print(f"  {vault}")
            print(f"  {progress_text}")
            print(f"  {projection_text}")
            print(f"--- END DRY RUN ---\n")
            alerts_sent += 1
            state["last_summary"] = datetime.now().isoformat()
        else:
            # Write full HTML report to /config/www/ (served at /local/)
            notifier.write_html_report(
                portfolio={"sym": sym, "rows": portfolio_rows},
                ai_text=ai_full_text or "",
                grams=total_grams,
                target=target_grams,
                pct=pct,
                projection=projection_text,
            )

            # Send short push notification to phone
            push_extra = {
                "color": "#FFD700",
                "clickAction": f"/local/gold_tracker.html?v={int(time.time())}",
                "actions": [
                    {
                        "action": "URI",
                        "title": "Open Trading 212",
                        "uri": "app://com.avuscapital.trading212",
                    }
                ],
            }
            if notifier.send(title, push_msg, extra=push_extra):
                alerts_sent += 1
                state["last_summary"] = datetime.now().isoformat()

    # Save state
    state["last_price"] = gold_price
    state["last_invested"] = actual_invested
    state["last_orders_count"] = orders_count
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


def run_test_data():
    """Test data collection from all sources — prints raw results."""
    cfg = CONFIG.get("ai_analyst", {})
    collector = MarketDataCollector(
        fred_api_key=cfg.get("fred_api_key", ""),
        finnhub_api_key=cfg.get("finnhub_api_key", ""),
    )
    print("Testing market data collection...\n")
    data = collector.collect_all()
    print(f"\n{'='*50}")
    print(json.dumps(data, indent=2, default=str))
    if data["errors"]:
        print(f"\nFailed sources: {', '.join(data['errors'])}")
    else:
        print("\nAll sources OK")


def run_test_ai():
    """Test AI prompt construction — prints prompt without calling API."""
    cfg = CONFIG
    ai_cfg = cfg.get("ai_analyst", {})

    collector = MarketDataCollector(
        fred_api_key=ai_cfg.get("fred_api_key", ""),
        finnhub_api_key=ai_cfg.get("finnhub_api_key", ""),
    )
    print("Collecting market data...\n")
    market_data = collector.collect_all()

    portfolio = {
        "invested": 0, "grams": 0, "target_grams": cfg["goals"]["target_gold_grams"],
        "target_date": cfg["goals"]["target_date"], "months_left": 16,
        "pct": 0, "monthly": cfg["goals"]["monthly_investment"],
        "gold_price_eur": get_gold_price_eur(), "ppl": 0, "sym": "\u20ac",
    }

    analyst = AIAnalyst(ai_cfg.get("anthropic_api_key", "no-key"))
    prompt = analyst.get_prompt_preview(market_data, portfolio)
    print(f"\n{'='*50}")
    print(prompt)
    print(f"{'='*50}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gold Tracker")
    parser.add_argument("--daemon", "-d", action="store_true", help="Run as daemon")
    parser.add_argument("--time", "-t", default="08:00", help="Daily run time (HH:MM)")
    parser.add_argument("--test-data", action="store_true", help="Test data collection only")
    parser.add_argument("--test-ai", action="store_true", help="Test AI prompt (no API call)")
    parser.add_argument("--dry-run", action="store_true", help="Full run, print instead of send")
    args = parser.parse_args()

    if args.test_data:
        run_test_data()
    elif args.test_ai:
        run_test_ai()
    elif args.daemon:
        run_daemon(args.time)
    else:
        run_analysis(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
