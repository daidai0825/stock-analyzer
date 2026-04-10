"""Multi-condition stock screener built on top of TechnicalAnalyzer.

Conditions are expressed as plain dicts, making them easily serialisable
from JSON API payloads:

    {"indicator": "rsi", "operator": "lt", "value": 30}
    {"indicator": "price", "operator": "gt", "value": 100}
    {"indicator": "volume", "operator": "gt", "value": 1_000_000}
    {"indicator": "sma_20", "operator": "gt", "value": 0}      # raw indicator
    {"indicator": "sma_cross", "operator": "above", "value": "sma_50"}

Supported operators:
    gt    — greater than
    gte   — greater than or equal
    lt    — less than
    lte   — less than or equal
    eq    — equal (float comparison with small tolerance)
    above — most recent value crossed above reference (cross detection)
    below — most recent value crossed below reference (cross detection)
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.services.data_fetcher import StockDataFetcher
from app.services.technical_analysis import TechnicalAnalyzer

logger = logging.getLogger(__name__)

# Mapping from condition indicator names to TechnicalAnalyzer method calls.
# Values are (method_name, kwargs) tuples.
_INDICATOR_MAP: dict[str, tuple[str, dict]] = {
    "sma_20": ("sma", {"period": 20}),
    "sma_50": ("sma", {"period": 50}),
    "sma_200": ("sma", {"period": 200}),
    "ema_20": ("ema", {"period": 20}),
    "ema_50": ("ema", {"period": 50}),
    "rsi": ("rsi", {"period": 14}),
    "rsi_14": ("rsi", {"period": 14}),
    "bollinger_upper": ("bollinger_bands", {}),
    "bollinger_lower": ("bollinger_bands", {}),
    "bollinger_middle": ("bollinger_bands", {}),
    "k": ("kd", {}),
    "d": ("kd", {}),
}

# Indicators that are sub-keys of a multi-output dict result.
_MULTI_OUTPUT_MAP: dict[str, tuple[str, str]] = {
    "bollinger_upper": ("bollinger_bands", "upper"),
    "bollinger_lower": ("bollinger_bands", "lower"),
    "bollinger_middle": ("bollinger_bands", "middle"),
    "macd_line": ("macd", "macd"),
    "macd_signal": ("macd", "signal"),
    "macd_histogram": ("macd", "histogram"),
    "k": ("kd", "k"),
    "d": ("kd", "d"),
}


def _last_value(series: list[dict]) -> float | None:
    """Return the most recent ``value`` from a date-value series, or None."""
    if not series:
        return None
    return series[-1]["value"]


def _prev_value(series: list[dict]) -> float | None:
    """Return the second-to-last value, or None."""
    if len(series) < 2:
        return None
    return series[-2]["value"]


class StockScreener:
    """Multi-condition stock screener.

    Applies ALL conditions (logical AND) to each symbol in the market
    universe and returns matching symbols with their current indicator
    snapshot.
    """

    def __init__(self, analyzer: TechnicalAnalyzer, fetcher: StockDataFetcher) -> None:
        self.analyzer = analyzer
        self.fetcher = fetcher

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def screen(
        self,
        conditions: list[dict],
        market: str = "US",
        limit: int = 50,
        db: AsyncSession | None = None,
    ) -> list[dict]:
        """Screen stocks matching ALL supplied conditions.

        Args:
            conditions: List of condition dicts.  Each dict must have keys:
                        ``indicator``, ``operator``, ``value``.
            market:     Market filter — ``"US"`` or ``"TW"``.
            limit:      Maximum number of results to return.
            db:         Optional AsyncSession used to resolve the symbol
                        universe from the database.  When ``None``, the
                        universe is empty and the screener returns nothing.

        Returns:
            List of dicts ``{"symbol": str, "indicators": dict}`` for each
            matching symbol.
        """
        if not conditions:
            return []

        if db is None:
            logger.warning("screen() called without a db session — no universe available")
            return []

        symbols = await self.get_universe(market, db)
        if not symbols:
            logger.info("screen(): empty universe for market=%s", market)
            return []

        results: list[dict] = []
        for symbol in symbols:
            if len(results) >= limit:
                break
            try:
                prices = await self.fetcher.fetch_history(symbol, period="6mo")
                if not prices:
                    continue
                indicators = self._compute_indicators(prices)
                if all(
                    self._evaluate_condition(cond, prices, indicators)
                    for cond in conditions
                ):
                    results.append(
                        {
                            "symbol": symbol,
                            "indicators": self._snapshot(indicators),
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("screen(): error processing symbol=%s: %s", symbol, exc)
                continue

        return results

    # Default universe when the database has no stock entries.
    _DEFAULT_US = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
        "JPM", "V", "UNH", "HD", "PG", "MA", "JNJ", "ABBV", "XOM", "COST",
        "MRK", "AVGO", "KO", "PEP", "WMT", "LLY", "ADBE", "CRM", "TMO",
        "NFLX", "AMD", "INTC", "CSCO", "DIS", "QCOM", "TXN", "BA",
    ]
    _DEFAULT_TW = [
        "2330", "2317", "2454", "2308", "2382", "2881", "2882", "2891",
        "2303", "2412", "1303", "1301", "2886", "3711", "2884", "2357",
        "3008", "2395", "6505", "1216",
    ]

    async def get_universe(self, market: str, db: AsyncSession) -> list[str]:
        """Return all stock symbols for the given market from the database.

        Falls back to a built-in default universe when the database has no
        entries for the requested market.

        Args:
            market: ``"US"`` or ``"TW"``.
            db:     Active async SQLAlchemy session.

        Returns:
            List of ticker symbol strings.
        """
        result = await db.execute(
            select(Stock.symbol).where(Stock.market == market.upper())
        )
        symbols = [row[0] for row in result.all()]
        if symbols:
            return symbols
        # Fall back to built-in default universe
        if market.upper() == "TW":
            return self._DEFAULT_TW
        return self._DEFAULT_US

    # ------------------------------------------------------------------
    # Condition evaluation
    # ------------------------------------------------------------------

    def _evaluate_condition(
        self,
        condition: dict,
        prices: list[dict],
        indicators: dict,
    ) -> bool:
        """Evaluate a single screening condition against computed data.

        Args:
            condition:  Condition dict with ``indicator``, ``operator``,
                        ``value`` keys.
            prices:     Raw OHLCV list (used for ``price`` / ``volume``
                        conditions).
            indicators: Pre-computed indicator dict from
                        ``_compute_indicators()``.

        Returns:
            ``True`` if the condition is satisfied, ``False`` otherwise.
        """
        try:
            indicator: str = condition["indicator"]
            operator: str = condition["operator"]
            threshold: Any = condition["value"]

            lhs = self._resolve_lhs(indicator, prices, indicators)
            if lhs is None:
                return False

            # Cross operators require two consecutive values.
            if operator in ("above", "below"):
                return self._evaluate_cross(operator, indicator, threshold, indicators)

            rhs = self._resolve_rhs(threshold, prices, indicators)
            if rhs is None:
                return False

            return self._compare(lhs, operator, rhs)
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("_evaluate_condition error: %s  condition=%s", exc, condition)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_indicators(self, prices: list[dict]) -> dict:
        """Compute all needed indicator series from OHLCV prices."""
        return {
            "sma_20": self.analyzer.sma(prices, period=20),
            "sma_50": self.analyzer.sma(prices, period=50),
            "sma_200": self.analyzer.sma(prices, period=200),
            "ema_20": self.analyzer.ema(prices, period=20),
            "ema_50": self.analyzer.ema(prices, period=50),
            "rsi": self.analyzer.rsi(prices, period=14),
            "rsi_14": self.analyzer.rsi(prices, period=14),
            "macd": self.analyzer.macd(prices),
            "bollinger_bands": self.analyzer.bollinger_bands(prices),
            "kd": self.analyzer.kd(prices),
        }

    def _snapshot(self, indicators: dict) -> dict:
        """Reduce all indicator series to their most recent value."""
        snap: dict = {}
        for key, val in indicators.items():
            if isinstance(val, list):
                snap[key] = _last_value(val)
            elif isinstance(val, dict):
                snap[key] = {
                    sub_key: _last_value(sub_val)
                    for sub_key, sub_val in val.items()
                    if isinstance(sub_val, list)
                }
        return snap

    def _resolve_lhs(
        self,
        indicator: str,
        prices: list[dict],
        indicators: dict,
    ) -> float | None:
        """Resolve the left-hand-side value for a condition."""
        if indicator == "price":
            return prices[-1]["close"] if prices else None
        if indicator == "volume":
            return float(prices[-1]["volume"]) if prices else None
        if indicator in _MULTI_OUTPUT_MAP:
            parent_key, sub_key = _MULTI_OUTPUT_MAP[indicator]
            parent = indicators.get(parent_key, {})
            return _last_value(parent.get(sub_key, []))
        series = indicators.get(indicator)
        if isinstance(series, list):
            return _last_value(series)
        return None

    def _resolve_rhs(
        self,
        threshold: Any,
        prices: list[dict],
        indicators: dict,
    ) -> float | None:
        """Resolve the right-hand-side value from a threshold spec."""
        if isinstance(threshold, (int, float)):
            return float(threshold)
        if isinstance(threshold, str):
            # Allow referencing another indicator as the RHS.
            return self._resolve_lhs(threshold, prices, indicators)
        return None

    @staticmethod
    def _compare(lhs: float, operator: str, rhs: float) -> bool:
        """Compare two floats using the named operator."""
        if operator == "gt":
            return lhs > rhs
        if operator == "gte":
            return lhs >= rhs
        if operator == "lt":
            return lhs < rhs
        if operator == "lte":
            return lhs <= rhs
        if operator == "eq":
            return abs(lhs - rhs) < 1e-9
        logger.warning("_compare: unknown operator %r", operator)
        return False

    def _evaluate_cross(
        self,
        operator: str,
        indicator: str,
        reference: str,
        indicators: dict,
    ) -> bool:
        """Detect a crossover event between *indicator* and *reference*.

        ``above`` — indicator crossed above reference on the most recent bar.
        ``below`` — indicator crossed below reference on the most recent bar.

        A cross is detected by comparing the previous bar's relative position
        to the current bar's relative position.
        """
        series = indicators.get(indicator)
        ref_series = indicators.get(reference)
        if not isinstance(series, list) or not isinstance(ref_series, list):
            return False

        curr_lhs = _last_value(series)
        curr_rhs = _last_value(ref_series)
        prev_lhs = _prev_value(series)
        prev_rhs = _prev_value(ref_series)

        if any(v is None for v in (curr_lhs, curr_rhs, prev_lhs, prev_rhs)):
            return False

        if operator == "above":
            # Was below (or equal) before, now above.
            return prev_lhs <= prev_rhs and curr_lhs > curr_rhs
        if operator == "below":
            # Was above (or equal) before, now below.
            return prev_lhs >= prev_rhs and curr_lhs < curr_rhs
        return False
