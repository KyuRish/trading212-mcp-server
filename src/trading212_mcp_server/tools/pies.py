from typing import Optional
from datetime import datetime

from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import (
    PieSummary, PieDetails, DividendCashAction,
    PieRequest, DuplicatePieRequest,
)


@mcp.tool("fetch_pies")
def fetch_pies() -> list[PieSummary]:
    """List all your pies with their cash balances, dividend info, goal progress, and investment performance."""
    return client.fetch_pies()


@mcp.tool("fetch_a_pie")
def fetch_a_pie(pie_id: int) -> PieDetails:
    """Get full details for a single pie including every instrument allocation, current settings, and per-instrument results."""
    return client.fetch_pie(pie_id)


@mcp.tool("create_pie")
def create_pie(
    name: str,
    instrument_shares: dict[str, float],
    dividend_cash_action: Optional[DividendCashAction] = None,
    end_date: Optional[datetime] = None,
    goal: Optional[float] = None,
    icon: Optional[str] = None,
) -> PieDetails:
    """
    Build a new pie with the given instruments and weights.

    Args:
        name: Display name for the pie
        instrument_shares: Mapping of instrument tickers to their target weights
            (e.g., {'AAPL_US_EQ': 0.5, 'MSFT_US_EQ': 0.5})
        dividend_cash_action: What to do with dividends - REINVEST or TO_ACCOUNT_CASH
        end_date: Optional target end date in ISO 8601 format
            (e.g., '2025-12-31T23:59:59Z')
        goal: Target total value for the pie in your account currency
        icon: Identifier for the pie icon

    Returns:
        PieDetails: Full details of the newly created pie
    """
    pie_data = PieRequest(
        name=name, instrument_shares=instrument_shares,
        dividend_cash_action=dividend_cash_action,
        end_date=end_date, goal=goal, icon=icon,
    )
    return client.create_pie(pie_data)


@mcp.tool("update_pie")
def update_pie(
    pie_id: int,
    name: str = None,
    instrument_shares: dict[str, float] = None,
    dividend_cash_action: Optional[DividendCashAction] = None,
    end_date: Optional[datetime] = None,
    goal: Optional[float] = None,
    icon: Optional[str] = None,
) -> PieDetails:
    """
    Modify an existing pie's configuration. You must provide a new name when updating.

    Args:
        pie_id: Numeric ID of the pie to modify
        name: Updated name for the pie (required by the API)
        instrument_shares: New ticker-to-weight mapping
            (e.g., {'AAPL_US_EQ': 0.5, 'MSFT_US_EQ': 0.5})
        dividend_cash_action: Updated dividend handling - REINVEST or TO_ACCOUNT_CASH
        end_date: Revised end date in ISO 8601 format
            (e.g., '2025-12-31T23:59:59Z')
        goal: Revised target value in account currency
        icon: Updated icon identifier

    Returns:
        PieDetails: The pie after applying your changes
    """
    pie_data = PieRequest(
        name=name, instrument_shares=instrument_shares,
        dividend_cash_action=dividend_cash_action,
        end_date=end_date, goal=goal, icon=icon,
    )
    return client.update_pie(pie_id, pie_data)


@mcp.tool("duplicate_pie")
def duplicate_pie(
    pie_id: int, name: Optional[str] = None, icon: Optional[str] = None
) -> PieDetails:
    """
    Clone an existing pie into a new one with identical instrument allocations.

    Args:
        pie_id: ID of the source pie to copy
        name: Optional custom name for the clone
        icon: Optional icon for the clone

    Returns:
        PieDetails: Full details of the newly cloned pie
    """
    req = DuplicatePieRequest(name=name, icon=icon)
    return client.duplicate_pie(pie_id, req)


@mcp.tool("delete_pie")
def delete_pie(pie_id: int):
    """Permanently remove a pie. Instruments inside it become standalone positions in your portfolio."""
    return client.delete_pie(pie_id)
