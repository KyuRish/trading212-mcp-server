from typing import Optional
from datetime import datetime

from app import mcp, client
from models import (
    AccountBucketResultResponse, AccountBucketInstrumentsDetailedResponse,
    DividendCashActionEnum, PieRequest, DuplicateBucketRequest,
)


@mcp.tool("fetch_pies")
def fetch_pies() -> list[AccountBucketResultResponse]:
    """Fetch all pies."""
    return client.get_pies()


@mcp.tool("fetch_a_pie")
def fetch_a_pie(pie_id: int) -> AccountBucketResultResponse:
    """Fetch a specific pie by ID."""
    return client.get_pie_by_id(pie_id)


@mcp.tool("create_pie")
def create_pie(
    name: str,
    instrument_shares: dict[str, float],
    dividend_cash_action: Optional[DividendCashActionEnum] = None,
    end_date: Optional[datetime] = None,
    goal: Optional[float] = None,
    icon: Optional[str] = None,
) -> AccountBucketInstrumentsDetailedResponse:
    """
    Create a new pie with the specified parameters.

    Args:
        name: Name of the pie
        instrument_shares: Dictionary mapping instrument tickers to their
        weights in the pie
            (e.g., {'AAPL_US_EQ': 0.5, 'MSFT_US_EQ': 0.5})
        dividend_cash_action: How dividends are handled. Defaults to REINVEST.
            Possible values: REINVEST, TO_ACCOUNT_CASH
        end_date: Optional end date for the pie in ISO 8601 format
            (e.g., '2024-12-31T23:59:59Z')
        goal: Total desired value of the pie in account currency
        icon: Optional icon identifier for the pie

    Returns:
        AccountBucketInstrumentsDetailedResponse: Details of the created pie
    """
    pie_data = PieRequest(
        name=name, instrumentShares=instrument_shares,
        dividendCashAction=dividend_cash_action,
        endDate=end_date, goal=goal, icon=icon,
    )
    return client.create_pie(pie_data)


@mcp.tool("update_pie")
def update_pie(
    pie_id: int,
    name: str = None,
    instrument_shares: dict[str, float] = None,
    dividend_cash_action: Optional[DividendCashActionEnum] = None,
    end_date: Optional[datetime] = None,
    goal: Optional[float] = None,
    icon: Optional[str] = None,
) -> AccountBucketInstrumentsDetailedResponse:
    """
    Update an existing pie with new parameters. The pie must be renamed when
    updating it.

    Args:
        pie_id: ID of the pie to update
        name: New name for the pie. Required when updating a pie.
        instrument_shares: Dictionary mapping instrument tickers to their new
        weights in the pie
            (e.g., {'AAPL_US_EQ': 0.5, 'MSFT_US_EQ': 0.5})
        dividend_cash_action: How dividends should be handled.
            Possible values: REINVEST, TO_ACCOUNT_CASH
        end_date: New end date for the pie in ISO 8601 format
            (e.g., '2024-12-31T23:59:59Z')
        goal: New total desired value of the pie in account currency
        icon: New icon identifier for the pie

    Returns:
        AccountBucketInstrumentsDetailedResponse: Updated details of the pie
    """
    pie_data = PieRequest(
        name=name, instrumentShares=instrument_shares,
        dividendCashAction=dividend_cash_action,
        endDate=end_date, goal=goal, icon=icon,
    )
    return client.update_pie(pie_id, pie_data)


@mcp.tool("duplicate_pie")
def duplicate_pie(
    pie_id: int, name: Optional[str] = None, icon: Optional[str] = None
) -> AccountBucketResultResponse:
    """
    Create a duplicate of an existing pie.

    Args:
        pie_id: ID of the pie to duplicate
        name: Optional new name for the duplicated pie
        icon: Optional new icon for the duplicated pie

    Returns:
        AccountBucketResultResponse: Details of the duplicated pie
    """
    duplicate_request = DuplicateBucketRequest(name=name, icon=icon)
    return client.duplicate_pie(pie_id, duplicate_request)


@mcp.tool("delete_pie")
def delete_pie(pie_id: int):
    """Delete a pie."""
    return client.delete_pie(pie_id)
