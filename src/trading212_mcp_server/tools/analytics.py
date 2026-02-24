from datetime import datetime
from trading212_mcp_server.app import mcp, client


@mcp.tool("fetch_portfolio_summary")
def fetch_portfolio_summary() -> dict:
    """
    Produce a full portfolio snapshot in one call.

    Pulls account info, cash balance, and every open position, then
    calculates totals and ranks holdings by value.

    Returns:
        dict with keys: currency, total_value, cash_available, invested,
        profit_loss, profit_loss_pct, position_count, positions (by value
        descending), top_holdings (top 5)
    """
    account = client.fetch_account()
    cash = client.fetch_cash()
    positions = client.fetch_positions()

    holdings = []
    for pos in positions:
        current_value = (pos.current_price or 0) * (pos.quantity or 0)
        holdings.append({
            "ticker": pos.ticker,
            "quantity": pos.quantity,
            "average_price": pos.average_price,
            "current_price": pos.current_price,
            "current_value": round(current_value, 2),
            "profit_loss": round(pos.ppl or 0, 2),
            "profit_loss_pct": round(
                ((pos.ppl or 0) / ((pos.average_price or 1) * (pos.quantity or 1))) * 100, 2
            ) if pos.average_price and pos.quantity else 0,
        })

    holdings.sort(key=lambda h: h["current_value"], reverse=True)

    total = cash.total or 0
    invested = cash.invested or 0
    ppl = cash.ppl or 0

    return {
        "currency": account.currency_code,
        "total_value": round(total, 2),
        "cash_available": round(cash.free or 0, 2),
        "invested": round(invested, 2),
        "profit_loss": round(ppl, 2),
        "profit_loss_pct": round((ppl / invested) * 100, 2) if invested else 0,
        "position_count": len(positions),
        "positions": holdings,
        "top_holdings": holdings[:5],
    }


@mcp.tool("fetch_portfolio_performance")
def fetch_portfolio_performance() -> dict:
    """
    Build a performance report across all positions.

    Gathers current holdings, recent order history, and dividend payouts
    to calculate per-position returns and identify top/bottom performers.

    Returns:
        dict with keys: currency, total_price_ppl, total_dividends,
        total_return, best_performer, worst_performer, positions
        (with individual P/L and dividends), recent_filled_orders
    """
    account = client.fetch_account()
    positions = client.fetch_positions()
    orders = client.fetch_order_history(limit=50)
    dividends = client.fetch_dividends(limit=50)

    # Aggregate dividends per ticker
    div_by_ticker = {}
    for item in dividends.items:
        t = item.ticker or "unknown"
        div_by_ticker[t] = div_by_ticker.get(t, 0) + (item.amount or 0)

    total_dividends = sum(div_by_ticker.values())

    # Per-position performance
    perf = []
    for pos in positions:
        ticker = pos.ticker or ""
        invested = (pos.average_price or 0) * (pos.quantity or 0)
        current = (pos.current_price or 0) * (pos.quantity or 0)
        ppl = pos.ppl or 0
        divs = round(div_by_ticker.get(ticker, 0), 2)
        total_return = round(ppl + divs, 2)

        perf.append({
            "ticker": ticker,
            "quantity": pos.quantity,
            "invested": round(invested, 2),
            "current_value": round(current, 2),
            "price_ppl": round(ppl, 2),
            "dividends": divs,
            "total_return": total_return,
            "return_pct": round((total_return / invested) * 100, 2) if invested else 0,
            "held_since": pos.initial_fill_date.isoformat() if pos.initial_fill_date else None,
        })

    perf.sort(key=lambda p: p["total_return"], reverse=True)

    # Recent filled orders
    filled = [
        {
            "ticker": o.ticker,
            "type": o.type.value if o.type else None,
            "quantity": o.filled_quantity,
            "fill_price": o.fill_price,
            "date": o.date_executed.isoformat() if o.date_executed else None,
            "status": o.status.value if o.status else None,
        }
        for o in orders if o.status and o.status.value == "FILLED"
    ][:20]

    return {
        "currency": account.currency_code,
        "total_price_ppl": round(sum(p["price_ppl"] for p in perf), 2),
        "total_dividends": round(total_dividends, 2),
        "total_return": round(sum(p["total_return"] for p in perf), 2),
        "best_performer": perf[0] if perf else None,
        "worst_performer": perf[-1] if perf else None,
        "positions": perf,
        "recent_filled_orders": filled,
    }


