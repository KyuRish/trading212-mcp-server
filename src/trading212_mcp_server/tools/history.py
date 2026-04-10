from mcp.types import ToolAnnotations
from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import (
    HistoricalOrder, PaginatedDividends, PaginatedTransactions,
    Report, EnqueuedReport, ReportDataIncluded,
)

_READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)


@mcp.tool("fetch_historical_order_data", annotations=_READ)
def fetch_historical_order_data(
    cursor: int = None, ticker: str = None, limit: int = 20
) -> list[HistoricalOrder]:
    """
    Retrieve past orders (filled, cancelled, rejected) with execution details,
    fill prices, and timestamps. Supports pagination and ticker filtering.

    Use this to review trade history or to analyze past execution quality.
    For currently active orders, use fetch_all_orders instead.

    Args:
        cursor: Pagination cursor from a previous response. Omit for the first page.
        ticker: Filter results to a specific instrument (e.g., 'AAPL_US_EQ'). Omit for all.
        limit: Number of orders per page, 1-50. Defaults to 20.

    Returns:
        List of HistoricalOrder with ticker, type, status, filledQuantity, fillPrice,
        dateCreated, dateExecuted, and more
    """
    return client.fetch_order_history(cursor=cursor, ticker=ticker, limit=limit)


@mcp.tool("fetch_paid_out_dividends", annotations=_READ)
def fetch_paid_out_dividends(
    cursor: int = None, ticker: str = None, limit: int = 20
) -> PaginatedDividends:
    """
    Retrieve dividend payments received, including per-share amounts, payment dates,
    and total payouts. Supports pagination and ticker filtering.

    Use this to track income from dividend-paying stocks. For a summarized view
    grouped by ticker and month, use fetch_dividend_summary instead.

    Args:
        cursor: Pagination cursor from a previous response. Omit for the first page.
        ticker: Filter to a specific instrument (e.g., 'AAPL_US_EQ'). Omit for all.
        limit: Number of records per page, 1-50. Defaults to 20.

    Returns:
        PaginatedDividends with items (ticker, amount, paidOn, quantity) and nextPagePath
    """
    return client.fetch_dividends(cursor=cursor, ticker=ticker, limit=limit)


@mcp.tool("fetch_exports_list", annotations=_READ)
def fetch_exports_list() -> list[Report]:
    """
    List all previously generated CSV account exports with their status and
    download links.

    Use this to check if an export requested via request_csv_export is ready
    for download. Completed reports include a downloadLink field.

    Returns:
        List of Report objects with reportId, status, and downloadLink (when complete)
    """
    return client.fetch_reports()


@mcp.tool("request_csv_export", annotations=_WRITE)
def request_csv_export(
    include_dividends: bool = True,
    include_interest: bool = True,
    include_orders: bool = True,
    include_transactions: bool = True,
    time_from: str = None,
    time_to: str = None,
) -> EnqueuedReport:
    """
    Queue a CSV export of your account history. The export runs asynchronously -
    check fetch_exports_list to monitor progress and get the download link.

    This creates a server-side export job. Each call generates a new report.
    Use the time range parameters to limit the export to a specific period.

    Args:
        include_dividends: Include dividend payment records. Defaults to True.
        include_interest: Include interest payment records. Defaults to True.
        include_orders: Include trade/order history. Defaults to True.
        include_transactions: Include deposit/withdrawal records. Defaults to True.
        time_from: Start of the reporting window in ISO 8601 (e.g., '2024-01-01T00:00:00Z').
            Omit for all history.
        time_to: End of the reporting window in ISO 8601 (e.g., '2024-12-31T23:59:59Z').
            Omit for up to now.

    Returns:
        EnqueuedReport with the reportId for tracking via fetch_exports_list
    """
    data_included = ReportDataIncluded(
        include_dividends=include_dividends,
        include_interest=include_interest,
        include_orders=include_orders,
        include_transactions=include_transactions,
    )
    return client.request_export(
        data_included=data_included, time_from=time_from, time_to=time_to
    )


@mcp.tool("fetch_transaction_list", annotations=_READ)
def fetch_transaction_list(
    cursor: str | None = None, time: str | None = None, limit: int = 20
) -> PaginatedTransactions:
    """
    Retrieve account cash movements such as deposits, withdrawals, fees,
    interest payments, and internal transfers. Supports cursor-based pagination.

    Use this to audit account cash flow or to reconcile deposits/withdrawals.
    For a combined view of orders and transactions together, use fetch_recent_activity.

    Args:
        cursor: Pagination cursor from a previous response. Omit for the first page.
        time: Filter transactions from this ISO 8601 timestamp onward
            (e.g., '2024-06-01T00:00:00Z'). Omit for all.
        limit: Number of records per page, 1-50. Defaults to 20.

    Returns:
        PaginatedTransactions with items (type, dateTime, amount, reference) and nextPagePath
    """
    return client.fetch_transactions(cursor=cursor, time=time, limit=limit)
