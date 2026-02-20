from app import mcp, client
from models import Account, Cash, Position


@mcp.tool("fetch_account_info")
def fetch_account_info() -> Account:
    """Fetch account metadata."""
    return client.get_account_info()


@mcp.tool("fetch_account_cash")
def fetch_account_cash() -> Cash:
    """Fetch account cash balance."""
    return client.get_account_cash()


@mcp.tool("fetch_all_open_positions")
def fetch_all_open_positions() -> list[Position]:
    """Fetch all open positions."""
    return client.get_account_positions()


@mcp.tool("search_specific_position_by_ticker")
def search_position_by_ticker(ticker: str) -> Position:
    """Search for a position by ticker using POST endpoint."""
    return client.search_position_by_ticker(ticker)
