# Trading 212 MCP Server

[![PyPI](https://img.shields.io/pypi/v/trading212-mcp-server)](https://pypi.org/project/trading212-mcp-server/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

mcp-name: io.github.kyurish/trading212-mcp-server

MCP server for the Trading 212 API. Works with any LLM client that supports MCP - Claude, ChatGPT, Gemini, Cursor, Windsurf, and more.

## What can it do?

**28 tools** covering the full Trading 212 API, plus 4 analytics tools that combine multiple API calls into actionable insights:

| Category | Tools |
|----------|-------|
| **Analytics** | Portfolio summary, performance report, dividend analysis, recent activity |
| **Trading** | Market, limit, stop, and stop-limit orders |
| **Portfolio** | Positions, pies, cash balance |
| **Market Data** | Instrument search, exchange schedules |
| **History** | Past orders, dividends, transactions, CSV exports |

### Analytics tools

These combine multiple API calls into single high-level responses:

- **`fetch_portfolio_summary`** - Complete snapshot: total value, P&L, cash, top holdings, allocation
- **`fetch_portfolio_performance`** - Per-position returns with dividends, best/worst performers
- **`fetch_dividend_summary`** - Income analysis grouped by ticker and month
- **`fetch_recent_activity`** - Combined timeline of trades and transactions

## Installation

### Quick start (recommended)

```bash
uvx trading212-mcp-server
```

### pip

```bash
pip install trading212-mcp-server
```

### From source

```bash
git clone https://github.com/KyuRish/trading212-mcp-server.git
cd trading212-mcp-server
uv sync
```

## Authentication

Get your API Key and Secret from the Trading 212 app: **Settings > API (Beta)**.

Both are required - the server uses Basic Auth (base64 `key:secret`).

## Connect to your LLM

### Claude Desktop

Add to `claude_desktop_config.json` ([Windows](file:///C:/Users) `%APPDATA%\Claude\` / [Mac](file:///Users) `~/Library/Application Support/Claude/`):

```json
{
  "mcpServers": {
    "trading212": {
      "command": "uvx",
      "args": ["trading212-mcp-server"],
      "env": {
        "TRADING212_API_KEY": "<your-api-key>",
        "TRADING212_API_SECRET": "<your-api-secret>",
        "ENVIRONMENT": "live"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add trading212 -- uvx trading212-mcp-server
```

Then set the environment variables in your shell or `.env` file.

### Other clients (Cursor, Windsurf, etc.)

Same command and env vars - configure per your client's MCP docs.

Set `ENVIRONMENT` to `demo` for paper trading.

### From source

If running from a cloned repo instead of PyPI:

```json
{
  "mcpServers": {
    "trading212": {
      "command": "uv",
      "args": ["run", "--directory", "<path-to-repo>", "-m", "trading212_mcp_server.server"],
      "env": {
        "TRADING212_API_KEY": "<your-api-key>",
        "TRADING212_API_SECRET": "<your-api-secret>",
        "ENVIRONMENT": "live"
      }
    }
  }
}
```

## All tools

### Analytics (composite)
| Tool | Description |
|------|-------------|
| `fetch_portfolio_summary` | Complete portfolio snapshot with P&L and allocations |
| `fetch_portfolio_performance` | Per-position returns, dividends, best/worst performers |
| `fetch_dividend_summary` | Dividend income by ticker and month |
| `fetch_recent_activity` | Combined timeline of trades and transactions |

### Account
| Tool | Description |
|------|-------------|
| `fetch_account_info` | Account metadata (currency, ID) |
| `fetch_account_cash` | Cash balance, invested value, P&L |
| `fetch_all_open_positions` | All portfolio positions |
| `search_specific_position_by_ticker` | Single position by ticker |

### Trading
| Tool | Description |
|------|-------------|
| `place_market_order` | Buy/sell at current price |
| `place_limit_order` | Buy/sell at specified price or better |
| `place_stop_order` | Trigger order at stop price |
| `place_stop_limit_order` | Stop trigger with limit execution |
| `fetch_all_orders` | List pending orders |
| `fetch_order` | Get specific order by ID |
| `cancel_order` | Cancel a pending order |

### Pies
| Tool | Description |
|------|-------------|
| `fetch_pies` | List all pies |
| `fetch_a_pie` | Pie details by ID |
| `create_pie` | Create a new pie |
| `update_pie` | Update pie settings |
| `duplicate_pie` | Clone a pie |
| `delete_pie` | Remove a pie |

### Market Data
| Tool | Description |
|------|-------------|
| `search_instrument` | Search by ticker or name |
| `search_exchange` | Search exchanges |

### History
| Tool | Description |
|------|-------------|
| `fetch_historical_order_data` | Past orders with pagination |
| `fetch_paid_out_dividends` | Dividend history |
| `fetch_transaction_list` | Deposits/withdrawals |
| `fetch_exports_list` | List CSV exports |
| `request_csv_export` | Request new CSV export |

## Development

```bash
git clone https://github.com/KyuRish/trading212-mcp-server.git
cd trading212-mcp-server
cp .env.example .env  # fill in your API keys
uv sync
uv run -m trading212_mcp_server.server
```

## License

MIT
