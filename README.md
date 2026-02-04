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
- **Smart Notifications** -- Only alerts when there's actionable information
- **Dynamic Currency** -- Automatically detects your account currency (EUR, USD, GBP, etc.)
- **Gold Price Monitoring** -- Tracks daily price changes with trend indicators
- **Progress Visualization** -- Vault-style progress bar toward your gold target
- **Home Assistant Integration** -- Push notifications via the HA Companion app

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

### Weekly Summary Notification

The weekly notification includes:

```
Total: €800.00
Invested: €500.00 (3.9g)
Active Orders: 1
Cash: €300.00
Return: +€12.50
Dividends: €2.30
Gold Price: €128.05/g ↑2.0%

🪙🪙🪙⚫⚫⚫⚫⚫⚫⚫👑
3.9g → 100g (3.9%)
```

- **Total** and **Invested** are always shown; all other fields appear only when non-zero
- **Gold Price** includes daily change with ↑/↓ trend arrow
- **Progress bar** fills with coins as you accumulate gold toward your target
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

### Running Locally

```bash
# One-shot analysis
python scripts/standalone_analyzer.py

# Run as daemon (daily at 8 AM)
python scripts/standalone_analyzer.py --daemon --time 08:00
```

### Deploy on Home Assistant Server

`standalone_analyzer.py` has zero external dependencies -- it runs with just Python's standard library.

```bash
# SSH into your HA server
ssh user@homeassistant.local

# Create directory and transfer the script
mkdir -p ~/trading212-analyzer

# Create .env file with your credentials
cat > ~/trading212-analyzer/.env << 'EOF'
HA_URL=http://127.0.0.1:8123
HA_TOKEN=your_long_lived_token
HA_DEVICE=your_phone_device
T212_API_KEY=your_api_key
T212_API_SECRET=your_api_secret
T212_ENV=live
TARGET_GOLD=100
TARGET_DATE=2027-06-30
MONTHLY_INVEST=400
EOF

# Create runner script
cat > ~/trading212-analyzer/run.sh << 'EOF'
#!/bin/sh
cd ~/trading212-analyzer
set -a; . ./.env; set +a
python3 analyzer.py "$@"
EOF
chmod +x ~/trading212-analyzer/run.sh
```

Add to your HA `configuration.yaml`:

```yaml
shell_command:
  run_gold_tracker: "/home/user/trading212-analyzer/run.sh"
```

Create an automation to run daily at your preferred time.

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
└── README.md
```

## License

MIT License
