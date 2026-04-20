"""Stock data API routes.

Endpoints
---------
GET  /api/v1/stocks                      — paginated stock list with optional
                                           market and search filters
GET  /api/v1/stocks/{symbol}             — stock detail (DB + live fallback)
GET  /api/v1/stocks/{symbol}/history     — OHLCV history (cache-first)
GET  /api/v1/stocks/{symbol}/indicators  — technical indicators
GET  /api/v1/stocks/{symbol}/valuation   — fundamental valuation metrics
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_analyzer, get_cache, get_fetcher, get_scorer, get_valuation
from app.core.cache import CacheManager
from app.db.session import get_db
from app.models.stock import Stock
from app.schemas.stock import (
    IndicatorPointResponse,
    PricePointResponse,
    StockDetailResponse,
    StockHistoryResponse,
    StockIndicatorsResponse,
    StockListResponse,
    StockResponse,
    StockScoreDetailResponse,
    StockScoreResponse,
    StockSignal,
    StockValuationResponse,
    ValuationResponse,
)
from app.schemas.common import MetaResponse
from app.services.data_fetcher import StockDataFetcher
from app.services.stock_scorer import StockScorer
from app.services.technical_analysis import TechnicalAnalyzer
from app.services.valuation import ValuationAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MULTI_SERIES_INDICATORS = {"macd", "bollinger_bands", "kd"}


def _build_indicator_data(
    name: str,
    result: list | dict,
) -> list[IndicatorPointResponse] | dict[str, list[IndicatorPointResponse]]:
    """Convert a raw TechnicalAnalyzer result to the response schema format."""
    if isinstance(result, dict):
        # Multi-series indicator (macd, bollinger_bands, kd)
        return {
            sub_key: [IndicatorPointResponse(**point) for point in series]
            for sub_key, series in result.items()
            if isinstance(series, list)
        }
    # Single-series indicator
    return [IndicatorPointResponse(**point) for point in result]


def _compute_indicator(
    name: str,
    prices: list[dict],
    analyzer: TechnicalAnalyzer,
) -> list | dict | None:
    """Dispatch an indicator name to the correct TechnicalAnalyzer method.

    Returns None when the name is unrecognised.
    """
    name = name.strip().lower()

    if name in ("sma", "sma_20"):
        return analyzer.sma(prices, period=20)
    if name == "sma_50":
        return analyzer.sma(prices, period=50)
    if name == "sma_200":
        return analyzer.sma(prices, period=200)
    if name in ("ema", "ema_20"):
        return analyzer.ema(prices, period=20)
    if name == "ema_50":
        return analyzer.ema(prices, period=50)
    if name in ("rsi", "rsi_14"):
        return analyzer.rsi(prices, period=14)
    if name == "macd":
        return analyzer.macd(prices)
    if name in ("bb", "bollinger_bands", "bollinger"):
        return analyzer.bollinger_bands(prices)
    if name == "kd":
        return analyzer.kd(prices)
    if name == "all":
        return analyzer.compute_all(prices)
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


# Default popular symbols when the database has no stock entries.
_DEFAULT_US_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "V", "UNH", "HD", "PG", "MA", "JNJ", "XOM", "COST",
    "NFLX", "AMD", "INTC", "CRM",
]
_DEFAULT_TW_SYMBOLS = [
    "2330", "2317", "2454", "2308", "2382", "2881", "2882", "2891",
    "2303", "2412", "1303", "1301", "2886", "3711", "2884",
]


@router.get("", response_model=StockListResponse)
async def list_stocks(
    market: str = Query("US", description="Market filter: US or TW"),
    q: str = Query("", description="Search symbol or name (case-insensitive)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    fetcher: StockDataFetcher = Depends(get_fetcher),
) -> StockListResponse:
    """Return a paginated list of stocks, optionally filtered by market and
    keyword search.  Falls back to live-fetched popular symbols when the
    database is empty.
    """
    base_query = select(Stock)

    if market:
        base_query = base_query.where(Stock.market == market.upper())

    if q:
        pattern = f"%{q}%"
        base_query = base_query.where(
            or_(
                Stock.symbol.ilike(pattern),
                Stock.name.ilike(pattern),
            )
        )

    # Total count for meta
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    if total > 0:
        # Paginated fetch from DB
        offset = (page - 1) * limit
        paginated = base_query.order_by(Stock.symbol).offset(offset).limit(limit)
        result = await db.execute(paginated)
        stocks = result.scalars().all()
        return StockListResponse(
            data=[StockResponse.model_validate(s) for s in stocks],
            meta=MetaResponse(total=total, page=page, limit=limit),
        )

    # DB is empty — return popular symbols from live data sources.
    if q:
        # For search queries when DB is empty, try live fetch for the symbol.
        info = await fetcher.fetch_stock_info(q.strip().upper())
        if info and info.get("name"):
            return StockListResponse(
                data=[StockResponse(
                    symbol=info.get("symbol", q.upper()),
                    name=info.get("name", ""),
                    market=info.get("market", "US"),
                    industry=info.get("industry"),
                )],
                meta=MetaResponse(total=1, page=1, limit=limit),
            )
        return StockListResponse(data=[], meta=MetaResponse(total=0, page=1, limit=limit))

    defaults = _DEFAULT_TW_SYMBOLS if market.upper() == "TW" else _DEFAULT_US_SYMBOLS
    offset = (page - 1) * limit
    page_symbols = defaults[offset : offset + limit]

    data: list[StockResponse] = []
    for sym in page_symbols:
        data.append(StockResponse(
            symbol=sym,
            name=sym,
            market=market.upper(),
        ))

    return StockListResponse(
        data=data,
        meta=MetaResponse(total=len(defaults), page=page, limit=limit),
    )


@router.get("/{symbol}", response_model=StockDetailResponse)
async def get_stock(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    fetcher: StockDataFetcher = Depends(get_fetcher),
) -> StockDetailResponse:
    """Return stock detail by symbol.

    Checks the database first.  If not found, attempts a live fetch from
    the appropriate data source (yfinance / FinMind).  Returns 404 when
    the symbol cannot be resolved at all.
    """
    symbol_upper = symbol.upper()

    # 1. Try database
    result = await db.execute(select(Stock).where(Stock.symbol == symbol_upper))
    stock = result.scalar_one_or_none()

    if stock is not None:
        return StockDetailResponse(data=StockResponse.model_validate(stock))

    # 2. Try live data source
    info = await fetcher.fetch_stock_info(symbol_upper)
    if not info or not info.get("name"):
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Stock '{symbol_upper}' not found.", "code": "STOCK_NOT_FOUND"},
        )

    return StockDetailResponse(
        data=StockResponse(
            symbol=info.get("symbol", symbol_upper),
            name=info.get("name", ""),
            market=info.get("market", "US"),
            industry=info.get("industry"),
            description=info.get("description"),
        )
    )


@router.get("/{symbol}/history", response_model=StockHistoryResponse)
async def get_stock_history(
    symbol: str,
    period: str = Query("1y", description="Period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,max"),
    interval: str = Query("1d", description="Interval: 1d,1wk,1mo"),
    cache: CacheManager = Depends(get_cache),
    fetcher: StockDataFetcher = Depends(get_fetcher),
) -> StockHistoryResponse:
    """Return historical OHLCV data for a stock.

    Checks Redis cache first.  On cache miss, fetches from the data source
    and caches the result for 1 hour before returning.
    """
    symbol_upper = symbol.upper()

    # Cache key encodes both period and interval to avoid collisions.
    cache_key_period = f"{period}_{interval}"

    # 1. Cache hit
    cached = await cache.get_stock_data(symbol_upper, cache_key_period)
    if cached is not None:
        return StockHistoryResponse(
            data=[PricePointResponse(**r) for r in cached]
        )

    # 2. Fetch from source
    records = await fetcher.fetch_history(symbol_upper, period=period, interval=interval)

    if not records:
        # Return empty list rather than 404 — valid symbol with no data for
        # the requested period is a normal business scenario.
        return StockHistoryResponse(data=[])

    # 3. Cache and return
    await cache.set_stock_data(symbol_upper, cache_key_period, records)
    return StockHistoryResponse(
        data=[PricePointResponse(**r) for r in records]
    )


@router.get("/{symbol}/indicators", response_model=StockIndicatorsResponse)
async def get_stock_indicators(
    symbol: str,
    indicators: str = Query(
        "sma,rsi",
        description=(
            "Comma-separated indicator names. "
            "Supported: sma, sma_20, sma_50, sma_200, ema, ema_20, ema_50, "
            "rsi, rsi_14, macd, bollinger_bands, kd, all"
        ),
    ),
    period: str = Query("1y", description="History period used for indicator calculation"),
    cache: CacheManager = Depends(get_cache),
    fetcher: StockDataFetcher = Depends(get_fetcher),
    analyzer: TechnicalAnalyzer = Depends(get_analyzer),
) -> StockIndicatorsResponse:
    """Compute and return technical indicators for a stock.

    Fetches historical prices (using cache if available), then runs the
    requested indicator calculations via TechnicalAnalyzer.
    """
    symbol_upper = symbol.upper()

    # Fetch history (reuse cached data when available)
    cached = await cache.get_stock_data(symbol_upper, period)
    if cached is not None:
        prices = cached
    else:
        prices = await fetcher.fetch_history(symbol_upper, period=period)
        if prices:
            await cache.set_stock_data(symbol_upper, period, prices)

    if not prices:
        return StockIndicatorsResponse(data={})

    # Parse requested indicator names
    requested = [name.strip().lower() for name in indicators.split(",") if name.strip()]

    result_data: dict = {}
    for name in requested:
        if name == "all":
            # Expand "all" into every default indicator
            all_indicators = analyzer.compute_all(prices)
            for key, value in all_indicators.items():
                result_data[key] = _build_indicator_data(key, value)
        else:
            computed = _compute_indicator(name, prices, analyzer)
            if computed is None:
                logger.warning("Unknown indicator requested: %r — skipping", name)
                continue
            result_data[name] = _build_indicator_data(name, computed)

    return StockIndicatorsResponse(data=result_data)


@router.get("/{symbol}/valuation", response_model=StockValuationResponse)
async def get_stock_valuation(
    symbol: str,
    valuation_svc: ValuationAnalyzer = Depends(get_valuation),
) -> StockValuationResponse:
    """Return fundamental valuation metrics for a stock.

    Retrieves data from yfinance (US) or FinMind (TW) depending on the
    symbol.  All fields may be ``null`` when the data source does not
    provide them.
    """
    symbol_upper = symbol.upper()
    metrics = await valuation_svc.get_valuation(symbol_upper)

    return StockValuationResponse(data=ValuationResponse(**metrics))


@router.get("/{symbol}/score", response_model=StockScoreDetailResponse)
async def get_stock_score(
    symbol: str,
    scorer: StockScorer = Depends(get_scorer),
) -> StockScoreDetailResponse:
    """Return composite quality score for a stock.

    Aggregates valuation, technical, and fundamental analyses into a single
    score and grade.  The ``signals`` list provides human-readable
    positive/negative/neutral observations that drove the score.
    """
    symbol_upper = symbol.upper()
    result = await scorer.score(symbol_upper)

    return StockScoreDetailResponse(
        data=StockScoreResponse(
            overall_score=result.overall_score,
            valuation_score=result.valuation_score,
            technical_score=result.technical_score,
            fundamental_score=result.fundamental_score,
            grade=result.grade,
            signals=[StockSignal(**s) for s in result.signals],
        )
    )
