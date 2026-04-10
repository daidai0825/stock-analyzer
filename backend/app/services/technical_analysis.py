"""Technical indicator calculations from OHLCV price data.

All computations use NumPy for vectorized operations.  No pandas dependency
is needed in this module — keeping the import surface minimal.

Each public method accepts a list of OHLCV dicts (the canonical format
returned by StockDataFetcher) and returns either:

  - list[dict]  — single-series indicators: [{"date": str, "value": float}, …]
  - dict        — multi-series indicators: {"<series>": list[dict], …}
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Sentinel returned when there is not enough data for a computation.
_EMPTY: list = []


def _to_series(prices: list[dict], field: str = "close") -> np.ndarray:
    """Extract a numeric field from the price list into a float64 array."""
    return np.array([p[field] for p in prices], dtype=np.float64)


def _dated(dates: list[str], values: np.ndarray) -> list[dict]:
    """Zip a list of date strings with a NumPy array into the standard format."""
    return [{"date": d, "value": float(v)} for d, v in zip(dates, values)]


class TechnicalAnalyzer:
    """Calculate technical indicators from OHLCV price data.

    All methods are pure (no side effects, no I/O).  The ``prices`` argument
    must be a list of dicts with at minimum the keys:
      ``date``, ``open``, ``high``, ``low``, ``close``.

    Dates are expected to be ISO-8601 strings (``"YYYY-MM-DD"``).
    """

    # ------------------------------------------------------------------
    # Simple Moving Average
    # ------------------------------------------------------------------

    def sma(self, prices: list[dict], period: int = 20) -> list[dict]:
        """Simple Moving Average over *period* days.

        Returns one value per date starting from index ``period - 1``.

        Args:
            prices: List of OHLCV dicts sorted by date ascending.
            period: Look-back window size.

        Returns:
            List of ``{"date": str, "value": float}`` dicts.
        """
        if not prices or len(prices) < period:
            return _EMPTY

        closes = _to_series(prices)
        dates = [p["date"] for p in prices]

        # Use a cumulative-sum trick for O(n) computation.
        cum = np.cumsum(closes)
        cum[period:] = cum[period:] - cum[:-period]
        sma_values = cum[period - 1 :] / period

        return _dated(dates[period - 1 :], sma_values)

    # ------------------------------------------------------------------
    # Exponential Moving Average
    # ------------------------------------------------------------------

    def ema(self, prices: list[dict], period: int = 20) -> list[dict]:
        """Exponential Moving Average over *period* days.

        Uses the standard multiplier ``k = 2 / (period + 1)``.
        The first EMA value is seeded with the SMA of the first *period* bars.

        Args:
            prices: List of OHLCV dicts sorted by date ascending.
            period: Look-back window size.

        Returns:
            List of ``{"date": str, "value": float}`` dicts starting from
            index ``period - 1``.
        """
        if not prices or len(prices) < period:
            return _EMPTY

        closes = _to_series(prices)
        dates = [p["date"] for p in prices]

        k = 2.0 / (period + 1)
        ema_values = np.empty(len(closes) - period + 1, dtype=np.float64)
        # Seed with the SMA of the first window.
        ema_values[0] = closes[:period].mean()
        for i in range(1, len(ema_values)):
            ema_values[i] = closes[period - 1 + i] * k + ema_values[i - 1] * (1 - k)

        return _dated(dates[period - 1 :], ema_values)

    # ------------------------------------------------------------------
    # Relative Strength Index (Wilder's smoothing)
    # ------------------------------------------------------------------

    def rsi(self, prices: list[dict], period: int = 14) -> list[dict]:
        """Relative Strength Index using Wilder's smoothing method.

        RSI range: 0 – 100.  The first RSI value appears at index
        ``period`` (we need *period* deltas, seeded with a simple average).

        Args:
            prices: List of OHLCV dicts sorted by date ascending.
            period: Look-back window (standard: 14).

        Returns:
            List of ``{"date": str, "value": float}`` dicts.
        """
        # Need at least period + 1 bars to produce one delta and one RSI value.
        if not prices or len(prices) <= period:
            return _EMPTY

        closes = _to_series(prices)
        dates = [p["date"] for p in prices]

        deltas = np.diff(closes)  # length = len(closes) - 1
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        # Seed average gain / loss with simple mean of first *period* deltas.
        avg_gain = gains[:period].mean()
        avg_loss = losses[:period].mean()

        rsi_values: list[float] = []

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0.0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100.0 - 100.0 / (1.0 + rs))

        # RSI values align to dates starting at index period + 1 (closes[period+1])
        # because we need closes[0..period] to produce period deltas then compute
        # the first rolling RSI from index period onward in the delta array.
        result_dates = dates[period + 1 :]
        return _dated(result_dates, np.array(rsi_values))

    # ------------------------------------------------------------------
    # MACD
    # ------------------------------------------------------------------

    def macd(
        self,
        prices: list[dict],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> dict[str, list[dict]]:
        """Moving Average Convergence/Divergence.

        Args:
            prices: List of OHLCV dicts sorted by date ascending.
            fast:   Fast EMA period (default 12).
            slow:   Slow EMA period (default 26).
            signal: Signal EMA period (default 9).

        Returns:
            ``{"macd": [...], "signal": [...], "histogram": [...]}``
            where each list contains ``{"date": str, "value": float}`` dicts.
            The series are aligned — they all start at the same date (the
            earliest date where both the slow EMA and signal EMA are defined).
        """
        empty: dict[str, list] = {"macd": [], "signal": [], "histogram": []}

        # Need enough bars to compute the slow EMA then the signal EMA on top.
        min_bars = slow + signal - 1
        if not prices or len(prices) < min_bars:
            return empty

        closes = _to_series(prices)
        dates = [p["date"] for p in prices]
        n = len(closes)

        def _ema_full(arr: np.ndarray, p: int) -> np.ndarray:
            """Return full-length EMA array; first p-1 values are NaN."""
            k = 2.0 / (p + 1)
            out = np.full(len(arr), np.nan)
            out[p - 1] = arr[:p].mean()
            for i in range(p, len(arr)):
                out[i] = arr[i] * k + out[i - 1] * (1 - k)
            return out

        fast_ema = _ema_full(closes, fast)
        slow_ema = _ema_full(closes, slow)

        # MACD line: defined wherever both EMAs are defined (from index slow-1).
        macd_line = fast_ema - slow_ema  # NaN where either is NaN

        # Signal EMA of the MACD line, seeded at index slow-1 (first valid MACD).
        signal_arr = np.full(n, np.nan)
        signal_start = slow - 1  # first valid MACD index
        # Need `signal` bars of MACD to compute first signal value.
        first_signal_idx = signal_start + signal - 1
        if first_signal_idx >= n:
            return empty

        k_sig = 2.0 / (signal + 1)
        signal_arr[first_signal_idx] = macd_line[signal_start:first_signal_idx + 1].mean()
        for i in range(first_signal_idx + 1, n):
            signal_arr[i] = macd_line[i] * k_sig + signal_arr[i - 1] * (1 - k_sig)

        # Trim all series to the range where signal is defined.
        trim_dates = dates[first_signal_idx:]
        macd_trimmed = macd_line[first_signal_idx:]
        signal_trimmed = signal_arr[first_signal_idx:]
        hist_trimmed = macd_trimmed - signal_trimmed

        return {
            "macd": _dated(trim_dates, macd_trimmed),
            "signal": _dated(trim_dates, signal_trimmed),
            "histogram": _dated(trim_dates, hist_trimmed),
        }

    # ------------------------------------------------------------------
    # Bollinger Bands
    # ------------------------------------------------------------------

    def bollinger_bands(
        self,
        prices: list[dict],
        period: int = 20,
        std_dev: float = 2.0,
    ) -> dict[str, list[dict]]:
        """Bollinger Bands (SMA ± std_dev * rolling standard deviation).

        Uses the population (ddof=0) standard deviation, consistent with
        most charting platforms.

        Args:
            prices:  List of OHLCV dicts sorted by date ascending.
            period:  Look-back window (default 20).
            std_dev: Number of standard deviations for the bands (default 2.0).

        Returns:
            ``{"upper": [...], "middle": [...], "lower": [...]}``
        """
        empty: dict[str, list] = {"upper": [], "middle": [], "lower": []}
        if not prices or len(prices) < period:
            return empty

        closes = _to_series(prices)
        dates = [p["date"] for p in prices]
        result_n = len(closes) - period + 1

        middle = np.empty(result_n)
        upper = np.empty(result_n)
        lower = np.empty(result_n)

        for i in range(result_n):
            window = closes[i : i + period]
            m = window.mean()
            s = window.std(ddof=0)
            middle[i] = m
            upper[i] = m + std_dev * s
            lower[i] = m - std_dev * s

        trim_dates = dates[period - 1 :]
        return {
            "upper": _dated(trim_dates, upper),
            "middle": _dated(trim_dates, middle),
            "lower": _dated(trim_dates, lower),
        }

    # ------------------------------------------------------------------
    # KD Stochastic (台股常用)
    # ------------------------------------------------------------------

    def kd(
        self,
        prices: list[dict],
        k_period: int = 9,
        d_period: int = 3,
    ) -> dict[str, list[dict]]:
        """KD Stochastic Oscillator (as commonly used on Taiwan exchanges).

        The raw ``%K`` is the stochastic of the *k_period* window:
            %K = (close - lowest_low) / (highest_high - lowest_low) * 100

        The smoothed K and D lines use simple moving averages of *d_period*:
            K = SMA(raw_%K, d_period)
            D = SMA(K, d_period)

        Args:
            prices:   List of OHLCV dicts sorted by date ascending.
            k_period: Fast stochastic look-back (default 9).
            d_period: Smoothing period for both K and D (default 3).

        Returns:
            ``{"k": [...], "d": [...]}``
        """
        empty: dict[str, list] = {"k": [], "d": []}
        min_bars = k_period + 2 * (d_period - 1)
        if not prices or len(prices) < min_bars:
            return empty

        highs = _to_series(prices, "high")
        lows = _to_series(prices, "low")
        closes = _to_series(prices)
        dates = [p["date"] for p in prices]
        n = len(prices)

        # Compute raw %K for each bar that has a full k_period window.
        raw_k_n = n - k_period + 1
        raw_k = np.empty(raw_k_n)
        for i in range(raw_k_n):
            h = highs[i : i + k_period].max()
            l = lows[i : i + k_period].min()
            c = closes[i + k_period - 1]
            raw_k[i] = 50.0 if h == l else (c - l) / (h - l) * 100.0

        # K = SMA(raw_%K, d_period)
        k_n = raw_k_n - d_period + 1
        k_vals = np.array(
            [raw_k[i : i + d_period].mean() for i in range(k_n)]
        )

        # D = SMA(K, d_period)
        d_n = k_n - d_period + 1
        d_vals = np.array(
            [k_vals[i : i + d_period].mean() for i in range(d_n)]
        )

        # Align dates: the last D value corresponds to the last price bar.
        # D starts at index: (k_period - 1) + (d_period - 1) + (d_period - 1)
        start_idx = k_period - 1 + 2 * (d_period - 1)
        trim_dates = dates[start_idx:]

        return {
            "k": _dated(trim_dates, k_vals[d_period - 1 :]),
            "d": _dated(trim_dates, d_vals),
        }

    # ------------------------------------------------------------------
    # Compute all default indicators
    # ------------------------------------------------------------------

    def compute_all(self, prices: list[dict]) -> dict[str, Any]:
        """Compute all default indicators and return as a keyed dict.

        Default parameters are used for every indicator.

        Args:
            prices: List of OHLCV dicts sorted by date ascending.

        Returns:
            Dict with keys: ``sma_20``, ``sma_50``, ``ema_20``, ``rsi_14``,
            ``macd``, ``bollinger_bands``, ``kd``.
        """
        return {
            "sma_20": self.sma(prices, period=20),
            "sma_50": self.sma(prices, period=50),
            "ema_20": self.ema(prices, period=20),
            "rsi_14": self.rsi(prices, period=14),
            "macd": self.macd(prices),
            "bollinger_bands": self.bollinger_bands(prices),
            "kd": self.kd(prices),
        }
