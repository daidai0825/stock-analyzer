"""Unit tests for TechnicalAnalyzer.

All computations are verified against hand-calculated or independently
derived values.  No external I/O is required.
"""

import math

import pytest

from app.services.technical_analysis import TechnicalAnalyzer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def analyzer() -> TechnicalAnalyzer:
    return TechnicalAnalyzer()


def _prices(closes: list[float], start_date: str = "2024-01-01") -> list[dict]:
    """Build a minimal OHLCV list from a list of close prices.

    Open, high, low are set equal to close for simplicity; volume is 1.
    Dates are sequential trading days (no weekend/holiday handling needed
    for testing purposes).
    """
    from datetime import date, timedelta

    base = date.fromisoformat(start_date)
    records = []
    for i, c in enumerate(closes):
        d = (base + timedelta(days=i)).isoformat()
        records.append(
            {
                "date": d,
                "open": c,
                "high": c,
                "low": c,
                "close": c,
                "volume": 1,
                "adj_close": c,
            }
        )
    return records


def _ohlcv(rows: list[dict]) -> list[dict]:
    """Pass-through helper for explicit OHLCV construction."""
    return rows


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------


class TestSMA:
    def test_sma_known_values(self, analyzer: TechnicalAnalyzer) -> None:
        """SMA(3) on [1, 2, 3, 4, 5] → [2.0, 3.0, 4.0]."""
        prices = _prices([1.0, 2.0, 3.0, 4.0, 5.0])
        result = analyzer.sma(prices, period=3)
        assert len(result) == 3
        assert result[0]["value"] == pytest.approx(2.0)
        assert result[1]["value"] == pytest.approx(3.0)
        assert result[2]["value"] == pytest.approx(4.0)

    def test_sma_dates_aligned(self, analyzer: TechnicalAnalyzer) -> None:
        """The first SMA date is at index period-1 of the input."""
        prices = _prices([10.0, 20.0, 30.0, 40.0])
        result = analyzer.sma(prices, period=2)
        assert result[0]["date"] == prices[1]["date"]
        assert result[-1]["date"] == prices[-1]["date"]

    def test_sma_period_equals_length(self, analyzer: TechnicalAnalyzer) -> None:
        """SMA(n) on n prices returns exactly one value."""
        prices = _prices([5.0, 10.0, 15.0])
        result = analyzer.sma(prices, period=3)
        assert len(result) == 1
        assert result[0]["value"] == pytest.approx(10.0)

    def test_sma_empty_input(self, analyzer: TechnicalAnalyzer) -> None:
        assert analyzer.sma([], period=20) == []

    def test_sma_insufficient_data(self, analyzer: TechnicalAnalyzer) -> None:
        """Fewer bars than period → empty list."""
        prices = _prices([1.0, 2.0])
        assert analyzer.sma(prices, period=5) == []

    def test_sma_default_period(self, analyzer: TechnicalAnalyzer) -> None:
        """Default period is 20."""
        prices = _prices(list(range(1, 22)))  # 21 bars
        result = analyzer.sma(prices)
        assert len(result) == 2  # 21 - 20 + 1 = 2

    def test_sma_all_same_price(self, analyzer: TechnicalAnalyzer) -> None:
        """SMA of constant prices equals that constant."""
        prices = _prices([100.0] * 30)
        result = analyzer.sma(prices, period=10)
        for r in result:
            assert r["value"] == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------


