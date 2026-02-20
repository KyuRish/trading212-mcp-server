import httpx
import os
import base64
from typing import Optional, List, Any

from models import *


class Trading212Client:
    def __init__(self, api_key: str = None, api_secret: str = None,
                 environment: str = None, version: str = "v0"):
        api_key = api_key or os.getenv("TRADING212_API_KEY")
        api_secret = api_secret or os.getenv("TRADING212_API_SECRET")
        environment = environment or os.getenv("ENVIRONMENT") or Environment.DEMO.value
        base_url = f"https://{environment}.trading212.com/api/{version}"

        if api_secret:
            credentials = f"{api_key}:{api_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()
            auth_header = f"Basic {encoded}"
        else:
            auth_header = api_key

        headers = {"Authorization": auth_header, "Content-Type": "application/json"}
        self.client = httpx.Client(base_url=base_url, headers=headers, timeout=30)

    def _request(self, method: str, url: str, **kwargs) -> Any:
        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Trading 212 API error {e.response.status_code}: {e.response.text}")

    def get_account_info(self) -> Account:
        data = self._request("GET", "/equity/account/info")
        return Account.model_validate(data)

    def get_account_cash(self) -> Cash:
        data = self._request("GET", "/equity/account/cash")
        return Cash.model_validate(data)

    def get_account_positions(self) -> List[Position]:
        data = self._request("GET", "/equity/portfolio")
        return [Position.model_validate(pos) for pos in data]

    def search_position_by_ticker(self, ticker: str) -> Position:
        data = self._request("POST", "/equity/portfolio/ticker",
                             json={"ticker": ticker})
        return Position.model_validate(data)

    def get_dividends(self, cursor: Optional[int] = None,
                      ticker: Optional[str] = None,
                      limit: int = 20) -> PaginatedResponseHistoryDividendItem:
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if ticker is not None:
            params["ticker"] = ticker
        if limit is not None:
            params["limit"] = min(50, max(1, limit))
        data = self._request("GET", "/history/dividends", params=params)
        return PaginatedResponseHistoryDividendItem.model_validate(data)

    def get_orders(self) -> List[Order]:
        data = self._request("GET", "/equity/orders")
        return [Order.model_validate(order) for order in data]

    def get_order_by_id(self, order_id: int) -> Order:
        data = self._request("GET", f"/equity/orders/{order_id}")
        return Order.model_validate(data)

    def get_pies(self) -> List[AccountBucketResultResponse]:
        data = self._request("GET", "/equity/pies")
        return [AccountBucketResultResponse.model_validate(pie) for pie in data]

    def get_pie_by_id(self, pie_id: int) -> AccountBucketInstrumentsDetailedResponse:
        data = self._request("GET", f"/equity/pies/{pie_id}")
        return AccountBucketInstrumentsDetailedResponse.model_validate(data)

    def create_pie(self, pie_data: PieRequest) -> AccountBucketInstrumentsDetailedResponse:
        data = self._request("POST", "/equity/pies",
                             json=pie_data.model_dump(mode="json"))
        return AccountBucketInstrumentsDetailedResponse.model_validate(data)

    def update_pie(self, pie_id: int, pie_data: PieRequest) -> AccountBucketInstrumentsDetailedResponse:
        payload = {k: v for k, v in pie_data.model_dump(mode="json").items() if v is not None}
        data = self._request("POST", f"/equity/pies/{pie_id}", json=payload)
        return AccountBucketInstrumentsDetailedResponse.model_validate(data)

    def duplicate_pie(self, pie_id: int,
                      req: DuplicateBucketRequest) -> AccountBucketInstrumentsDetailedResponse:
        data = self._request("POST", f"/equity/pies/{pie_id}/duplicate",
                             json=req.model_dump(mode="json"))
        return AccountBucketInstrumentsDetailedResponse.model_validate(data)

    def delete_pie(self, pie_id: int):
        return self._request("DELETE", f"/equity/pies/{pie_id}")

    def get_historical_order_data(self, cursor: Optional[int] = None,
                                  ticker: Optional[str] = None,
                                  limit: int = 20) -> List[HistoricalOrder]:
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if ticker is not None:
            params["ticker"] = ticker
        data = self._request("GET", "/equity/history/orders", params=params)
        return [HistoricalOrder.model_validate(order) for order in data["items"]]

    def get_history_transactions(self, cursor: Optional[str] = None,
                                 time: Optional[str] = None,
                                 limit: int = 20) -> PaginatedResponseHistoryTransactionItem:
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if time is not None:
            params["time"] = time
        data = self._request("GET", "/equity/history/transactions", params=params)
        return PaginatedResponseHistoryTransactionItem.model_validate(data)

    def get_instruments(self) -> List[TradeableInstrument]:
        data = self._request("GET", "/equity/metadata/instruments")
        return [TradeableInstrument.model_validate(inst) for inst in data]

    def get_exchanges(self) -> List[Exchange]:
        data = self._request("GET", "/equity/metadata/exchanges")
        return [Exchange.model_validate(exch) for exch in data]

    def place_market_order(self, order_data: MarketRequest) -> Order:
        data = self._request("POST", "/equity/orders/market",
                             json=order_data.model_dump(mode="json"))
        return Order.model_validate(data)

    def place_limit_order(self, order_data: LimitRequest) -> Order:
        data = self._request("POST", "/equity/orders/limit",
                             json=order_data.model_dump(mode="json"))
        return Order.model_validate(data)

    def place_stop_order(self, order_data: StopRequest) -> Order:
        data = self._request("POST", "/equity/orders/stop",
                             json=order_data.model_dump(mode="json"))
        return Order.model_validate(data)

    def place_stop_limit_order(self, order_data: StopLimitRequest) -> Order:
        data = self._request("POST", "/equity/orders/stop_limit",
                             json=order_data.model_dump(mode="json"))
        return Order.model_validate(data)

    def cancel_order(self, order_id: int) -> None:
        self._request("DELETE", f"/equity/orders/{order_id}")

    def get_reports(self) -> list[ReportResponse]:
        data = self._request("GET", "/history/exports")
        return [ReportResponse.model_validate(report) for report in data]

    def request_export(self, data_included: ReportDataIncluded = None,
                       time_from: str = None,
                       time_to: str = None) -> EnqueuedReportResponse:
        payload = {}
        data_included = data_included or ReportDataIncluded()
        payload["dataIncluded"] = data_included.model_dump(mode="json")
        if time_from:
            payload["timeFrom"] = time_from
        if time_to:
            payload["timeTo"] = time_to
        data = self._request("POST", "/history/exports", json=payload)
        return EnqueuedReportResponse.model_validate(data)
