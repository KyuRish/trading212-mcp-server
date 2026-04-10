from datetime import datetime
from mcp.types import ToolAnnotations
from trading212_mcp_server.app import mcp, client

_READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)


@mcp.tool("fetch_portfolio_summary", annotations=_READ)
def fetch_portfolio_summary() -> dict:
    """
    Produce a complete portfolio snapshot in one call by combining account info,
    cash balance, and all open positions into a single aggregated response.

    This is the recommended starting point for portfolio analysis. It calculates
    total value, P/L percentages, and ranks holdings by current value. For
    per-position performance with dividends, use fetch_portfolio_performance instead.

    Returns:
        dict with currency, total_value, cash_available, invested, profit_loss,
        profit_loss_pct, position_count, positions (sorted by value descending),
        and top_holdings (top 5)
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

    result = {
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
    waited = client.drain_wait_time()
    if waited:
        result["_note"] = f"Response delayed {waited}s due to Trading 212 rate limits."
    return result


@mcp.tool("fetch_portfolio_performance", annotations=_READ)
def fetch_portfolio_performance() -> dict:
    """
    Build a detailed performance report across all positions by combining
    current holdings, recent order history, and dividend payouts.

    Calculates per-position total returns (price P/L + dividends) and identifies
    best and worst performers. Use this for deeper analysis than fetch_portfolio_summary
    provides, especially when dividend income matters.

    Returns:
        dict with currency, total_price_ppl, total_dividends, total_return,
        best_performer, worst_performer, positions (each with invested, current_value,
        price_ppl, dividends, total_return, return_pct, held_since), recent_filled_orders
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

    result = {
        "currency": account.currency_code,
        "total_price_ppl": round(sum(p["price_ppl"] for p in perf), 2),
        "total_dividends": round(total_dividends, 2),
        "total_return": round(sum(p["total_return"] for p in perf), 2),
        "best_performer": perf[0] if perf else None,
        "worst_performer": perf[-1] if perf else None,
        "positions": perf,
        "recent_filled_orders": filled,
    }
    waited = client.drain_wait_time()
    if waited:
        result["_note"] = f"Response delayed {waited}s due to Trading 212 rate limits."
    return result


@mcp.tool("fetch_dividend_summary", annotations=_READ)
def fetch_dividend_summary() -> dict:
    """
    Analyse dividend income history by collecting up to 200 dividend records
    and breaking them down by ticker and by calendar month.

    Use this to identify which holdings generate the most income and to spot
    monthly income trends. For raw dividend records with pagination control,
    use fetch_paid_out_dividends instead.

    Returns:
        dict with currency, total_dividends, dividend_count, average_monthly,
        by_ticker (sorted highest-paying first), by_month (chronological)
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

    result = {
        "currency": account.currency_code,
        "total_dividends": round(total, 2),
        "dividend_count": len(all_divs),
        "average_monthly": round(total / months_span, 2),
        "by_ticker": ticker_list,
        "by_month": month_list,
    }
    waited = client.drain_wait_time()
    if waited:
        result["_note"] = f"Response delayed {waited}s due to Trading 212 rate limits."
    return result


@mcp.tool("fetch_recent_activity", annotations=_READ)
def fetch_recent_activity(limit: int = 20) -> dict:
    """
    Get a unified timeline of recent trades and account movements by merging
    order history with deposit/withdrawal transactions into a single
    chronologically sorted feed.

    Use this for a quick "what happened recently" overview. Each entry is tagged
    as either 'order' (trade) or 'transaction' (cash movement). For separate
    access, use fetch_historical_order_data or fetch_transaction_list.

    Args:
        limit: How many items to pull from each source (orders and transactions
            separately), 1-50. Defaults to 20. Total activity items may be up to 2x this.

    Returns:
        dict with currency, activity (sorted newest-first, each tagged as 'order' or
        'transaction'), order_count, transaction_count
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

    result = {
        "currency": account.currency_code,
        "activity": activity,
        "order_count": len(orders),
        "transaction_count": len(txns.items),
    }
    waited = client.drain_wait_time()
    if waited:
        result["_note"] = f"Response delayed {waited}s due to Trading 212 rate limits."
    return result