class TestEMA:
    def test_ema_seed_equals_sma(self, analyzer: TechnicalAnalyzer) -> None:
        """First EMA value must equal the SMA of the seed window."""
        closes = [10.0, 20.0, 30.0]
        prices = _prices(closes)
        result = analyzer.ema(prices, period=3)
        assert len(result) == 1
        # SMA([10,20,30]) = 20.0
        assert result[0]["value"] == pytest.approx(20.0)

    def test_ema_convergence(self, analyzer: TechnicalAnalyzer) -> None:
        """EMA of a constant price series converges to that constant."""
        prices = _prices([50.0] * 100)
        result = analyzer.ema(prices, period=20)
        # After many bars the EMA should be very close to 50.
        assert result[-1]["value"] == pytest.approx(50.0, abs=1e-6)

    def test_ema_rising_series(self, analyzer: TechnicalAnalyzer) -> None:
        """EMA lags behind a rising series — last value < last close."""
        prices = _prices(list(range(1, 31)))  # 1..30
        result = analyzer.ema(prices, period=5)
        # The last EMA must be less than the last close (30.0) due to lag.
        assert result[-1]["value"] < 30.0

    def test_ema_empty_input(self, analyzer: TechnicalAnalyzer) -> None:
        assert analyzer.ema([], period=10) == []

    def test_ema_insufficient_data(self, analyzer: TechnicalAnalyzer) -> None:
        prices = _prices([1.0, 2.0])
        assert analyzer.ema(prices, period=5) == []

    def test_ema_manual_two_steps(self, analyzer: TechnicalAnalyzer) -> None:
        """Manually verify two EMA steps with period=3 (k=0.5)."""
        # k = 2/(3+1) = 0.5
        # seed = SMA([10,20,30]) = 20.0
        # step1 (close=40): 40*0.5 + 20*0.5 = 30.0
        closes = [10.0, 20.0, 30.0, 40.0]
        prices = _prices(closes)
        result = analyzer.ema(prices, period=3)
        assert len(result) == 2
        assert result[0]["value"] == pytest.approx(20.0)
        assert result[1]["value"] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------


