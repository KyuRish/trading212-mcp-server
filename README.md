# Trading 212 MCP Server

A Model Context Protocol (MCP) server for seamless integration with Trading 212's trading platform.

## Features

- **Account Management**: View account info, cash balance, portfolio positions
- **Order Management**: Place market, limit, stop, and stop-limit orders
- **Pie Management**: Create, update, duplicate, and delete investment pies
- **Market Data**: Access tradeable instruments and exchange information
- **History**: Fetch order history, dividends, and transaction records
- **CSV Exports**: Request and download account data exports

## Installation

### Prerequisites
- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/KyuRish/trading212-mcp-server.git
cd trading212-mcp-server
```

2. Install dependencies:
```bash
uv install
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

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

## API Authentication

This server uses Trading 212's Basic Auth:
- Generate API Key and Secret from Trading 212 app: Settings → API (Beta)
- Both `TRADING212_API_KEY` and `TRADING212_API_SECRET` are required

## Available Tools

| Tool | Description |
|------|-------------|
| `fetch_account_info` | Get account metadata |
| `fetch_account_cash` | Get cash balance |
| `fetch_all_open_positions` | Get portfolio positions |
| `fetch_pies` | List all pies |
| `place_market_order` | Place market order |
| `place_limit_order` | Place limit order |
| `fetch_historical_order_data` | Get order history |
| `fetch_paid_out_dividends` | Get dividend history |

## License

MIT License
