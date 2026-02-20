from app import mcp, client
from models import (
    HistoricalOrder, PaginatedResponseHistoryDividendItem,
    PaginatedResponseHistoryTransactionItem,
    ReportResponse, EnqueuedReportResponse, ReportDataIncluded,
)


@mcp.tool("fetch_historical_order_data")
def fetch_historical_order_data(
    cursor: int = None, ticker: str = None, limit: int = 20
) -> list[HistoricalOrder]:
    """Fetch historical order data with pagination."""
    return client.get_historical_order_data(cursor=cursor, ticker=ticker, limit=limit)


@mcp.tool("fetch_paid_out_dividends")
def fetch_paid_out_dividends(
    cursor: int = None, ticker: str = None, limit: int = 20
) -> PaginatedResponseHistoryDividendItem:
    """Fetch historical dividend data with pagination."""
    return client.get_dividends(cursor=cursor, ticker=ticker, limit=limit)


@mcp.tool("fetch_exports_list")
def fetch_exports_list() -> list[ReportResponse]:
    """Lists detailed information about all csv account exports."""
    return client.get_reports()


@mcp.tool("request_csv_export")
def request_csv_export(
    include_dividends: bool = True,
    include_interest: bool = True,
    include_orders: bool = True,
    include_transactions: bool = True,
    time_from: str = None,
    time_to: str = None,
) -> EnqueuedReportResponse:
    """
    Request a CSV export of the account's orders, dividends and transactions
    history.
    Once the export is complete it can be accessed from the download link in the
     exports list.

    Args:
        include_dividends: Whether to include dividend information in the export.
            Defaults to True
        include_interest: Whether to include interest information in the export.
        Defaults to True
        include_orders: Whether to include order history in the export.
        Defaults to True
        include_transactions: Whether to include transaction history in the export.
        Defaults to True
        time_from: Start time for the report in ISO 8601 format
        (e.g., '2023-01-01T00:00:00Z')
        time_to: End time for the report in ISO 8601 format
        (e.g., '2023-12-31T23:59:59Z')

    Returns:
        EnqueuedReportResponse: Response containing the report ID and status
    """
    data_included = ReportDataIncluded(
        includeDividends=include_dividends,
        includeInterest=include_interest,
        includeOrders=include_orders,
        includeTransactions=include_transactions,
    )
    return client.request_export(
        data_included=data_included, time_from=time_from, time_to=time_to
    )


@mcp.tool("fetch_transaction_list")
def fetch_transaction_list(
    cursor: str | None = None, time: str | None = None, limit: int = 20
) -> PaginatedResponseHistoryTransactionItem:
    """Fetch superficial information about movements to and from your
    account."""
    return client.get_history_transactions(cursor=cursor, time=time, limit=limit)
