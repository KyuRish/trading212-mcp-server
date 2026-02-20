from app import mcp, client
from models import (
    Order, LimitRequest, MarketRequest, StopRequest, StopLimitRequest,
    LimitRequestTimeValidityEnum, StopRequestTimeValidityEnum,
    StopLimitRequestTimeValidityEnum,
)


@mcp.tool("fetch_all_orders")
def fetch_orders() -> list[Order]:
    """Fetch all equity orders."""
    return client.get_orders()


@mcp.tool("fetch_order")
def fetch_order_by_id(order_id: int) -> Order:
    """Fetch a specific order by ID."""
    return client.get_order_by_id(order_id)


@mcp.tool("place_market_order")
def place_market_order(ticker: str, quantity: float) -> Order:
    """
    Place a market order to buy or sell an instrument at the current market price.

    Args:
        ticker: Ticker symbol of the instrument to trade (e.g., 'AAPL_US_EQ')
        quantity: Number of shares/units to trade

    Returns:
        Order: Details of the placed order
    """
    market_request = MarketRequest(ticker=ticker, quantity=quantity)
    return client.place_market_order(market_request)


@mcp.tool("place_limit_order")
def place_limit_order(
    ticker: str,
    quantity: float,
    limit_price: float,
    time_validity: LimitRequestTimeValidityEnum = LimitRequestTimeValidityEnum.DAY,
) -> Order:
    """
    Place a limit order to buy or sell an instrument at a specified price or better.

    Args:
        ticker: Ticker symbol of the instrument to trade (e.g., 'AAPL_US_EQ')
        quantity: Number of shares/units to trade
        limit_price: Limit price for the order
        time_validity: Time validity of the order. Defaults to DAY.
            Possible values: DAY, GOOD_TILL_CANCEL

    Returns:
        Order: Details of the placed order
    """
    limit_request = LimitRequest(
        ticker=ticker, quantity=quantity,
        limitPrice=limit_price, timeValidity=time_validity,
    )
    return client.place_limit_order(limit_request)


@mcp.tool("place_stop_order")
def place_stop_order(
    ticker: str,
    quantity: float,
    stop_price: float,
    time_validity: StopRequestTimeValidityEnum = StopRequestTimeValidityEnum.DAY,
) -> Order:
    """
    Place a stop order to buy or sell an instrument when the market price
    reaches a specified stop price.

    Args:
        ticker: Ticker symbol of the instrument to trade (e.g., 'AAPL_US_EQ')
        quantity: Number of shares/units to trade
        stop_price: Stop price that triggers the order
        time_validity: Time validity of the order. Defaults to DAY.
            Possible values: DAY, GOOD_TILL_CANCEL

    Returns:
        Order: Details of the placed order
    """
    stop_request = StopRequest(
        ticker=ticker, quantity=quantity,
        stopPrice=stop_price, timeValidity=time_validity,
    )
    return client.place_stop_order(stop_request)


@mcp.tool("place_stop_limit_order")
def place_stop_limit_order(
    ticker: str,
    quantity: float,
    stop_price: float,
    limit_price: float,
    time_validity: StopLimitRequestTimeValidityEnum = StopLimitRequestTimeValidityEnum.DAY,
) -> Order:
    """
    Place a stop-limit order to buy or sell an instrument when the market
    price reaches a specified stop price, then execute at a specified limit
    price or better.

    Args:
        ticker: Ticker symbol of the instrument to trade (e.g., 'AAPL_US_EQ')
        quantity: Number of shares/units to trade
        stop_price: Stop price that triggers the limit order
        limit_price: Limit price for the order
        time_validity: Time validity of the order. Defaults to DAY.
            Possible values: DAY, GOOD_TILL_CANCEL

    Returns:
        Order: Details of the placed order
    """
    stop_limit_request = StopLimitRequest(
        ticker=ticker, quantity=quantity,
        stopPrice=stop_price, limitPrice=limit_price,
        timeValidity=time_validity,
    )
    return client.place_stop_limit_order(stop_limit_request)


@mcp.tool("cancel_order")
def cancel_order_by_id(order_id: int) -> None:
    """Cancel an existing order."""
    return client.cancel_order(order_id)
