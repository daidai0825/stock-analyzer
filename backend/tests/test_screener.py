"""Unit tests for StockScreener.

All external I/O (database, StockDataFetcher) is mocked.  Tests focus on
condition evaluation logic and the AND-combination of multiple conditions.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.screener import StockScreener
from app.services.technical_analysis import TechnicalAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prices(closes: list[float]) -> list[dict]:
    """Build a minimal OHLCV list suitable for indicator computation."""
    from datetime import date, timedelta

    base = date(2024, 1, 1)
    records = []
    for i, c in enumerate(closes):
        d = (base + timedelta(days=i)).isoformat()
        records.append(
            {
                "date": d,
                "open": c,
                "high": c + 1.0,
                "low": c - 1.0,
                "close": c,
                "volume": 1_000_000,
                "adj_close": c,
            }
        )
    return records


def _make_screener() -> StockScreener:
    analyzer = TechnicalAnalyzer()
    fetcher = MagicMock()
    return StockScreener(analyzer=analyzer, fetcher=fetcher)


def _make_series(value: float, n: int = 3) -> list[dict]:
    """Return a simple date-value series where the last value is *value*."""
    from datetime import date, timedelta

    return [
        {
            "date": (date(2024, 1, 1) + timedelta(days=i)).isoformat(),
            "value": value - (n - 1 - i) * 0.5,  # slight variation, last = value
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def screener() -> StockScreener:
    return _make_screener()


@pytest.fixture
def flat_prices() -> list[dict]:
    """100 bars of flat prices (close = 100) for screener tests."""
    return _prices([100.0] * 100)


@pytest.fixture
def rising_prices() -> list[dict]:
    """100 bars of steadily rising prices."""
    return _prices([50.0 + i for i in range(100)])


# ---------------------------------------------------------------------------
# _evaluate_condition — numeric operators
# ---------------------------------------------------------------------------


class TestEvaluateConditionNumeric:
    def test_gt_true(self, screener: StockScreener) -> None:
        prices = _prices([150.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "price", "operator": "gt", "value": 100.0}
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_gt_false(self, screener: StockScreener) -> None:
        prices = _prices([80.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "price", "operator": "gt", "value": 100.0}
        assert screener._evaluate_condition(cond, prices, indicators) is False

    def test_gte_equal(self, screener: StockScreener) -> None:
        prices = _prices([100.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "price", "operator": "gte", "value": 100.0}
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_lt_true(self, screener: StockScreener) -> None:
        prices = _prices([25.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "price", "operator": "lt", "value": 30.0}
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_lte_equal(self, screener: StockScreener) -> None:
        prices = _prices([30.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "price", "operator": "lte", "value": 30.0}
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_eq_true(self, screener: StockScreener) -> None:
        prices = _prices([42.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "price", "operator": "eq", "value": 42.0}
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_volume_gt(self, screener: StockScreener) -> None:
        prices = _prices([100.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "volume", "operator": "gt", "value": 500_000}
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_volume_lt_fails(self, screener: StockScreener) -> None:
        prices = _prices([100.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "volume", "operator": "lt", "value": 500_000}
        assert screener._evaluate_condition(cond, prices, indicators) is False

    def test_rsi_lt_30_oversold(self, screener: StockScreener) -> None:
        """Monotonically falling prices → RSI < 30."""
        prices = _prices([100.0 - i for i in range(50)])
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "rsi", "operator": "lt", "value": 30.0}
        # RSI of a strongly falling series should be below 30.
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_sma_20_gt_zero(self, screener: StockScreener) -> None:
        prices = _prices([50.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "sma_20", "operator": "gt", "value": 0.0}
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_unknown_operator_returns_false(self, screener: StockScreener) -> None:
        prices = _prices([100.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "price", "operator": "between", "value": 50.0}
        assert screener._evaluate_condition(cond, prices, indicators) is False

    def test_missing_indicator_returns_false(self, screener: StockScreener) -> None:
        prices = _prices([100.0] * 10)  # too few bars for any indicator
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "rsi", "operator": "lt", "value": 30.0}
        # RSI series is empty with only 10 bars → should return False.
        assert screener._evaluate_condition(cond, prices, indicators) is False


# ---------------------------------------------------------------------------
# _evaluate_condition — cross operators
# ---------------------------------------------------------------------------


class TestEvaluateConditionCross:
    def test_sma_cross_above_detected(self, screener: StockScreener) -> None:
        """Manually craft indicators where sma_20 just crossed above sma_50."""
        # Previous bar: sma_20 = 99, sma_50 = 100  (below)
        # Current bar:  sma_20 = 101, sma_50 = 100  (above)
        indicators = {
            "sma_20": [
                {"date": "2024-01-09", "value": 99.0},
                {"date": "2024-01-10", "value": 101.0},
            ],
            "sma_50": [
                {"date": "2024-01-09", "value": 100.0},
                {"date": "2024-01-10", "value": 100.0},
            ],
        }
        cond = {"indicator": "sma_20", "operator": "above", "value": "sma_50"}
        assert screener._evaluate_condition(cond, [], indicators) is True

    def test_sma_cross_above_not_detected_when_already_above(
        self, screener: StockScreener
    ) -> None:
        """No new cross when sma_20 was already above sma_50 on the previous bar."""
        indicators = {
            "sma_20": [
                {"date": "2024-01-09", "value": 102.0},
                {"date": "2024-01-10", "value": 103.0},
            ],
            "sma_50": [
                {"date": "2024-01-09", "value": 100.0},
                {"date": "2024-01-10", "value": 100.0},
            ],
        }
        cond = {"indicator": "sma_20", "operator": "above", "value": "sma_50"}
        assert screener._evaluate_condition(cond, [], indicators) is False

    def test_sma_cross_below_detected(self, screener: StockScreener) -> None:
        indicators = {
            "sma_20": [
                {"date": "2024-01-09", "value": 101.0},
                {"date": "2024-01-10", "value": 99.0},
            ],
            "sma_50": [
                {"date": "2024-01-09", "value": 100.0},
                {"date": "2024-01-10", "value": 100.0},
            ],
        }
        cond = {"indicator": "sma_20", "operator": "below", "value": "sma_50"}
        assert screener._evaluate_condition(cond, [], indicators) is True

    def test_cross_insufficient_history_returns_false(
        self, screener: StockScreener
    ) -> None:
        """Cross detection needs at least 2 values per series."""
        indicators = {
            "sma_20": [{"date": "2024-01-10", "value": 101.0}],
            "sma_50": [{"date": "2024-01-10", "value": 100.0}],
        }
        cond = {"indicator": "sma_20", "operator": "above", "value": "sma_50"}
        assert screener._evaluate_condition(cond, [], indicators) is False


# ---------------------------------------------------------------------------
# Multi-condition AND logic
# ---------------------------------------------------------------------------


class TestMultiConditionAnd:
    def test_all_conditions_must_pass(self, screener: StockScreener) -> None:
        """AND logic: all conditions must be True."""
        prices = _prices([25.0] * 30)
        indicators = screener._compute_indicators(prices)

        # price < 30 → True; price > 100 → False
        conditions = [
            {"indicator": "price", "operator": "lt", "value": 30.0},
            {"indicator": "price", "operator": "gt", "value": 100.0},
        ]
        results = [
            screener._evaluate_condition(c, prices, indicators) for c in conditions
        ]
        assert all(results) is False  # second condition fails

    def test_single_passing_condition(self, screener: StockScreener) -> None:
        prices = _prices([200.0] * 30)
        indicators = screener._compute_indicators(prices)
        cond = {"indicator": "price", "operator": "gt", "value": 150.0}
        assert screener._evaluate_condition(cond, prices, indicators) is True

    def test_rsi_and_price_both_pass(self, screener: StockScreener) -> None:
        """RSI < 30 (falling prices) AND price < 60."""
        prices = _prices([60.0 - i for i in range(50)])
        indicators = screener._compute_indicators(prices)
        conditions = [
            {"indicator": "rsi", "operator": "lt", "value": 30.0},
            {"indicator": "price", "operator": "lt", "value": 60.0},
        ]
        # Both should pass for monotonically falling prices starting at 60.
        assert all(
            screener._evaluate_condition(c, prices, indicators) for c in conditions
        )


# ---------------------------------------------------------------------------
# screen() integration (DB and fetcher mocked)
# ---------------------------------------------------------------------------


class TestScreenIntegration:
    async def test_screen_no_db_returns_empty(self, screener: StockScreener) -> None:
        result = await screener.screen(
            [{"indicator": "price", "operator": "gt", "value": 0}],
            market="US",
            db=None,
        )
        assert result == []

    async def test_screen_empty_conditions_returns_empty(
        self, screener: StockScreener
    ) -> None:
        mock_db = AsyncMock()
        result = await screener.screen([], market="US", db=mock_db)
        assert result == []

    async def test_screen_returns_matching_symbol(self) -> None:
        """screen() should return a symbol whose price passes the condition."""
        analyzer = TechnicalAnalyzer()
        fetcher = MagicMock()
        # Fetcher returns 30 bars of price=200 for any symbol.
        fetcher.fetch_history = AsyncMock(return_value=_prices([200.0] * 30))

        screener = StockScreener(analyzer=analyzer, fetcher=fetcher)

        # Mock DB: return one symbol.
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        conditions = [{"indicator": "price", "operator": "gt", "value": 100.0}]
        results = await screener.screen(conditions, market="US", db=mock_db)

        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"

    async def test_screen_filters_non_matching_symbol(self) -> None:
        """Symbols that fail conditions are excluded from results."""
        analyzer = TechnicalAnalyzer()
        fetcher = MagicMock()
        # Price = 50, condition asks for > 100 → should not match.
        fetcher.fetch_history = AsyncMock(return_value=_prices([50.0] * 30))

        screener = StockScreener(analyzer=analyzer, fetcher=fetcher)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        conditions = [{"indicator": "price", "operator": "gt", "value": 100.0}]
        results = await screener.screen(conditions, market="US", db=mock_db)
        assert results == []

    async def test_screen_respects_limit(self) -> None:
        """screen() must not return more than *limit* results."""
        analyzer = TechnicalAnalyzer()
        fetcher = MagicMock()
        fetcher.fetch_history = AsyncMock(return_value=_prices([200.0] * 30))

        screener = StockScreener(analyzer=analyzer, fetcher=fetcher)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        # Return 10 symbols.
        mock_result.all.return_value = [(f"SYM{i}",) for i in range(10)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        conditions = [{"indicator": "price", "operator": "gt", "value": 0.0}]
        results = await screener.screen(conditions, market="US", limit=3, db=mock_db)
        assert len(results) <= 3

    async def test_get_universe_queries_db(self) -> None:
        """get_universe() passes the market filter to the DB query."""
        analyzer = TechnicalAnalyzer()
        fetcher = MagicMock()
        screener = StockScreener(analyzer=analyzer, fetcher=fetcher)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("MSFT",), ("GOOG",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        symbols = await screener.get_universe("US", mock_db)
        assert symbols == ["AAPL", "MSFT", "GOOG"]
        mock_db.execute.assert_awaited_once()

    async def test_screen_skips_symbol_with_empty_prices(self) -> None:
        """Symbols with empty price data are silently skipped."""
        analyzer = TechnicalAnalyzer()
        fetcher = MagicMock()
        fetcher.fetch_history = AsyncMock(return_value=[])  # empty

        screener = StockScreener(analyzer=analyzer, fetcher=fetcher)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("EMPTY",)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await screener.screen(
            [{"indicator": "price", "operator": "gt", "value": 0}],
            db=mock_db,
        )
        assert results == []
