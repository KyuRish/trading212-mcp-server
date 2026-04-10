from typing import Optional
from datetime import datetime

from mcp.types import ToolAnnotations
from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import (
    PieSummary, PieDetails, DividendCashAction,
    PieRequest, DuplicatePieRequest,
)

_READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
_DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True)


@mcp.tool("fetch_pies", annotations=_READ)
def fetch_pies() -> list[PieSummary]:
    """
    List all investment pies with their cash balances, dividend details,
    goal progress, and overall investment performance.

    Use this to get an overview of all pies before drilling into a specific one
    with fetch_a_pie. Each pie includes its numeric ID needed for other pie operations.

    Returns:
        List of PieSummary objects with id, status, cash, progress, result, dividendDetails
    """
    return client.fetch_pies()


@mcp.tool("fetch_a_pie", annotations=_READ)
def fetch_a_pie(pie_id: int) -> PieDetails:
    """
    Get full details for a single pie including every instrument allocation,
    current vs target weights, per-instrument P/L, and pie settings.

    Use fetch_pies first to get the list of pie IDs, then call this for
    detailed breakdown of a specific pie.

    Args:
        pie_id: Numeric ID of the pie (e.g., 6894572). Get this from fetch_pies.

    Returns:
        PieDetails with settings (name, goal, endDate, dividendCashAction) and
        instruments (ticker, expectedShare, currentShare, ownedQuantity, result)
    """
    return client.fetch_pie(pie_id)


@mcp.tool("create_pie", annotations=_WRITE)
def create_pie(
    name: str,
    instrument_shares: dict[str, float],
    dividend_cash_action: Optional[DividendCashAction] = None,
    end_date: Optional[datetime] = None,
    goal: Optional[float] = None,
    icon: Optional[str] = None,
) -> PieDetails:
    """
    Create a new investment pie with the given instruments and target weights.
    This creates a real pie in your account - instruments will be purchased
    when you fund the pie.

    Use search_instrument to find valid ticker symbols before creating. Weights
    must sum to 1.0 (100%). See also: duplicate_pie to clone an existing pie.

    Args:
        name: Display name for the pie (e.g., 'Tech Growth')
        instrument_shares: Mapping of ticker to target weight, must sum to 1.0.
            Example: {'AAPL_US_EQ': 0.5, 'MSFT_US_EQ': 0.3, 'NVDA_US_EQ': 0.2}
        dividend_cash_action: REINVEST (buy more shares) or TO_ACCOUNT_CASH (withdraw to cash).
            Defaults to REINVEST if not specified.
        end_date: Optional target date in ISO 8601 (e.g., '2029-12-31T23:59:59Z')
        goal: Optional target value in account currency (e.g., 20000.0)
        icon: Optional pie icon identifier (e.g., 'Coins', 'Education')

    Returns:
        PieDetails: Full details of the newly created pie
    """
    pie_data = PieRequest(
        name=name, instrument_shares=instrument_shares,
        dividend_cash_action=dividend_cash_action,
        end_date=end_date, goal=goal, icon=icon,
    )
    return client.create_pie(pie_data)


@mcp.tool("update_pie", annotations=_WRITE)
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
    Modify an existing pie's settings, instrument allocations, or target weights.
    Only provided fields are updated - omitted fields remain unchanged.

    Use fetch_a_pie first to see the current configuration before making changes.
    The API requires providing a name even if you are not changing it.

    Args:
        pie_id: Numeric ID of the pie to modify (e.g., 6894572). Get this from fetch_pies.
        name: Updated name for the pie. Required by the API even if unchanged.
        instrument_shares: New ticker-to-weight mapping, must sum to 1.0.
            Example: {'AAPL_US_EQ': 0.5, 'MSFT_US_EQ': 0.5}
        dividend_cash_action: REINVEST or TO_ACCOUNT_CASH
        end_date: Revised end date in ISO 8601 (e.g., '2029-12-31T23:59:59Z')
        goal: Revised target value in account currency (e.g., 25000.0)
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


@mcp.tool("duplicate_pie", annotations=_WRITE)
def duplicate_pie(
    pie_id: int, name: Optional[str] = None, icon: Optional[str] = None
) -> PieDetails:
    """
    Clone an existing pie into a new one with identical instrument allocations
    and settings. The new pie starts with zero invested value.

    Use this to create a variation of an existing pie without rebuilding it
    from scratch. See also: create_pie for building a pie from scratch.

    Args:
        pie_id: ID of the source pie to copy (e.g., 6894572). Get this from fetch_pies.
        name: Optional custom name for the clone. Defaults to the original name with a suffix.
        icon: Optional icon for the clone.

    Returns:
        PieDetails: Full details of the newly cloned pie
    """
    req = DuplicatePieRequest(name=name, icon=icon)
    return client.duplicate_pie(pie_id, req)


@mcp.tool("delete_pie", annotations=_DESTRUCTIVE)
def delete_pie(pie_id: int):
    """
    Permanently delete a pie. This is irreversible. Instruments inside the pie
    become standalone positions in your portfolio - they are not sold.

    Use fetch_a_pie first to review the pie contents before deleting. Consider
    whether you want to sell the positions separately after deletion.

    Args:
        pie_id: Numeric ID of the pie to delete (e.g., 6894572). Get this from fetch_pies.
    """
    return client.delete_pie(pie_id)
