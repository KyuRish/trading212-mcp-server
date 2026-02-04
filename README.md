# Trading 212 MCP Server

A Model Context Protocol (MCP) server for seamless integration with Trading 212's trading platform, paired with a standalone gold accumulation tracker that delivers smart notifications via Home Assistant.

## Features

### MCP Server
- **Account Management** -- View account info, cash balance, and portfolio positions
- **Order Management** -- Place market, limit, stop, and stop-limit orders
- **Pie Management** -- Create, update, duplicate, and delete investment pies
- **Market Data** -- Search tradeable instruments and exchange schedules
- **History** -- Fetch order history, dividends, and transaction records
- **CSV Exports** -- Request and download account data exports

### Gold Tracker (Standalone Analyzer)
- **Zero Dependencies** -- Uses only Python standard library; runs anywhere Python 3 is available
- **AI Financial Analyst** -- Claude-powered market analysis with buy/hold/sell recommendations
- **Smart Notifications** -- Split push (short) + persistent report (full) via Home Assistant
- **Dynamic Currency** -- Automatically detects your account currency (EUR, USD, GBP, etc.)
- **Gold Price Monitoring** -- Tracks daily price changes with trend indicators
- **Technical Analysis** -- SMA(50/200), RSI(14), golden cross detection
- **Macro Data** -- DXY, 10Y yield, VIX, Fear & Greed index
- **Event-Aware Scheduling** -- AI recommends next analysis time based on economic events (CPI, Fed, NFP)
- **Progress Visualization** -- Vault-style progress bar toward your gold target
- **Home Assistant Integration** -- Push notifications + persistent reports via HA Companion app

## Installation

### Prerequisites
- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
git clone https://github.com/KyuRish/trading212-mcp-server.git
cd trading212-mcp-server
uv sync
```

## API Authentication

Generate your API Key and Secret from the Trading 212 app under **Settings > API (Beta)**.

Both `TRADING212_API_KEY` and `TRADING212_API_SECRET` are required. The server uses Basic Auth (base64-encoded `key:secret`).

## MCP Server

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "trading212": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<path-to-repo>",
        "src/server.py"
      ],
      "env": {
        "TRADING212_API_KEY": "<your-api-key>",
        "TRADING212_API_SECRET": "<your-api-secret>",
        "ENVIRONMENT": "live"
      }
    }
  }
}
```

Set `ENVIRONMENT` to `demo` for paper trading.

### Available Tools

| Tool | Description |
|------|-------------|
| `fetch_account_info` | Account metadata (currency, ID) |
| `fetch_account_cash` | Cash balance, invested value, P&L |
| `fetch_all_open_positions` | All portfolio positions |
| `search_instrument` | Search instruments by ticker or name |
| `search_exchange` | Search exchanges by name or ID |
| `fetch_pies` | List all investment pies |
| `fetch_a_pie` | Get details of a specific pie |
| `create_pie` | Create a new pie |
| `update_pie` | Update an existing pie |
| `duplicate_pie` | Duplicate a pie |
| `delete_pie` | Delete a pie |
| `fetch_all_orders` | List active orders |
| `fetch_order` | Get a specific order |
| `place_market_order` | Place a market order |
| `place_limit_order` | Place a limit order |
| `place_stop_order` | Place a stop order |
| `place_stop_limit_order` | Place a stop-limit order |
| `cancel_order` | Cancel an existing order |
| `fetch_historical_order_data` | Order history with pagination |
| `fetch_paid_out_dividends` | Dividend history |
| `fetch_transaction_list` | Deposit/withdrawal history |
| `fetch_exports_list` | List CSV exports |
| `request_csv_export` | Request a new CSV export |

---

## Gold Tracker

The standalone analyzer monitors your gold investments on Trading 212 and sends notifications via Home Assistant only when there's something worth acting on.

### Alert Types

