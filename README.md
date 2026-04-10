# Trading 212 MCP Server

[![PyPI](https://img.shields.io/pypi/v/trading212-mcp-server)](https://pypi.org/project/trading212-mcp-server/)
![Downloads](https://img.shields.io/pypi/dm/trading212-mcp-server?color=8B4513)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Glama](https://img.shields.io/badge/Glama-Security%20A%20%C2%B7%20Quality%20A-green)](https://glama.ai/mcp/servers/@KyuRish/trading212-mcp-server)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![MCP](https://img.shields.io/badge/MCP-compatible-purple)
![Tools](https://img.shields.io/badge/Tools-32-orange)

<!-- mcp-name: io.github.KyuRish/trading212-mcp-server -->

Connect your AI assistant to your Trading 212 brokerage account. Ask questions about your portfolio, place trades, manage pies, and analyze dividends - all through natural language.

Works with **Claude Desktop, Claude Code, ChatGPT, Gemini, Cursor, Windsurf**, and any client that supports the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## Why this server?

- **32 tools** covering the full Trading 212 API, plus 4 analytics tools that combine multiple API calls into actionable insights
- **Smart rate limiting** - reads T212's rate limit headers, auto-waits, and retries on 429 (up to 3 times). No rate limit errors leak to your AI
- **Zero config** - install from PyPI, add your API key, done. No Docker, no database, no Redis
- **Typed responses** - every tool returns structured Pydantic models, not raw JSON
- **Paper trading** - set `ENVIRONMENT=demo` to test with virtual money first

## What can it do?

| Category | Tools | Examples |
|----------|-------|---------|
| **Analytics** | Portfolio summary, performance, dividends, activity | "Show me my portfolio P&L" |
| **Trading** | Market, limit, stop, stop-limit orders | "Buy 5 shares of AAPL" |
| **Portfolio** | Positions, cash balance, account info | "What's my cash balance?" |
| **Pies** | Create, update, duplicate, delete pies | "Show my pie allocations" |
| **Market Data** | Instrument search, exchange schedules | "Search for Tesla" |
| **History** | Past orders, dividends, transactions, CSV exports | "Show my dividend history" |

### Analytics tools

These combine multiple API calls into single high-level responses:

- **`fetch_portfolio_summary`** - Complete snapshot: total value, P&L, cash, top holdings, allocation
- **`fetch_portfolio_performance`** - Per-position returns with dividends, best/worst performers
- **`fetch_dividend_summary`** - Income analysis grouped by ticker and month
- **`fetch_recent_activity`** - Combined timeline of trades and transactions

## Quick start

### Install

```bash
uvx trading212-mcp-server
```

Or via pip:

```bash
pip install trading212-mcp-server
```

### Get your API credentials

From the Trading 212 app: **Settings > API (Beta)**. You need both the API Key and Secret - the server uses Basic Auth.

### Connect to Claude Desktop

Add to `claude_desktop_config.json` (Windows: `%APPDATA%\Claude\`, Mac: `~/Library/Application Support/Claude/`):

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

### Connect to Claude Code

```bash
claude mcp add trading212 -- uvx trading212-mcp-server
```

Then set the environment variables in your shell or `.env` file.

### Other clients (Cursor, Windsurf, ChatGPT, etc.)

Same command and env vars - configure per your client's MCP docs. Set `ENVIRONMENT` to `demo` for paper trading.

### From source

```bash
git clone https://github.com/KyuRish/trading212-mcp-server.git
cd trading212-mcp-server
cp .env.example .env  # fill in your API keys
uv sync
uv run -m trading212_mcp_server.server
```

<details>
<summary><code>claude_desktop_config.json</code> for source installs</summary>

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

</details>

## All 32 tools

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
| `fetch_all_open_positions` | All portfolio positions with live prices |
| `search_specific_position_by_ticker` | Single position lookup by ticker |

### Trading
| Tool | Description |
|------|-------------|
| `place_market_order` | Buy/sell at current market price |
| `place_limit_order` | Buy/sell at specified price or better |
| `place_stop_order` | Trigger order at stop price |
| `place_stop_limit_order` | Stop trigger with limit execution |
| `fetch_all_orders` | List all pending orders |
| `fetch_order` | Get specific order by ID |
| `cancel_order` | Cancel a pending order |

### Pies
| Tool | Description |
|------|-------------|
| `fetch_pies` | List all investment pies |
| `fetch_a_pie` | Pie details with instrument allocations |
| `create_pie` | Create a new pie with target weights |
| `update_pie` | Update pie settings and allocations |
| `duplicate_pie` | Clone an existing pie |
| `delete_pie` | Remove a pie |

### Market Data
| Tool | Description |
|------|-------------|
| `search_instrument` | Search tradeable instruments by ticker or name |
| `search_exchange` | Search available exchanges |

### History
| Tool | Description |
|------|-------------|
| `fetch_historical_order_data` | Past orders with pagination |
| `fetch_paid_out_dividends` | Dividend payment history |
| `fetch_transaction_list` | Deposits and withdrawals |
| `fetch_exports_list` | List CSV export reports |
| `request_csv_export` | Request a new CSV export |

## Compatibility

Tested with these MCP clients:

| Client | Status |
|--------|--------|
| Claude Desktop | Supported |
| Claude Code | Supported |
| Cursor | Supported |
| Windsurf | Supported |
| Any MCP-compatible client | Supported |

## Author

Built by [Rishabh Dogra](https://github.com/KyuRish).

## Support

If this server saves you time, a coffee would mean a lot.

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/kyuish)

## License

MIT
