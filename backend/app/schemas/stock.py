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
    """Fundamental valuation metrics for a stock."""

    pe_ratio: float | None = None
    pb_ratio: float | None = None
    ps_ratio: float | None = None
    dividend_yield: float | None = None
    market_cap: float | None = None
    eps: float | None = None
    revenue: float | None = None
    profit_margin: float | None = None


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
