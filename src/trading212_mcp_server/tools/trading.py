from mcp.types import ToolAnnotations
from trading212_mcp_server.app import mcp, client
from trading212_mcp_server.models import (
    Order, LimitOrderRequest, MarketOrderRequest, StopOrderRequest,
    StopLimitOrderRequest, TimeValidity,
)

_READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
_DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True)


@mcp.tool("fetch_all_orders", annotations=_READ)
def fetch_orders() -> list[Order]:
    """
    List all active pending orders (limit, stop, stop-limit) waiting to be filled.

    Use this to review open orders before placing new ones or to check if a
    previously placed order is still active. Does not include filled or
    cancelled orders - use fetch_historical_order_data for those.

    Returns:
        List of Order objects with id, ticker, type, status, quantity, limitPrice, stopPrice
    """
    return client.fetch_orders()


@mcp.tool("fetch_order", annotations=_READ)
def fetch_order_by_id(order_id: int) -> Order:
    """
    Retrieve a single pending order by its ID to check its current status,
    fill progress, and price parameters.

    Use this after placing an order to monitor its status, or before cancelling
    to confirm the order is still active. See also: fetch_all_orders to list
    all pending orders at once.

    Args:
        order_id: Numeric order ID returned when the order was placed (e.g., 12345678)

    Returns:
        Order with id, ticker, type, status, quantity, filledQuantity, limitPrice, stopPrice
    """
    return client.fetch_order(order_id)


@mcp.tool("place_market_order", annotations=_WRITE)
def place_market_order(ticker: str, quantity: float) -> Order:
    """
    Execute a market order at the current price. This creates a real trade that
    affects your portfolio immediately. The order fills at the best available
    market price.

    Use search_instrument first to find the correct ticker symbol. Check
    fetch_account_cash to verify sufficient buying power before placing.

    Args:
        ticker: Instrument ticker to trade (e.g., 'AAPL_US_EQ', 'MSFT_US_EQ').
            Use search_instrument to find valid tickers.
        quantity: Number of shares. Positive to buy, negative to sell.
            Fractional shares are supported (e.g., 0.5).

    Returns:
        Order: The newly created order with its initial status
    """
    req = MarketOrderRequest(ticker=ticker, quantity=quantity)
    return client.place_market_order(req)


@mcp.tool("place_limit_order", annotations=_WRITE)
def place_limit_order(
    ticker: str,
    quantity: float,
    limit_price: float,
    time_validity: TimeValidity = TimeValidity.DAY,
) -> Order:
    """
    Submit a limit order that executes only when the instrument reaches your
    target price. The order stays open until filled, cancelled, or expired.

    Use this instead of a market order when you want to control the execution
    price. Check fetch_all_orders afterward to monitor fill status.

    Args:
        ticker: Instrument ticker (e.g., 'AAPL_US_EQ'). Use search_instrument to find valid tickers.
        quantity: Number of shares. Positive to buy, negative to sell.
        limit_price: Maximum price to pay (buy) or minimum to accept (sell).
            For example, 150.00 means "buy at 150 or lower".
        time_validity: How long the order stays active. DAY (expires end of trading day)
            or GOOD_TILL_CANCEL (stays open until filled or manually cancelled). Defaults to DAY.

    Returns:
        Order: The newly created limit order with its pending status
    """
    req = LimitOrderRequest(
        ticker=ticker, quantity=quantity,
        limit_price=limit_price, time_validity=time_validity,
    )
    return client.place_limit_order(req)


@mcp.tool("place_stop_order", annotations=_WRITE)
def place_stop_order(
    ticker: str,
    quantity: float,
    stop_price: float,
    time_validity: TimeValidity = TimeValidity.DAY,
) -> Order:
    """
    Submit a stop order that triggers a market execution once the instrument
    reaches the specified stop price. Commonly used as a stop-loss to limit
    downside risk on an existing position.

    When the stop price is hit, the order becomes a market order and fills at
    the best available price (which may differ from the stop price in fast markets).
    For more control over the fill price, use place_stop_limit_order instead.

    Args:
        ticker: Instrument ticker (e.g., 'AAPL_US_EQ'). Use search_instrument to find valid tickers.
        quantity: Number of shares. Positive to buy, negative to sell.
        stop_price: Trigger price that activates the order (e.g., 140.00).
        time_validity: DAY or GOOD_TILL_CANCEL. Defaults to DAY.

    Returns:
        Order: The newly created stop order
    """
    req = StopOrderRequest(
        ticker=ticker, quantity=quantity,
        stop_price=stop_price, time_validity=time_validity,
    )
    return client.place_stop_order(req)


@mcp.tool("place_stop_limit_order", annotations=_WRITE)
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

    This gives more control than a plain stop order by preventing execution at
    an unfavourable price during fast market moves, but the order may not fill
    if the price moves through the limit. See also: place_stop_order for a
    simpler stop that guarantees execution.

    Args:
        ticker: Instrument ticker (e.g., 'AAPL_US_EQ'). Use search_instrument to find valid tickers.
        quantity: Number of shares. Positive to buy, negative to sell.
        stop_price: Trigger price that activates the limit order (e.g., 140.00).
        limit_price: Price at which the resulting limit order is placed (e.g., 139.50).
            Typically set slightly below the stop price for sells.
        time_validity: DAY or GOOD_TILL_CANCEL. Defaults to DAY.

    Returns:
        Order: The newly created stop-limit order
    """
    req = StopLimitOrderRequest(
        ticker=ticker, quantity=quantity,
        stop_price=stop_price, limit_price=limit_price,
        time_validity=time_validity,
    )
    return client.place_stop_limit_order(req)


@mcp.tool("cancel_order", annotations=_DESTRUCTIVE)
def cancel_order_by_id(order_id: int) -> None:
    """
    Cancel a pending order and remove it from the order book. This is irreversible -
    once cancelled, the order cannot be reinstated and must be placed again.

    Use fetch_all_orders or fetch_order first to confirm the order is still
    active before attempting to cancel.

    Args:
        order_id: Numeric ID of the pending order to cancel (e.g., 12345678).
            Get this from fetch_all_orders or from the response when the order was placed.
    """
    return client.cancel_order(order_id)
