from mcp.types import ToolAnnotations
from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import Instrument, Exchange

_READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)


@mcp.tool("search_instrument", annotations=_READ)
def search_instrument(search_term: str = None) -> list[Instrument]:
    """
    Search for tradeable instruments by ticker symbol or company name.
    Returns matching instruments with their ticker, ISIN, currency, and type.

    Use this before placing orders or creating pies to find the correct Trading 212
    ticker format (e.g., 'AAPL_US_EQ' for Apple). Omit the search term to retrieve
    the full instrument catalogue.

    The search is case-insensitive and matches partial strings against both
    ticker symbols and instrument names.

    Args:
        search_term: Text to match against tickers and names (e.g., 'Apple', 'AAPL',
            'silver ETC'). Omit to return every available instrument.

    Returns:
        List of Instrument objects with ticker, name, type (STOCK/ETF), currencyCode,
        isin, shortName, and maxOpenQuantity
    """
    instruments = client.fetch_instruments()

    if not search_term:
        return instruments

    search_lower = search_term.lower()
    return [
        inst for inst in instruments
        if search_lower in inst.ticker.lower()
        or search_lower in inst.name.lower()
    ]


@mcp.tool("search_exchange", annotations=_READ)
def search_exchange(search_term: str = None) -> list[Exchange]:
    """
    Search for stock exchanges by name or numeric ID. Returns exchange details
    including trading hours and working schedules.

    Use this to check when a specific exchange is open for trading, or to
    look up exchange information by its numeric ID from an instrument's
    workingScheduleId field.

    Args:
        search_term: Case-insensitive text to match against exchange names
            (e.g., 'NASDAQ', 'London'), or an exact numeric exchange ID
            (e.g., '71'). Omit to return all exchanges.

    Returns:
        List of Exchange objects with id, name, and workingSchedules
    """
    exchanges = client.fetch_exchanges()

    if not search_term:
        return exchanges

    search_lower = search_term.lower()
    return [
        exch for exch in exchanges
        if search_lower in exch.name.lower()
        or str(exch.id) == search_term
    ]
