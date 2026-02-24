from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import (
    HistoricalOrder, PaginatedDividends, PaginatedTransactions,
    Report, EnqueuedReport, ReportDataIncluded,
)


@mcp.tool("fetch_historical_order_data")
def fetch_historical_order_data(
    cursor: int = None, ticker: str = None, limit: int = 20
) -> list[HistoricalOrder]:
    """Retrieve past orders (filled, cancelled, rejected) along with their execution details and timestamps."""
    return client.fetch_order_history(cursor=cursor, ticker=ticker, limit=limit)


@mcp.tool("fetch_paid_out_dividends")
def fetch_paid_out_dividends(
    cursor: int = None, ticker: str = None, limit: int = 20
) -> PaginatedDividends:
    """Retrieve dividend payouts you have received, including per-share amounts, payment dates, and totals."""
    return client.fetch_dividends(cursor=cursor, ticker=ticker, limit=limit)


@mcp.tool("fetch_exports_list")
def fetch_exports_list() -> list[Report]:
    """Get a list of all previously generated CSV account exports with their status and download links."""
    return client.fetch_reports()


@mcp.tool("request_csv_export")
def request_csv_export(
    include_dividends: bool = True,
    include_interest: bool = True,
    include_orders: bool = True,
    include_transactions: bool = True,
    time_from: str = None,
    time_to: str = None,
) -> EnqueuedReport:
    """
    Queue a CSV export of your account history. When finished, the download
    link appears in the exports list.

    Args:
        include_dividends: Add dividend records to the export. Defaults to True.
        include_interest: Add interest records to the export. Defaults to True.
        include_orders: Add order history to the export. Defaults to True.
        include_transactions: Add deposit/withdrawal records. Defaults to True.
        time_from: Start of the reporting window in ISO 8601
            (e.g., '2024-01-01T00:00:00Z')
        time_to: End of the reporting window in ISO 8601
            (e.g., '2024-12-31T23:59:59Z')

    Returns:
        EnqueuedReport: Confirmation with the report ID for tracking
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


@mcp.tool("fetch_transaction_list")
def fetch_transaction_list(
    cursor: str | None = None, time: str | None = None, limit: int = 20
) -> PaginatedTransactions:
    """Retrieve account movements such as deposits, withdrawals, fees, and internal transfers with pagination support."""
    return client.fetch_transactions(cursor=cursor, time=time, limit=limit)