@mcp.tool("fetch_dividend_summary")
def fetch_dividend_summary() -> dict:
    """
    Analyse your dividend income history.

    Collects up to 200 dividend records and breaks them down by ticker
    and by calendar month to reveal income trends.

    Returns:
        dict with keys: currency, total_dividends, dividend_count,
        average_monthly, by_ticker (highest first), by_month (chronological)
    """
    account = client.fetch_account()

    # Collect up to 200 dividends across 4 pages
    all_divs = []
    cursor = None
    for _ in range(4):
        page = client.fetch_dividends(cursor=cursor, limit=50)
        all_divs.extend(page.items)
        if not page.next_page_path:
            break
        # Pull cursor value from the next page URL
        try:
            cursor = int(page.next_page_path.split("cursor=")[1].split("&")[0])
        except (IndexError, ValueError):
            break

    # Totals per ticker
    by_ticker = {}
    for d in all_divs:
        t = d.ticker or "unknown"
        by_ticker[t] = by_ticker.get(t, 0) + (d.amount or 0)

    ticker_list = [
        {"ticker": t, "total": round(v, 2)}
        for t, v in sorted(by_ticker.items(), key=lambda x: x[1], reverse=True)
    ]

    # Totals per month
    by_month = {}
    for d in all_divs:
        if d.paid_on:
            key = d.paid_on.strftime("%Y-%m")
            by_month[key] = by_month.get(key, 0) + (d.amount or 0)

    month_list = [
        {"month": m, "total": round(v, 2)}
        for m, v in sorted(by_month.items())
    ]

    total = sum(d.amount or 0 for d in all_divs)
    months_span = len(by_month) or 1

    return {
        "currency": account.currency_code,
        "total_dividends": round(total, 2),
        "dividend_count": len(all_divs),
        "average_monthly": round(total / months_span, 2),
        "by_ticker": ticker_list,
        "by_month": month_list,
    }


@mcp.tool("fetch_recent_activity")
def fetch_recent_activity(limit: int = 20) -> dict:
    """
    Get a unified timeline of recent trades and account movements.

    Merges order history with deposit/withdrawal transactions into a
    single chronologically sorted feed.

    Args:
        limit: How many items to pull from each source (capped at 50, default 20)

    Returns:
        dict with keys: currency, activity (merged and sorted newest-first,
        each entry tagged as 'order' or 'transaction'), order_count,
        transaction_count
    """
    account = client.fetch_account()
    orders = client.fetch_order_history(limit=min(limit, 50))
    txns = client.fetch_transactions(limit=min(limit, 50))

    activity = []

    for o in orders:
        activity.append({
            "type": "order",
            "date": o.date_executed.isoformat() if o.date_executed else (
                o.date_created.isoformat() if o.date_created else None
            ),
            "ticker": o.ticker,
            "order_type": o.type.value if o.type else None,
            "status": o.status.value if o.status else None,
            "quantity": o.filled_quantity or o.ordered_quantity,
            "fill_price": o.fill_price,
            "value": o.filled_value or o.ordered_value,
        })

    for t in txns.items:
        activity.append({
            "type": "transaction",
            "date": t.date_time.isoformat() if t.date_time else None,
            "transaction_type": t.type.value if t.type else None,
            "amount": t.amount,
            "reference": t.reference,
        })

    activity.sort(key=lambda a: a.get("date") or "", reverse=True)

    return {
        "currency": account.currency_code,
        "activity": activity,
        "order_count": len(orders),
        "transaction_count": len(txns.items),
    }
