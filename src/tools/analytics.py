from datetime import datetime
from app import mcp, client


@mcp.tool("fetch_portfolio_summary")
def fetch_portfolio_summary() -> dict:
    """
    Get a complete portfolio snapshot in a single call.

    Combines account info, cash balance, and all open positions into one
    response with calculated totals and allocation breakdown.

    Returns:
        dict with keys: currency, total_value, cash, invested, profit_loss,
        profit_loss_pct, position_count, positions (sorted by value),
        top_holdings (top 5 by value)
    """
    account = client.get_account_info()
    cash = client.get_account_cash()
    positions = client.get_account_positions()

    holdings = []
    for pos in positions:
        current_value = (pos.currentPrice or 0) * (pos.quantity or 0)
        holdings.append({
            "ticker": pos.ticker,
            "quantity": pos.quantity,
            "average_price": pos.averagePrice,
            "current_price": pos.currentPrice,
            "current_value": round(current_value, 2),
            "profit_loss": round(pos.ppl or 0, 2),
            "profit_loss_pct": round(
                ((pos.ppl or 0) / ((pos.averagePrice or 1) * (pos.quantity or 1))) * 100, 2
            ) if pos.averagePrice and pos.quantity else 0,
        })

    holdings.sort(key=lambda h: h["current_value"], reverse=True)

    total = cash.total or 0
    invested = cash.invested or 0
    ppl = cash.ppl or 0

    return {
        "currency": account.currencyCode,
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
    Analyze portfolio performance with per-position P&L breakdown.

    Combines current positions, recent order history, and dividend payouts
    to build a performance report.

    Returns:
        dict with keys: currency, total_return, total_dividends,
        best_performer, worst_performer, positions (with individual P&L
        and dividends), recent_orders (last 20 filled orders)
    """
    account = client.get_account_info()
    positions = client.get_account_positions()
    orders = client.get_historical_order_data(limit=50)
    dividends = client.get_dividends(limit=50)

    # Build per-ticker dividend totals
    div_by_ticker = {}
    for item in dividends.items:
        t = item.ticker or "unknown"
        div_by_ticker[t] = div_by_ticker.get(t, 0) + (item.amount or 0)

    total_dividends = sum(div_by_ticker.values())

    # Build per-position performance
    perf = []
    for pos in positions:
        ticker = pos.ticker or ""
        invested = (pos.averagePrice or 0) * (pos.quantity or 0)
        current = (pos.currentPrice or 0) * (pos.quantity or 0)
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
            "held_since": pos.initialFillDate.isoformat() if pos.initialFillDate else None,
        })

    perf.sort(key=lambda p: p["total_return"], reverse=True)

    # Recent filled orders
    filled = [
        {
            "ticker": o.ticker,
            "type": o.type.value if o.type else None,
            "quantity": o.filledQuantity,
            "fill_price": o.fillPrice,
            "date": o.dateExecuted.isoformat() if o.dateExecuted else None,
            "status": o.status.value if o.status else None,
        }
        for o in orders if o.status and o.status.value == "FILLED"
    ][:20]

    return {
        "currency": account.currencyCode,
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
    Analyze dividend income across your portfolio.

    Fetches all available dividend history and groups it by ticker and by
    month to show income patterns.

    Returns:
        dict with keys: total_dividends, by_ticker (sorted by amount),
        by_month (chronological), currency
    """
    account = client.get_account_info()

    # Fetch up to 200 dividends (4 pages)
    all_divs = []
    cursor = None
    for _ in range(4):
        page = client.get_dividends(cursor=cursor, limit=50)
        all_divs.extend(page.items)
        if not page.nextPagePath:
            break
        # Extract cursor from nextPagePath
        try:
            cursor = int(page.nextPagePath.split("cursor=")[1].split("&")[0])
        except (IndexError, ValueError):
            break

    # Group by ticker
    by_ticker = {}
    for d in all_divs:
        t = d.ticker or "unknown"
        by_ticker[t] = by_ticker.get(t, 0) + (d.amount or 0)

    ticker_list = [
        {"ticker": t, "total": round(v, 2)}
        for t, v in sorted(by_ticker.items(), key=lambda x: x[1], reverse=True)
    ]

    # Group by month
    by_month = {}
    for d in all_divs:
        if d.paidOn:
            key = d.paidOn.strftime("%Y-%m")
            by_month[key] = by_month.get(key, 0) + (d.amount or 0)

    month_list = [
        {"month": m, "total": round(v, 2)}
        for m, v in sorted(by_month.items())
    ]

    total = sum(d.amount or 0 for d in all_divs)
    months_span = len(by_month) or 1

    return {
        "currency": account.currencyCode,
        "total_dividends": round(total, 2),
        "dividend_count": len(all_divs),
        "average_monthly": round(total / months_span, 2),
        "by_ticker": ticker_list,
        "by_month": month_list,
    }


@mcp.tool("fetch_recent_activity")
def fetch_recent_activity(limit: int = 20) -> dict:
    """
    Get a combined timeline of recent trades and account transactions.

    Merges order history and deposit/withdrawal transactions into a single
    chronological feed.

    Args:
        limit: Number of items to fetch from each source (max 50, default 20)

    Returns:
        dict with keys: currency, activity (merged timeline sorted by date,
        each item has type 'order' or 'transaction'), order_count,
        transaction_count
    """
    account = client.get_account_info()
    orders = client.get_historical_order_data(limit=min(limit, 50))
    txns = client.get_history_transactions(limit=min(limit, 50))

    activity = []

    for o in orders:
        activity.append({
            "type": "order",
            "date": o.dateExecuted.isoformat() if o.dateExecuted else (
                o.dateCreated.isoformat() if o.dateCreated else None
            ),
            "ticker": o.ticker,
            "order_type": o.type.value if o.type else None,
            "status": o.status.value if o.status else None,
            "quantity": o.filledQuantity or o.orderedQuantity,
            "fill_price": o.fillPrice,
            "value": o.filledValue or o.orderedValue,
        })

    for t in txns.items:
        activity.append({
            "type": "transaction",
            "date": t.dateTime.isoformat() if t.dateTime else None,
            "transaction_type": t.type.value if t.type else None,
            "amount": t.amount,
            "reference": t.reference,
        })

    activity.sort(key=lambda a: a.get("date") or "", reverse=True)

    return {
        "currency": account.currencyCode,
        "activity": activity,
        "order_count": len(orders),
        "transaction_count": len(txns.items),
    }