| Alert | Trigger |
|-------|---------|
| **Buying Opportunity** | Gold price drops >5% in 7 days |
| **Take Profit** | Gold price rises >10% in 7 days |
| **Weekly Summary** | Portfolio + progress report every 7 days |
| **Event-Triggered** | AI-scheduled check around high-impact events (CPI, Fed, NFP) |

### Notification System

Notifications are split into two parts:

**Push notification** (short, fits on phone lock screen):
```
Total: €500.00
Invested: €483.53 (3.9g)
Cash: €11.26
Gold Price: €128.05/g ↑2.0%

📊 → HOLD
⏰ Next: Feb 12 15:00 (CPI release)
Tap for full AI report ↗
```

**Full HTML report** (served by HA, opens on tap):
- 3D vault-style progress bar with metallic frame, rivets, and gold-coin fill
- Animated neon fox mascot (Kyubi) that runs along the bar and turns to face you at 100%
- Coin spill animations with burst effect at goal completion
- Portfolio table, AI market analysis, and "Open Trading 212" button
- Mobile-aware: launches the T212 app on phones, web on desktop

Tapping the push notification opens the full report at `/local/gold_tracker.html`:

```
┌──────────────────────────────────────┐
│  🪙 Gold Tracker                     │
│  Wednesday, 04 February 2026         │
│                                      │
│  ┌─ Portfolio ─────────────────────┐ │
│  │ Total Value         €500.00     │ │
│  │ Invested      €483.53 (3.9g)   │ │
│  │ Cash                 €11.26     │ │
│  │ Return              +€12.50     │ │
│  │ Gold Price    €128.05/g ↑2.0%  │ │
│  └─────────────────────────────────┘ │
│                                      │
│  📊 AI Market Analysis               │
│  → HOLD — Continue monthly SIP       │
│                                      │
│       🦊                             │
│  ╔══●═══[████░░░░░░░░░░░░]═●══🏦╗  │
│  3.9g                    👑 100g     │
│                                      │
│  ┌──────────────────────────────────┐│
│  │      Open Trading 212 →         ││
│  └──────────────────────────────────┘│
└──────────────────────────────────────┘
```

- Each new report auto-replaces the previous one
- **Currency symbol** is auto-detected from your Trading 212 account

### Configuration

The analyzer is configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `HA_URL` | Home Assistant URL | `http://127.0.0.1:8123` |
| `HA_TOKEN` | HA long-lived access token | -- |
| `HA_DEVICE` | HA Companion app device name | `my_oneplus` |
| `T212_API_KEY` | Trading 212 API key | -- |
| `T212_API_SECRET` | Trading 212 API secret | -- |
| `T212_ENV` | Trading 212 environment | `live` |
| `TARGET_GOLD` | Target gold in grams | `100` |
| `TARGET_DATE` | Target date (YYYY-MM-DD) | `2027-06-30` |
| `MONTHLY_INVEST` | Monthly investment amount | `400` |
| `AI_ANALYST_ENABLED` | Enable AI analysis | `true` |
| `ANTHROPIC_API_KEY` | Claude API key for AI analyst | -- |
| `FRED_API_KEY` | FRED API key for macro data | -- |
| `FINNHUB_API_KEY` | Finnhub API key (optional) | -- |

### Running Locally

```bash
# One-shot analysis
python scripts/standalone_analyzer.py

# Run as daemon (daily baseline + event-aware checks every 4h)
python scripts/standalone_analyzer.py --daemon --time 08:00
```

### Deploy on Home Assistant Server

`standalone_analyzer.py` has zero external dependencies -- it runs with just Python's standard library.

> **Important**: On HA SSH add-on, only `/config/` persists across restarts. Do not use `~/` (home directory).

