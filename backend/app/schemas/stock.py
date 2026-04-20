"""Pydantic schemas for stock data endpoints."""

from pydantic import BaseModel

from app.schemas.common import MetaResponse


class StockResponse(BaseModel):
    """Flat representation of a Stock record."""

    symbol: str
    name: str
    market: str
    industry: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class PricePointResponse(BaseModel):
    """Single OHLCV bar."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float | None = None


class IndicatorPointResponse(BaseModel):
    """Single date/value pair for a technical indicator series."""

    date: str
    value: float


class ValuationResponse(BaseModel):
    """Fundamental valuation metrics for a stock.

    All fields default to ``None`` when the data source does not provide them
    (e.g. Taiwan stocks for US-only fields).
    """

    # Core valuation
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    ps_ratio: float | None = None
    dividend_yield: float | None = None
    market_cap: float | None = None
    eps: float | None = None
    revenue: float | None = None
    profit_margin: float | None = None

    # 風險指標
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None

    # 財務健康
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None

    # 獲利能力
    roe: float | None = None
    roa: float | None = None
    operating_margin: float | None = None
    gross_margin: float | None = None
    free_cash_flow: float | None = None

    # 成長指標
    revenue_growth: float | None = None
    earnings_growth: float | None = None

    # 進階估值
    peg_ratio: float | None = None
    ev_to_ebitda: float | None = None
    forward_pe: float | None = None

    # 分析師
    target_mean_price: float | None = None
    recommendation_key: str | None = None
    number_of_analysts: float | None = None

    # 持股結構
    insider_holding: float | None = None
    institutional_holding: float | None = None

    # 做空資料
    short_ratio: float | None = None
    short_percent_of_float: float | None = None

    # 股息詳情
    payout_ratio: float | None = None
    dividend_rate: float | None = None
    five_year_avg_dividend_yield: float | None = None


class StockListResponse(BaseModel):
    """Paginated list of stocks."""

    data: list[StockResponse]
    meta: MetaResponse


class StockDetailResponse(BaseModel):
    """Single stock detail envelope."""

    data: StockResponse | None


class StockHistoryResponse(BaseModel):
    """Historical OHLCV data envelope."""

    data: list[PricePointResponse]


class StockIndicatorsResponse(BaseModel):
    """Technical indicators envelope.

    ``data`` is a dict keyed by indicator name.  Simple single-series
    indicators (sma, ema, rsi) map to ``list[IndicatorPointResponse]``.
    Multi-series indicators (macd, bollinger_bands, kd) map to a nested
    dict where each sub-key is also a ``list[IndicatorPointResponse]``.
    """

    data: dict[str, list[IndicatorPointResponse] | dict[str, list[IndicatorPointResponse]]]


class StockValuationResponse(BaseModel):
    """Valuation metrics envelope."""

    data: ValuationResponse


class StockSignal(BaseModel):
    """A single qualitative signal from the scoring engine."""

    type: str  # "positive" | "negative" | "neutral"
    message: str


class StockScoreResponse(BaseModel):
    """Composite quality score for a stock."""

    overall_score: int
    valuation_score: float
    technical_score: float
    fundamental_score: float
    grade: str
    signals: list[StockSignal]


class StockScoreDetailResponse(BaseModel):
    """Stock score envelope."""

    data: StockScoreResponse
