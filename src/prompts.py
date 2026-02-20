from textwrap import dedent
from app import mcp, client


@mcp.prompt("analyse_trading212_data")
def analyse_trading212_data_prompt():
    """Provide context for analyzing the user's Trading 212 portfolio."""
    try:
        account = client.get_account_info()
        currency = account.currencyCode
    except Exception:
        currency = "unknown"

    return dedent(f"""\
        You are analyzing a Trading 212 investment account.
        Account currency: {currency}

        Note: GBX means pence (1/100 of GBP). Convert to GBP for display.

        Available analytics tools:
        - fetch_portfolio_summary: complete snapshot (value, P&L, allocations)
        - fetch_portfolio_performance: per-position returns with dividends
        - fetch_dividend_summary: income analysis by ticker and month
        - fetch_recent_activity: combined timeline of trades and transactions

        Use these composite tools first for a high-level view before drilling
        into individual positions or orders.""")