```bash
# From your local machine, deploy the script via SSH pipe (SCP is not supported by HA SSH add-on)
cat scripts/standalone_analyzer.py | ssh -i ~/.ssh/your_ha_key user@homeassistant.local \
  "sudo tee /config/trading212-analyzer/analyzer.py > /dev/null"

# Deploy the fox animation GIF (served by HA at /local/kyubi_fox.gif)
cat assets/kyubi_fox.gif | ssh -i ~/.ssh/your_ha_key user@homeassistant.local \
  "sudo tee /config/www/kyubi_fox.gif > /dev/null"

# Create .env file with your credentials
ssh -i ~/.ssh/your_ha_key user@homeassistant.local "sudo tee /config/trading212-analyzer/.env > /dev/null" << 'EOF'
HA_URL=http://127.0.0.1:8123
HA_TOKEN=your_long_lived_token
HA_DEVICE=your_phone_device
T212_API_KEY=your_api_key
T212_API_SECRET=your_api_secret
T212_ENV=live
TARGET_GOLD=100
TARGET_DATE=2027-06-30
MONTHLY_INVEST=400
AI_ANALYST_ENABLED=true
ANTHROPIC_API_KEY=your_claude_api_key
FRED_API_KEY=your_fred_api_key
EOF

# Create runner script
ssh -i ~/.ssh/your_ha_key user@homeassistant.local "sudo tee /config/trading212-analyzer/run.sh > /dev/null && sudo chmod +x /config/trading212-analyzer/run.sh" << 'EOF'
#!/bin/sh
cd /config/trading212-analyzer
set -a; . ./.env; set +a
python3 analyzer.py "$@"
EOF
```

Add to your HA `configuration.yaml`:

```yaml
shell_command:
  run_gold_tracker: "/config/trading212-analyzer/run.sh"
```

Create an automation to run every 4 hours (the script is smart enough to only send notifications when warranted):

```yaml
automation:
  - alias: "Gold Tracker"
    trigger:
      - platform: time_pattern
        hours: "/4"
    action:
      - service: shell_command.run_gold_tracker
```

The AI analyst recommends when to check next based on upcoming economic events. On quiet weeks it defaults to 7 days; before major events (CPI, Fed, NFP) it schedules a check ~30 minutes after the release.

### CLI Flags

```bash
python3 analyzer.py              # Full run (fetch data, AI analysis, send notification)
python3 analyzer.py --dry-run    # Full run but print instead of sending
python3 analyzer.py --test-data  # Test market data collection only
python3 analyzer.py --test-ai    # Test data + build AI prompt (no API call)
python3 analyzer.py --daemon     # Run as daemon (daily + event-aware 4h checks)
```

### REST API Service (Optional)

Run the analyzer as a service with a REST API for remote control:

```bash
uv run python scripts/analyzer_service.py --port 8212
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/status` | Service status |
| GET | `/health` | Health check |
| POST | `/run` | Trigger analysis |
| POST | `/stop` | Stop the service |

## Project Structure

```
trading212-mcp-server/
├── src/
│   ├── server.py              # MCP server entry point
│   ├── mcp_server.py          # MCP framework setup
│   ├── tools.py               # MCP tool definitions
│   ├── models.py              # Pydantic models for T212 API
│   ├── prompts.py             # MCP prompts
│   ├── resources.py           # MCP resources
│   └── utils/
│       ├── client.py          # Trading 212 API client (httpx)
│       └── hishel_config.py   # HTTP cache configuration
├── scripts/
│   ├── standalone_analyzer.py # Gold tracker (stdlib only)
│   ├── daily_analyzer.py      # Portfolio analyzer (with deps)
│   ├── analyzer_service.py    # REST API service
│   ├── ha_notifier.py         # Home Assistant notifications
│   ├── email_notifier.py      # Email notifications
│   ├── alert_config.example.json
│   └── homeassistant/         # HA integration configs
│       ├── configuration.yaml
│       ├── scripts.yaml
│       └── dashboard_card.yaml
├── assets/
│   └── kyubi_fox.gif          # Neon fox animation for HTML report
└── README.md
```

## License

MIT License
