from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import Account, Cash, Position


@mcp.tool("fetch_account_info")
def fetch_account_info() -> Account:
    """Retrieve account metadata such as the currency and unique account identifier."""
    return client.fetch_account()


@mcp.tool("fetch_account_cash")
def fetch_account_cash() -> Cash:
    """Get a detailed breakdown of your account balance, including available cash, invested capital, P/L, and blocked funds."""
    return client.fetch_cash()


@mcp.tool("fetch_all_open_positions")
def fetch_all_open_positions() -> list[Position]:
    """Retrieve your current holdings with live prices, quantities, cost basis, and unrealised gains for every position."""
    return client.fetch_positions()


@mcp.tool("search_specific_position_by_ticker")
def search_position_by_ticker(ticker: str) -> Position:
    """Look up a single position by its ticker symbol to get real-time details on that specific holding."""
    return client.search_position_by_ticker(ticker)
