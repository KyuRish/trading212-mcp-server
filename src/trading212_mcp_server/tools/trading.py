from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import (
    Order, LimitOrderRequest, MarketOrderRequest, StopOrderRequest,
    StopLimitOrderRequest, TimeValidity,
)


@mcp.tool("fetch_all_orders")
def fetch_orders() -> list[Order]:
    """List all active equity orders (limit, stop, stop-limit) that are waiting to be filled."""
    return client.fetch_orders()


@mcp.tool("fetch_order")
def fetch_order_by_id(order_id: int) -> Order:
    """Retrieve a single pending order by ID, showing its current status, fill progress, and price parameters."""
    return client.fetch_order(order_id)


@mcp.tool("place_market_order")
def place_market_order(ticker: str, quantity: float) -> Order:
    """
    Execute a market order at the current price for the given instrument.

    Args:
        ticker: Instrument ticker to trade (e.g., 'AAPL_US_EQ')
        quantity: Number of shares to trade. Use a positive value to buy, negative to sell.

    Returns:
        Order: The newly created order with its initial status
    """
    req = MarketOrderRequest(ticker=ticker, quantity=quantity)
    return client.place_market_order(req)


@mcp.tool("place_limit_order")
def place_limit_order(
    ticker: str,
    quantity: float,
    limit_price: float,
    time_validity: TimeValidity = TimeValidity.DAY,
) -> Order:
    """
    Submit a limit order that executes only when the instrument reaches your target price.

    Args:
        ticker: Instrument ticker to trade (e.g., 'AAPL_US_EQ')
        quantity: Number of shares to trade
        limit_price: Maximum price you are willing to pay (buy) or minimum to accept (sell)
        time_validity: How long the order stays active. Options: DAY, GOOD_TILL_CANCEL

    Returns:
        Order: The newly created limit order
    """
    req = LimitOrderRequest(
        ticker=ticker, quantity=quantity,
        limit_price=limit_price, time_validity=time_validity,
    )
    return client.place_limit_order(req)


@mcp.tool("place_stop_order")
def place_stop_order(
    ticker: str,
    quantity: float,
    stop_price: float,
    time_validity: TimeValidity = TimeValidity.DAY,
) -> Order:
    """
    Submit a stop order that triggers a market execution once the instrument hits the specified stop price.

    Args:
        ticker: Instrument ticker to trade (e.g., 'AAPL_US_EQ')
        quantity: Number of shares to trade
        stop_price: Trigger price that activates the order
        time_validity: How long the order stays active. Options: DAY, GOOD_TILL_CANCEL

    Returns:
        Order: The newly created stop order
    """
    req = StopOrderRequest(
        ticker=ticker, quantity=quantity,
        stop_price=stop_price, time_validity=time_validity,
    )
    return client.place_stop_order(req)


@mcp.tool("place_stop_limit_order")
def place_stop_limit_order(
    ticker: str,
    quantity: float,
    stop_price: float,
    limit_price: float,
    time_validity: TimeValidity = TimeValidity.DAY,
) -> Order:
    """
    Submit a combined stop-limit order: once the stop price is hit, a limit order
    is placed at your specified limit price instead of executing at market.

    Args:
        ticker: Instrument ticker to trade (e.g., 'AAPL_US_EQ')
        quantity: Number of shares to trade
        stop_price: Trigger price that activates the limit order
        limit_price: Price at which the resulting limit order will be placed
        time_validity: How long the order stays active. Options: DAY, GOOD_TILL_CANCEL

    Returns:
        Order: The newly created stop-limit order
    """
    req = StopLimitOrderRequest(
        ticker=ticker, quantity=quantity,
        stop_price=stop_price, limit_price=limit_price,
        time_validity=time_validity,
    )
    return client.place_stop_limit_order(req)


@mcp.tool("cancel_order")
def cancel_order_by_id(order_id: int) -> None:
    """Remove a pending order from the book. This cannot be undone once executed."""
    return client.cancel_order(order_id)
