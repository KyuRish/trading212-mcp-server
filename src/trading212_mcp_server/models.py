from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from enum import Enum
from datetime import datetime


class T212BaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


# Enums - consolidated where the API reuses the same value set

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    NEW = "NEW"
    CONFIRMED = "CONFIRMED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    CANCELLING = "CANCELLING"
    REJECTED = "REJECTED"
    REPLACED = "REPLACED"
    REPLACING = "REPLACING"
    LOCAL = "LOCAL"
    UNCONFIRMED = "UNCONFIRMED"


class OrderStrategy(str, Enum):
    QUANTITY = "QUANTITY"
    VALUE = "VALUE"


class TimeValidity(str, Enum):
    DAY = "DAY"
    GOOD_TILL_CANCEL = "GOOD_TILL_CANCEL"


class Executor(str, Enum):
    API = "API"
    WEB = "WEB"
    IOS = "IOS"
    ANDROID = "ANDROID"
    SYSTEM = "SYSTEM"
    AUTOINVEST = "AUTOINVEST"


class FillType(str, Enum):
    TOTV = "TOTV"
    OTC = "OTC"


class InstrumentType(str, Enum):
    STOCK = "STOCK"
    ETF = "ETF"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    CRYPTOCURRENCY = "CRYPTOCURRENCY"
    INDEX = "INDEX"
    FUTURES = "FUTURES"
    WARRANT = "WARRANT"
    CVR = "CVR"
    CORPACT = "CORPACT"


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    TRANSFER = "TRANSFER"
    FEE = "FEE"


class DividendCashAction(str, Enum):
    REINVEST = "REINVEST"
    TO_ACCOUNT_CASH = "TO_ACCOUNT_CASH"


class PieStatus(str, Enum):
    AHEAD = "AHEAD"
    ON_TRACK = "ON_TRACK"
    BEHIND = "BEHIND"


class IssueType(str, Enum):
    DELISTED = "DELISTED"
    SUSPENDED = "SUSPENDED"
    NO_LONGER_TRADABLE = "NO_LONGER_TRADABLE"
    MAX_POSITION_SIZE_REACHED = "MAX_POSITION_SIZE_REACHED"
    APPROACHING_MAX_POSITION_SIZE = "APPROACHING_MAX_POSITION_SIZE"
    COMPLEX_INSTRUMENT_APP_TEST_REQUIRED = "COMPLEX_INSTRUMENT_APP_TEST_REQUIRED"


class IssueSeverity(str, Enum):
    IRREVERSIBLE = "IRREVERSIBLE"
    REVERSIBLE = "REVERSIBLE"
    INFORMATIVE = "INFORMATIVE"


class TaxName(str, Enum):
    STAMP_DUTY = "STAMP_DUTY"
    STAMP_DUTY_RESERVE_TAX = "STAMP_DUTY_RESERVE_TAX"
    FINRA_FEE = "FINRA_FEE"
    COMMISSION_TURNOVER = "COMMISSION_TURNOVER"
    FRENCH_TRANSACTION_TAX = "FRENCH_TRANSACTION_TAX"
    PTM_LEVY = "PTM_LEVY"
    TRANSACTION_FEE = "TRANSACTION_FEE"
    CURRENCY_CONVERSION_FEE = "CURRENCY_CONVERSION_FEE"


