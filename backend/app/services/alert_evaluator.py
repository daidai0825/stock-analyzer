"""Alert evaluation service.

Evaluates alert conditions against live market data fetched via
StockDataFetcher and TechnicalAnalyzer.  Each ``_check_*`` method
returns a ``(triggered: bool, current_value: float)`` tuple.
"""

import logging

from app.models.alert import Alert
from app.services.data_fetcher import StockDataFetcher
from app.services.technical_analysis import TechnicalAnalyzer

logger = logging.getLogger(__name__)

# Number of historical bars fetched for indicator-based checks.
# 100 days is enough for RSI(14), SMA(50), etc.
_INDICATOR_HISTORY_PERIOD = "6mo"


class AlertEvaluationError(Exception):
    """Raised when an alert cannot be evaluated due to missing/bad data."""


class AlertEvaluator:
    """Evaluate alert conditions against current market data.

    Args:
        fetcher:  Shared :class:`StockDataFetcher` instance.
        analyzer: Shared :class:`TechnicalAnalyzer` instance.
    """

    def __init__(self, fetcher: StockDataFetcher, analyzer: TechnicalAnalyzer) -> None:
        self.fetcher = fetcher
        self.analyzer = analyzer

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate(self, alert: Alert) -> tuple[bool, float]:
        """Check whether *alert*'s condition is currently met.

        Args:
            alert: :class:`~app.models.alert.Alert` ORM instance.

        Returns:
            ``(triggered, current_value)`` where *triggered* is ``True``
            when the condition is met and *current_value* is the latest
            relevant market value (price, indicator reading, etc.).

        Raises:
            :class:`AlertEvaluationError` for unknown alert types or
            insufficient market data.
        """
        dispatch: dict[str, object] = {
            "price_above": self._check_price_above,
            "price_below": self._check_price_below,
            "rsi_above": self._check_rsi_above,
            "rsi_below": self._check_rsi_below,
            "sma_cross": self._check_sma_cross,
            "volume_above": self._check_volume_above,
        }

        handler = dispatch.get(alert.alert_type)
        if handler is None:
            raise AlertEvaluationError(f"Unknown alert_type: {alert.alert_type!r}")

        return await handler(alert.symbol, alert.condition)  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Price checks
    # ------------------------------------------------------------------

    async def _check_price_above(
        self, symbol: str, condition: dict
    ) -> tuple[bool, float]:
        """Return True when the latest close is strictly above *target_price*."""
        target = float(condition["target_price"])
        price = await self._latest_close(symbol)
        return price > target, price

    async def _check_price_below(
        self, symbol: str, condition: dict
    ) -> tuple[bool, float]:
        """Return True when the latest close is strictly below *target_price*."""
        target = float(condition["target_price"])
        price = await self._latest_close(symbol)
        return price < target, price

    # ------------------------------------------------------------------
    # RSI checks
    # ------------------------------------------------------------------

    async def _check_rsi_above(
        self, symbol: str, condition: dict
    ) -> tuple[bool, float]:
        """Return True when the RSI reading is above *threshold*.

        Condition keys:
            - ``period`` (int, default 14): RSI look-back window.
            - ``threshold`` (float): Trigger level (e.g. 70).
        """
        period = int(condition.get("period", 14))
        threshold = float(condition["threshold"])
        rsi_value = await self._latest_rsi(symbol, period)
        return rsi_value > threshold, rsi_value

    async def _check_rsi_below(
        self, symbol: str, condition: dict
    ) -> tuple[bool, float]:
        """Return True when the RSI reading is below *threshold*.

        Condition keys:
            - ``period`` (int, default 14): RSI look-back window.
            - ``threshold`` (float): Trigger level (e.g. 30).
        """
        period = int(condition.get("period", 14))
        threshold = float(condition["threshold"])
        rsi_value = await self._latest_rsi(symbol, period)
        return rsi_value < threshold, rsi_value

    # ------------------------------------------------------------------
    # SMA crossover check
    # ------------------------------------------------------------------

    async def _check_sma_cross(
        self, symbol: str, condition: dict
    ) -> tuple[bool, float]:
        """Return True when the short SMA is above the long SMA (golden cross).

        Condition keys:
            - ``fast_period`` (int, default 20): Short-window SMA period.
            - ``slow_period`` (int, default 50): Long-window SMA period.

        The returned *current_value* is the latest fast-SMA reading.
        """
        fast_period = int(condition.get("fast_period", 20))
        slow_period = int(condition.get("slow_period", 50))

        prices = await self._fetch_prices(symbol, _INDICATOR_HISTORY_PERIOD)

        fast_series = self.analyzer.sma(prices, period=fast_period)
        slow_series = self.analyzer.sma(prices, period=slow_period)

        if not fast_series or not slow_series:
            raise AlertEvaluationError(
                f"Insufficient data for SMA cross check on {symbol!r}"
            )

        fast_val = fast_series[-1]["value"]
        slow_val = slow_series[-1]["value"]
        return fast_val > slow_val, fast_val

    # ------------------------------------------------------------------
    # Volume check
    # ------------------------------------------------------------------

    async def _check_volume_above(
        self, symbol: str, condition: dict
    ) -> tuple[bool, float]:
        """Return True when the latest session's volume exceeds *threshold*.

        Condition keys:
            - ``threshold`` (float | int): Volume trigger level.
        """
        threshold = float(condition["threshold"])
        prices = await self._fetch_prices(symbol, "5d")
        if not prices:
            raise AlertEvaluationError(
                f"No price data available for {symbol!r}"
            )
        latest_volume = float(prices[-1]["volume"])
        return latest_volume > threshold, latest_volume

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_prices(self, symbol: str, period: str) -> list[dict]:
        """Fetch OHLCV history and raise if empty."""
        prices = await self.fetcher.fetch_history(symbol, period=period, interval="1d")
        if not prices:
            raise AlertEvaluationError(
                f"No price data returned for symbol={symbol!r} period={period!r}"
            )
        return prices

    async def _latest_close(self, symbol: str) -> float:
        """Return the most recent closing price for *symbol*."""
        prices = await self._fetch_prices(symbol, "5d")
        return float(prices[-1]["close"])

    async def _latest_rsi(self, symbol: str, period: int) -> float:
        """Compute RSI for *symbol* and return the most recent value."""
        prices = await self._fetch_prices(symbol, _INDICATOR_HISTORY_PERIOD)
        rsi_series = self.analyzer.rsi(prices, period=period)
        if not rsi_series:
            raise AlertEvaluationError(
                f"Insufficient data for RSI({period}) on {symbol!r}"
            )
        return float(rsi_series[-1]["value"])
