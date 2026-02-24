from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import Instrument, Exchange


@mcp.tool("search_instrument")
def search_instrument(search_term: str = None) -> list[Instrument]:
    """
    Look up tradeable instruments, with optional filtering by ticker or name.

    Args:
        search_term: Case-insensitive text to match against ticker symbols
            and instrument names. Omit to return every available instrument.

    Returns:
        List of instruments matching the search, or the full catalogue if
        no search_term is given
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


@mcp.tool("search_exchange")
def search_exchange(search_term: str = None) -> list[Exchange]:
    """
    Look up exchanges, with optional filtering by name or numeric ID.

    Args:
        search_term: Case-insensitive text to match against exchange names,
            or an exact numeric exchange ID. Omit to return all exchanges.

    Returns:
        List of matching exchanges, or every exchange if no filter is applied
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
