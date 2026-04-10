from mcp.types import ToolAnnotations
from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import Account, Cash, Position

_READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)


@mcp.tool("fetch_account_info", annotations=_READ)
def fetch_account_info() -> Account:
    """
    Retrieve account metadata such as the account currency and unique identifier.

    Use this as a starting point to determine the account's base currency before
    interpreting monetary values from other tools. Safe to call frequently.

    Returns:
        Account with id (int) and currencyCode (e.g., 'EUR', 'GBP', 'USD')
    """
    return client.fetch_account()


@mcp.tool("fetch_account_cash", annotations=_READ)
def fetch_account_cash() -> Cash:
    """
    Get a detailed breakdown of the account balance including available cash,
    invested capital, profit/loss, blocked funds, and pie cash.

    Use this to check buying power before placing orders, or to understand
    the overall account health. See also: fetch_portfolio_summary for a
    richer overview that includes individual positions.

    Returns:
        Cash with free, invested, total, ppl (profit/loss), result, blocked, pieCash
    """
    return client.fetch_cash()


@mcp.tool("fetch_all_open_positions", annotations=_READ)
def fetch_all_open_positions() -> list[Position]:
    """
    Retrieve every open position in the portfolio with live prices, quantities,
    cost basis, and unrealised gains.

    Use this to get a complete view of current holdings. Each position includes
    the ticker, quantity, averagePrice, currentPrice, and ppl (profit/loss).
    Positions held inside pies show a non-zero pieQuantity field.

    See also: search_specific_position_by_ticker for a single position lookup,
    or fetch_portfolio_summary for an aggregated portfolio view.

    Returns:
        List of Position objects, one per held instrument
    """
    return client.fetch_positions()


@mcp.tool("search_specific_position_by_ticker", annotations=_READ)
def search_position_by_ticker(ticker: str) -> Position:
    """
    Look up a single open position by its exact ticker symbol.

    Use this when you need details on one specific holding without fetching the
    entire portfolio. Returns the same Position data as fetch_all_open_positions
    but for a single instrument.

    Args:
        ticker: The exact Trading 212 ticker symbol (e.g., 'AAPL_US_EQ', 'IGLDd_EQ').
            Use search_instrument to find the correct ticker if unsure.

    Returns:
        Position with ticker, quantity, averagePrice, currentPrice, ppl, and more
    """
    return client.search_position_by_ticker(ticker)