class ScheduleEventType(str, Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    PRE_MARKET_OPEN = "PRE_MARKET_OPEN"
    AFTER_HOURS_OPEN = "AFTER_HOURS_OPEN"
    AFTER_HOURS_CLOSE = "AFTER_HOURS_CLOSE"
    OVERNIGHT_OPEN = "OVERNIGHT_OPEN"
    BREAK_START = "BREAK_START"
    BREAK_END = "BREAK_END"


class ReportStatus(str, Enum):
    QUEUED = "Queued"
    PROCESSING = "Processing"
    RUNNING = "Running"
    FINISHED = "Finished"
    FAILED = "Failed"
    CANCELED = "Canceled"


# Account

class Account(T212BaseModel):
    id: int
    currency_code: str


class Cash(T212BaseModel):
    free: Optional[float] = None
    invested: Optional[float] = None
    total: Optional[float] = None
    ppl: Optional[float] = None
    result: Optional[float] = None
    blocked: Optional[float] = None
    pie_cash: Optional[float] = None


# Positions

class Position(T212BaseModel):
    ticker: str
    quantity: float
    average_price: float
    current_price: float
    ppl: Optional[float] = None
    fx_ppl: Optional[float] = None
    initial_fill_date: Optional[datetime] = None
    pie_quantity: Optional[float] = None
    max_buy: Optional[float] = None
    max_sell: Optional[float] = None
    frontend: Optional[Executor] = None


# Orders

class Order(T212BaseModel):
    id: int
    ticker: str
    type: Optional[OrderType] = None
    status: Optional[OrderStatus] = None
    quantity: Optional[float] = None
    filled_quantity: Optional[float] = None
    filled_value: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    strategy: Optional[OrderStrategy] = None
    value: Optional[float] = None
    creation_time: Optional[datetime] = None


class Tax(T212BaseModel):
    name: Optional[TaxName] = None
    quantity: Optional[float] = None
    fill_id: Optional[str] = None
    time_charged: Optional[datetime] = None


class HistoricalOrder(T212BaseModel):
    id: int
    ticker: str
    type: Optional[OrderType] = None
    status: Optional[OrderStatus] = None
    executor: Optional[Executor] = None
    filled_quantity: Optional[float] = None
    filled_value: Optional[float] = None
    fill_price: Optional[float] = None
    fill_cost: Optional[float] = None
    fill_result: Optional[float] = None
    fill_type: Optional[FillType] = None
    fill_id: Optional[int] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    ordered_quantity: Optional[float] = None
    ordered_value: Optional[float] = None
    parent_order: Optional[int] = None
    time_validity: Optional[TimeValidity] = None
    taxes: Optional[list[Tax]] = None
    date_created: Optional[datetime] = None
    date_executed: Optional[datetime] = None
    date_modified: Optional[datetime] = None


# Dividends and Transactions

class DividendItem(T212BaseModel):
    ticker: str
    amount: float
    paid_on: Optional[datetime] = None
    quantity: Optional[float] = None
    gross_amount_per_share: Optional[float] = None
    amount_in_euro: Optional[float] = None
    reference: Optional[str] = None
    type: Optional[str] = None


class TransactionItem(T212BaseModel):
    amount: float
    type: TransactionType
    date_time: Optional[datetime] = None
    reference: Optional[str] = None


class PaginatedDividends(T212BaseModel):
    items: list[DividendItem]
    next_page_path: Optional[str] = None


class PaginatedTransactions(T212BaseModel):
    items: list[TransactionItem]
    next_page_path: Optional[str] = None


# Pies

class InvestmentResult(T212BaseModel):
    price_avg_value: Optional[float] = None
    price_avg_invested_value: Optional[float] = None
    price_avg_result: Optional[float] = None
    price_avg_result_coef: Optional[float] = None


class InstrumentIssue(T212BaseModel):
    name: IssueType
    severity: IssueSeverity


class PieInstrument(T212BaseModel):
    ticker: str
    expected_share: Optional[float] = None
    current_share: Optional[float] = None
    owned_quantity: Optional[float] = None
    result: Optional[InvestmentResult] = None
    issues: Optional[list[InstrumentIssue]] = None


class DividendDetails(T212BaseModel):
    gained: Optional[float] = None
    reinvested: Optional[float] = None
    in_cash: Optional[float] = None


class PieSettings(T212BaseModel):
    id: int
    name: Optional[str] = None
    icon: Optional[str] = None
    goal: Optional[float] = None
    dividend_cash_action: Optional[DividendCashAction] = None
    instrument_shares: Optional[dict[str, float]] = None
    creation_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_investment: Optional[float] = None
    public_url: Optional[str] = None


class PieDetails(T212BaseModel):
    settings: Optional[PieSettings] = None
    instruments: Optional[list[PieInstrument]] = None


class PieSummary(T212BaseModel):
    id: int
    status: Optional[PieStatus] = None
    cash: Optional[float] = None
    progress: Optional[float] = None
    result: Optional[InvestmentResult] = None
    dividend_details: Optional[DividendDetails] = None


# Market Data

class ScheduleEvent(T212BaseModel):
    date: datetime
    type: ScheduleEventType


class WorkingSchedule(T212BaseModel):
    id: int
    time_events: list[ScheduleEvent]


class Exchange(T212BaseModel):
    id: int
    name: str
    working_schedules: list[WorkingSchedule]


class Instrument(T212BaseModel):
    ticker: str
    name: str
    type: Optional[InstrumentType] = None
    currency_code: Optional[str] = None
    isin: Optional[str] = None
    short_name: Optional[str] = None
    min_trade_quantity: Optional[float] = None
    max_open_quantity: Optional[float] = None
    added_on: Optional[datetime] = None
    working_schedule_id: Optional[int] = None


# Requests

class MarketOrderRequest(T212BaseModel):
    ticker: str
    quantity: float


class LimitOrderRequest(T212BaseModel):
    ticker: str
    quantity: float
    limit_price: float
    time_validity: TimeValidity


class StopOrderRequest(T212BaseModel):
    ticker: str
    quantity: float
    stop_price: float
    time_validity: TimeValidity


class StopLimitOrderRequest(T212BaseModel):
    ticker: str
    quantity: float
    limit_price: float
    stop_price: float
    time_validity: TimeValidity


class PieRequest(T212BaseModel):
    name: Optional[str] = None
    instrument_shares: Optional[dict[str, float]] = None
    dividend_cash_action: Optional[DividendCashAction] = None
    goal: Optional[float] = None
    icon: Optional[str] = None
    end_date: Optional[datetime] = None


class DuplicatePieRequest(T212BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None


class ReportDataIncluded(T212BaseModel):
    include_orders: bool = True
    include_dividends: bool = True
    include_transactions: bool = True
    include_interest: bool = True


# Reports

class EnqueuedReport(T212BaseModel):
    report_id: int


class Report(T212BaseModel):
    report_id: Optional[int] = None
    status: Optional[ReportStatus] = None
    download_link: Optional[str] = None
    data_included: Optional[ReportDataIncluded] = None
    time_from: Optional[datetime] = None
    time_to: Optional[datetime] = None


WorkingSchedule.model_rebuild()
