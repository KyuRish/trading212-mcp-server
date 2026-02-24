from textwrap import dedent
from trading212_mcp_server.app import mcp, client


@mcp.prompt("analyse_trading212_data")
def analyse_trading212_data_prompt():
    """Build a context prompt for Trading 212 portfolio analysis."""
    try:
        account = client.fetch_account()
        currency = account.currency_code
    except Exception:
        currency = "unknown"

    return dedent(f"""\
        You have access to a Trading 212 investment account denominated in {currency}.

        There are four analytics tools at your disposal, each serving a distinct purpose:

        1. fetch_portfolio_summary
           Returns a full account snapshot including total value, cash balance,
           invested amount, overall profit/loss, and a breakdown of every position
           sorted by current value. Start here to get the big picture.

        2. fetch_portfolio_performance
           Provides a per-position performance report with individual P&L figures,
           dividend contributions, and the most recent filled orders. Use this when
           the user wants to know which holdings are winning or losing.

        3. fetch_dividend_summary
           Aggregates all historical dividend payments grouped by ticker and by
           calendar month. Ideal for answering questions about passive income,
           yield patterns, or dividend growth over time.

        4. fetch_recent_activity
           Merges order history and deposit/withdrawal transactions into a single
           chronological feed. Helpful for reviewing what happened recently without
           checking orders and transactions separately.

        Recommended workflow:
        - For broad questions ("how is my portfolio doing?"), call one of the
          composite tools above first. They combine multiple API calls internally,
          so a single invocation is usually enough.
        - Only fall back to individual endpoints (fetch_all_open_positions,
          fetch_historical_order_data, etc.) when you need data that the composite
          tools do not cover, such as pending limit orders or specific order IDs.

        Currency note: some instruments on the London Stock Exchange are quoted in
        GBX (pence sterling). 1 GBP = 100 GBX. Always convert GBX values to GBP
        before presenting them to the user so the numbers stay consistent.""")