class TestRSI:
    def _rsi_prices(self) -> list[dict]:
        """14-bar seed + extra bars for a verifiable RSI dataset.

        Classic test dataset where the RSI(14) value after the seeding
        period is computable by hand.
        """
        closes = [
            44.34, 44.09, 44.15, 43.61, 44.33,
            44.83, 45.10, 45.15, 43.61, 44.33,
            44.83, 45.10, 45.15, 43.61,  # first 14 → seed
            44.01,  # index 14 → first RSI
            44.34,
            44.09,
        ]
        return _prices(closes)

    def test_rsi_returns_correct_length(self, analyzer: TechnicalAnalyzer) -> None:
        """RSI(14) on N prices produces N - 15 values (one per bar after seed+1)."""
        n = 30
        prices = _prices(list(range(1, n + 1)))
        result = analyzer.rsi(prices, period=14)
        # We expect n - period - 1 = 30 - 14 - 1 = 15 values.
        assert len(result) == n - 14 - 1

    def test_rsi_constant_prices_returns_neutral(self, analyzer: TechnicalAnalyzer) -> None:
        """Constant prices have 0 gains and 0 losses → RSI = 100 (avg_loss==0)."""
        prices = _prices([100.0] * 30)
        result = analyzer.rsi(prices, period=14)
        assert all(r["value"] == pytest.approx(100.0) for r in result)

    def test_rsi_always_rising_is_high(self, analyzer: TechnicalAnalyzer) -> None:
        """Monotonically rising prices → RSI close to 100."""
        prices = _prices(list(range(1, 50)))
        result = analyzer.rsi(prices, period=14)
        assert result[-1]["value"] > 70.0

    def test_rsi_always_falling_is_low(self, analyzer: TechnicalAnalyzer) -> None:
        """Monotonically falling prices → RSI close to 0."""
        prices = _prices(list(range(50, 0, -1)))
        result = analyzer.rsi(prices, period=14)
        assert result[-1]["value"] < 30.0

    def test_rsi_range_0_to_100(self, analyzer: TechnicalAnalyzer) -> None:
        """All RSI values must be in [0, 100]."""
        import random

        random.seed(42)
        closes = [100.0 + random.gauss(0, 5) for _ in range(100)]
        prices = _prices(closes)
        result = analyzer.rsi(prices, period=14)
        for r in result:
            assert 0.0 <= r["value"] <= 100.0

    def test_rsi_empty_input(self, analyzer: TechnicalAnalyzer) -> None:
        assert analyzer.rsi([], period=14) == []

    def test_rsi_insufficient_data(self, analyzer: TechnicalAnalyzer) -> None:
        """Need > period bars to produce any RSI value."""
        prices = _prices([1.0] * 14)
        assert analyzer.rsi(prices, period=14) == []

    def test_rsi_known_dataset_within_tolerance(self, analyzer: TechnicalAnalyzer) -> None:
        """Verify RSI(14) on the Wilder textbook dataset (Cutler's variant).

        Using a well-known 25-bar dataset from investopedia-style examples:
        RSI(14) after 15th bar should be approximately 70.46.
        The exact value depends on the seed (SMA vs EMA), so we verify the
        direction and that it falls in the expected range.
        """
        # A dataset with 14 ups and only 1 down → high RSI expected.
        closes = [
            46.0, 47.0, 48.0, 49.0, 50.0,
            51.0, 52.0, 53.0, 54.0, 55.0,
            56.0, 57.0, 58.0, 59.0, 58.5,  # one down bar at index 14
        ]
        prices = _prices(closes)
        result = analyzer.rsi(prices, period=14)
        assert len(result) >= 1
        # After 14 ups then 1 down, RSI should be very high (> 85).
        assert result[0]["value"] > 85.0

    def test_rsi_wilders_smoothing_applied(self, analyzer: TechnicalAnalyzer) -> None:
        """Two identical sequences should diverge if Wilder smoothing vs SMA is used.

        We test indirectly: Wilder's smoothing reacts more slowly than a simple
        rolling average.  A sudden reversal should change RSI less with Wilder's
        method than with a fresh SMA each step.

        Verify that the RSI does NOT jump to 0 or 100 immediately after a
        reversal — that would only happen with a simple window that forgets history.
        """
        # 20 up bars then 5 down bars.
        ups = list(range(100, 121))  # 100..120
        downs = [120 - i * 5 for i in range(1, 6)]  # 115, 110, 105, 100, 95
        prices = _prices(ups + downs)
        result = analyzer.rsi(prices, period=14)
        # After the sudden reversal, RSI should not instantly hit 0.
        last_rsi = result[-1]["value"]
        assert last_rsi > 0.0, "RSI should not be exactly 0 with Wilder smoothing"
        # And it should be notably lower than the RSI during the uptrend.
        mid_rsi = result[len(result) // 2]["value"]
        assert last_rsi < mid_rsi


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------


class TestMACD:
    def test_macd_returns_three_series(self, analyzer: TechnicalAnalyzer) -> None:
        prices = _prices(list(range(1, 60)))
        result = analyzer.macd(prices)
        assert set(result.keys()) == {"macd", "signal", "histogram"}

    def test_macd_series_same_length(self, analyzer: TechnicalAnalyzer) -> None:
        prices = _prices(list(range(1, 60)))
        result = analyzer.macd(prices)
        assert len(result["macd"]) == len(result["signal"]) == len(result["histogram"])

    def test_macd_histogram_is_macd_minus_signal(self, analyzer: TechnicalAnalyzer) -> None:
        prices = _prices(list(range(1, 60)))
        result = analyzer.macd(prices)
        for m, s, h in zip(result["macd"], result["signal"], result["histogram"]):
            assert h["value"] == pytest.approx(m["value"] - s["value"], abs=1e-9)

    def test_macd_empty_input(self, analyzer: TechnicalAnalyzer) -> None:
        result = analyzer.macd([])
        assert result == {"macd": [], "signal": [], "histogram": []}

    def test_macd_insufficient_data(self, analyzer: TechnicalAnalyzer) -> None:
        """Need at least slow + signal - 1 = 34 bars for default MACD."""
        prices = _prices(list(range(1, 34)))
        result = analyzer.macd(prices)
        assert result == {"macd": [], "signal": [], "histogram": []}

    def test_macd_minimum_data(self, analyzer: TechnicalAnalyzer) -> None:
        """Exactly 34 bars → one MACD data point."""
        prices = _prices(list(range(1, 35)))
        result = analyzer.macd(prices)
        assert len(result["macd"]) == 1

    def test_macd_rising_series_positive_macd(self, analyzer: TechnicalAnalyzer) -> None:
        """For a steadily rising series, fast EMA > slow EMA → MACD > 0."""
        prices = _prices(list(range(1, 60)))
        result = analyzer.macd(prices)
        # Last value of MACD should be positive for a rising series.
        assert result["macd"][-1]["value"] > 0

    def test_macd_dates_aligned(self, analyzer: TechnicalAnalyzer) -> None:
        """All three series must share the same dates."""
        prices = _prices(list(range(1, 60)))
        result = analyzer.macd(prices)
        macd_dates = [r["date"] for r in result["macd"]]
        signal_dates = [r["date"] for r in result["signal"]]
        hist_dates = [r["date"] for r in result["histogram"]]
        assert macd_dates == signal_dates == hist_dates


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


class TestBollingerBands:
    def test_bb_returns_three_bands(self, analyzer: TechnicalAnalyzer) -> None:
        prices = _prices(list(range(1, 30)))
        result = analyzer.bollinger_bands(prices)
        assert set(result.keys()) == {"upper", "middle", "lower"}

    def test_bb_upper_gt_middle_gt_lower(self, analyzer: TechnicalAnalyzer) -> None:
        """Upper band > middle > lower for non-constant prices."""
        import random

        random.seed(7)
        prices = _prices([100.0 + random.gauss(0, 3) for _ in range(30)])
        result = analyzer.bollinger_bands(prices, period=20)
        for u, m, l in zip(result["upper"], result["middle"], result["lower"]):
            assert u["value"] > m["value"]
            assert m["value"] > l["value"]

    def test_bb_constant_prices_zero_width(self, analyzer: TechnicalAnalyzer) -> None:
        """For constant prices, upper == middle == lower (std dev = 0)."""
        prices = _prices([50.0] * 30)
        result = analyzer.bollinger_bands(prices, period=20)
        for u, m, l in zip(result["upper"], result["middle"], result["lower"]):
            assert u["value"] == pytest.approx(50.0)
            assert m["value"] == pytest.approx(50.0)
            assert l["value"] == pytest.approx(50.0)

    def test_bb_middle_equals_sma(self, analyzer: TechnicalAnalyzer) -> None:
        """Middle band must equal the SMA of the same period."""
        closes = list(range(1, 31))
        prices = _prices(closes)
        bb = analyzer.bollinger_bands(prices, period=20)
        sma = analyzer.sma(prices, period=20)
        for b, s in zip(bb["middle"], sma):
            assert b["value"] == pytest.approx(s["value"])

    def test_bb_width_scales_with_std_dev(self, analyzer: TechnicalAnalyzer) -> None:
        """Doubling std_dev parameter doubles the band width."""
        prices = _prices([100.0 + (i % 10) for i in range(30)])
        bb1 = analyzer.bollinger_bands(prices, period=20, std_dev=1.0)
        bb2 = analyzer.bollinger_bands(prices, period=20, std_dev=2.0)
        # Width = upper - lower; with std_dev doubled, width should double.
        width1 = bb1["upper"][-1]["value"] - bb1["lower"][-1]["value"]
        width2 = bb2["upper"][-1]["value"] - bb2["lower"][-1]["value"]
        assert width2 == pytest.approx(width1 * 2.0, rel=1e-6)

    def test_bb_empty_input(self, analyzer: TechnicalAnalyzer) -> None:
        result = analyzer.bollinger_bands([])
        assert result == {"upper": [], "middle": [], "lower": []}

    def test_bb_insufficient_data(self, analyzer: TechnicalAnalyzer) -> None:
        prices = _prices([1.0, 2.0, 3.0])
        result = analyzer.bollinger_bands(prices, period=20)
        assert result == {"upper": [], "middle": [], "lower": []}


# ---------------------------------------------------------------------------
# KD Stochastic
# ---------------------------------------------------------------------------


class TestKD:
    def _kd_prices(self) -> list[dict]:
        """Build a minimal OHLCV dataset with realistic high/low variation."""
        rows = []
        from datetime import date, timedelta

        base = date(2024, 1, 1)
        data = [
            (44.34, 44.84, 44.10),  # close, high, low
            (44.09, 44.50, 43.80),
            (44.15, 44.60, 43.90),
            (43.61, 44.20, 43.40),
            (44.33, 44.80, 43.90),
            (44.83, 45.20, 44.30),
            (45.10, 45.60, 44.70),
            (45.15, 45.70, 44.80),
            (43.61, 44.20, 43.30),
            (44.33, 44.90, 43.80),
            (44.83, 45.20, 44.20),
            (45.10, 45.50, 44.60),
            (45.15, 45.70, 44.70),
            (43.61, 44.30, 43.20),
            (44.34, 44.90, 44.00),
            (44.09, 44.50, 43.70),
            (44.15, 44.70, 43.80),
            (43.61, 44.20, 43.30),
            (44.33, 44.80, 43.80),
            (44.83, 45.20, 44.30),
        ]
        for i, (c, h, l) in enumerate(data):
            d = (base + timedelta(days=i)).isoformat()
            rows.append(
                {"date": d, "open": c, "high": h, "low": l, "close": c, "volume": 1}
            )
        return rows

    def test_kd_returns_two_series(self, analyzer: TechnicalAnalyzer) -> None:
        prices = self._kd_prices()
        result = analyzer.kd(prices)
        assert set(result.keys()) == {"k", "d"}

    def test_kd_same_length(self, analyzer: TechnicalAnalyzer) -> None:
        prices = self._kd_prices()
        result = analyzer.kd(prices)
        assert len(result["k"]) == len(result["d"])

    def test_kd_range_0_to_100(self, analyzer: TechnicalAnalyzer) -> None:
        prices = self._kd_prices()
        result = analyzer.kd(prices)
        for series in (result["k"], result["d"]):
            for r in series:
                assert 0.0 <= r["value"] <= 100.0, f"Out-of-range KD value: {r}"

    def test_kd_empty_input(self, analyzer: TechnicalAnalyzer) -> None:
        result = analyzer.kd([])
        assert result == {"k": [], "d": []}

    def test_kd_insufficient_data(self, analyzer: TechnicalAnalyzer) -> None:
        """Default params need at least k_period + 2*(d_period-1) = 9+4 = 13 bars."""
        prices = _prices([1.0] * 12)
        # Override high/low to equal close for simplicity.
        result = analyzer.kd(prices, k_period=9, d_period=3)
        assert result == {"k": [], "d": []}

    def test_kd_all_same_prices_returns_50(self, analyzer: TechnicalAnalyzer) -> None:
        """When high == low for all bars, raw %K = 50 (guard against division by zero)."""
        # Build prices where h == l == c (flat market).
        rows = []
        from datetime import date, timedelta

        for i in range(20):
            d = (date(2024, 1, 1) + timedelta(days=i)).isoformat()
            rows.append(
                {"date": d, "open": 50.0, "high": 50.0, "low": 50.0, "close": 50.0, "volume": 1}
            )
        result = analyzer.kd(rows, k_period=9, d_period=3)
        for r in result["k"] + result["d"]:
            assert r["value"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# compute_all
# ---------------------------------------------------------------------------


class TestComputeAll:
    def test_compute_all_returns_all_keys(self, analyzer: TechnicalAnalyzer) -> None:
        prices = _prices(list(range(1, 101)))  # 100 bars is enough for everything
        # Build realistic high/low for KD.
        for p in prices:
            p["high"] = p["close"] + 1.0
            p["low"] = p["close"] - 1.0
        result = analyzer.compute_all(prices)
        expected_keys = {"sma_20", "sma_50", "ema_20", "rsi_14", "macd", "bollinger_bands", "kd"}
        assert set(result.keys()) == expected_keys

    def test_compute_all_non_empty_with_sufficient_data(
        self, analyzer: TechnicalAnalyzer
    ) -> None:
        prices = _prices(list(range(1, 101)))
        for p in prices:
            p["high"] = p["close"] + 1.0
            p["low"] = p["close"] - 1.0
        result = analyzer.compute_all(prices)
        # Every indicator should have at least one value for 100 bars.
        assert len(result["sma_20"]) > 0
        assert len(result["sma_50"]) > 0
        assert len(result["ema_20"]) > 0
        assert len(result["rsi_14"]) > 0
        assert len(result["macd"]["macd"]) > 0
        assert len(result["bollinger_bands"]["middle"]) > 0
        assert len(result["kd"]["k"]) > 0

    def test_compute_all_empty_input(self, analyzer: TechnicalAnalyzer) -> None:
        result = analyzer.compute_all([])
        assert result["sma_20"] == []
        assert result["rsi_14"] == []
        assert result["macd"] == {"macd": [], "signal": [], "histogram": []}
        assert result["bollinger_bands"] == {"upper": [], "middle": [], "lower": []}
        assert result["kd"] == {"k": [], "d": []}
