import httpx
import os
import base64
from enum import Enum
from typing import Optional, Any

from trading212_mcp_server.models import (
    Account, Cash, Position, Order, Exchange, Instrument,
    PieSummary, PieDetails, PaginatedDividends, PaginatedTransactions,
    HistoricalOrder, Report, EnqueuedReport,
    PieRequest, DuplicatePieRequest, ReportDataIncluded,
    MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest,
)


class _Environment(str, Enum):
    DEMO = "demo"
    LIVE = "live"


class T212Client:
    def __init__(self, api_key: str = None, api_secret: str = None,
                 environment: str = None, version: str = "v0"):
        api_key = api_key or os.getenv("TRADING212_API_KEY")
        api_secret = api_secret or os.getenv("TRADING212_API_SECRET")
        environment = environment or os.getenv("ENVIRONMENT", "demo")
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
            status = e.response.status_code
            if status == 401:
                raise Exception(
                    "Authentication failed. Check TRADING212_API_KEY and "
                    "TRADING212_API_SECRET in your environment."
                )
            if status == 429:
                raise Exception(
                    "Rate limited by Trading 212. Wait a few seconds before retrying."
                )
            raise Exception(f"Trading 212 API error {status}: {e.response.text}")
        except httpx.ConnectError:
            raise Exception(
                "Cannot connect to Trading 212. Check your internet connection."
            )
        except httpx.TimeoutException:
            raise Exception(
                "Trading 212 API request timed out. Try again."
            )

    def _paginate(self, url: str, params: dict = None) -> list[dict]:
        """Follow nextPagePath cursors to collect all pages of results."""
        params = params or {}
        all_items = []
        while True:
            data = self._request("GET", url, params=params)
            all_items.extend(data.get("items", []))
            next_path = data.get("nextPagePath")
            if not next_path:
                break
            url = next_path
            params = {}
        return all_items

    # --- Account ---

    def fetch_account(self) -> Account:
        data = self._request("GET", "/equity/account/info")
        return Account.model_validate(data)

    def fetch_cash(self) -> Cash:
        data = self._request("GET", "/equity/account/cash")
        return Cash.model_validate(data)

    # --- Positions ---

    def fetch_positions(self) -> list[Position]:
        data = self._request("GET", "/equity/portfolio")
        return [Position.model_validate(pos) for pos in data]

    def search_position_by_ticker(self, ticker: str) -> Position:
        data = self._request("POST", "/equity/portfolio/ticker",
                             json={"ticker": ticker})
        return Position.model_validate(data)

    # --- Dividends ---

    def fetch_dividends(self, cursor: Optional[int] = None,
                        ticker: Optional[str] = None,
                        limit: int = 20) -> PaginatedDividends:
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if ticker is not None:
            params["ticker"] = ticker
        if limit is not None:
            params["limit"] = min(50, max(1, limit))
        data = self._request("GET", "/history/dividends", params=params)
        return PaginatedDividends.model_validate(data)

    # --- Orders ---

    def fetch_orders(self) -> list[Order]:
        data = self._request("GET", "/equity/orders")
        return [Order.model_validate(order) for order in data]

    def fetch_order(self, order_id: int) -> Order:
        data = self._request("GET", f"/equity/orders/{order_id}")
        return Order.model_validate(data)

    def place_market_order(self, order_data: MarketOrderRequest) -> Order:
        data = self._request("POST", "/equity/orders/market",
                             json=order_data.model_dump(mode="json", by_alias=True))
        return Order.model_validate(data)

    def place_limit_order(self, order_data: LimitOrderRequest) -> Order:
        data = self._request("POST", "/equity/orders/limit",
                             json=order_data.model_dump(mode="json", by_alias=True))
        return Order.model_validate(data)

    def place_stop_order(self, order_data: StopOrderRequest) -> Order:
        data = self._request("POST", "/equity/orders/stop",
                             json=order_data.model_dump(mode="json", by_alias=True))
        return Order.model_validate(data)

    def place_stop_limit_order(self, order_data: StopLimitOrderRequest) -> Order:
        data = self._request("POST", "/equity/orders/stop_limit",
                             json=order_data.model_dump(mode="json", by_alias=True))
        return Order.model_validate(data)

    def cancel_order(self, order_id: int) -> None:
        self._request("DELETE", f"/equity/orders/{order_id}")

    # --- Pies ---

    def fetch_pies(self) -> list[PieSummary]:
        data = self._request("GET", "/equity/pies")
        return [PieSummary.model_validate(pie) for pie in data]

    def fetch_pie(self, pie_id: int) -> PieDetails:
        data = self._request("GET", f"/equity/pies/{pie_id}")
        return PieDetails.model_validate(data)

    def create_pie(self, pie_data: PieRequest) -> PieDetails:
        data = self._request("POST", "/equity/pies",
                             json=pie_data.model_dump(mode="json", by_alias=True))
        return PieDetails.model_validate(data)

    def update_pie(self, pie_id: int, pie_data: PieRequest) -> PieDetails:
        payload = {k: v for k, v in pie_data.model_dump(mode="json", by_alias=True).items()
                   if v is not None}
        data = self._request("POST", f"/equity/pies/{pie_id}", json=payload)
        return PieDetails.model_validate(data)

    def duplicate_pie(self, pie_id: int, req: DuplicatePieRequest) -> PieDetails:
        data = self._request("POST", f"/equity/pies/{pie_id}/duplicate",
                             json=req.model_dump(mode="json", by_alias=True))
        return PieDetails.model_validate(data)

    def delete_pie(self, pie_id: int):
        return self._request("DELETE", f"/equity/pies/{pie_id}")

    # --- History ---

    def fetch_order_history(self, cursor: Optional[int] = None,
                            ticker: Optional[str] = None,
                            limit: int = 20) -> list[HistoricalOrder]:
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if ticker is not None:
            params["ticker"] = ticker
        data = self._request("GET", "/equity/history/orders", params=params)
        return [HistoricalOrder.model_validate(order) for order in data["items"]]

    def fetch_transactions(self, cursor: Optional[str] = None,
                           time: Optional[str] = None,
                           limit: int = 20) -> PaginatedTransactions:
        params = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if time is not None:
            params["time"] = time
        data = self._request("GET", "/equity/history/transactions", params=params)
        return PaginatedTransactions.model_validate(data)

    # --- Market Data ---

    def fetch_instruments(self) -> list[Instrument]:
        data = self._request("GET", "/equity/metadata/instruments")
        return [Instrument.model_validate(inst) for inst in data]

    def fetch_exchanges(self) -> list[Exchange]:
        data = self._request("GET", "/equity/metadata/exchanges")
        return [Exchange.model_validate(exch) for exch in data]

    # --- Reports ---

    def fetch_reports(self) -> list[Report]:
        data = self._request("GET", "/history/exports")
        return [Report.model_validate(report) for report in data]

    def request_export(self, data_included: ReportDataIncluded = None,
                       time_from: str = None,
                       time_to: str = None) -> EnqueuedReport:
        payload = {}
        data_included = data_included or ReportDataIncluded()
        payload["dataIncluded"] = data_included.model_dump(mode="json", by_alias=True)
        if time_from:
            payload["timeFrom"] = time_from
        if time_to:
            payload["timeTo"] = time_to
        data = self._request("POST", "/history/exports", json=payload)
        return EnqueuedReport.model_validate(data)
