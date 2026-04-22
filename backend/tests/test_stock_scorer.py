"""Tests for StockScorer quality scoring service.

Uses mock data to verify scoring logic without hitting external APIs.
All async tests use pytest-asyncio.
"""

import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.stock_scorer import (
    ScoreResult,
    StockScorer,
    _grade,
    _latest_value,
    _score_fundamental,
    _score_technical,
    _score_valuation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FULL_VALUATION = {
    "pe_ratio": 12.0,
    "pb_ratio": 1.2,
    "dividend_yield": 0.04,  # 4%
    "market_cap": 1e12,
    "eps": 5.0,
    "revenue": 1e9,
    "profit_margin": 0.20,  # 20%
    "ps_ratio": None,
}

_POOR_VALUATION = {
    "pe_ratio": 50.0,
    "pb_ratio": 5.0,
    "dividend_yield": 0.005,  # 0.5%
    "market_cap": 1e9,
    "eps": -1.0,
    "revenue": 0.0,
    "profit_margin": -0.05,
    "ps_ratio": None,
}

_EMPTY_VALUATION = {
    "pe_ratio": None,
    "pb_ratio": None,
    "dividend_yield": None,
    "market_cap": None,
    "eps": None,
    "revenue": None,
    "profit_margin": None,
    "ps_ratio": None,
}


def _make_prices(n: int = 250, base: float = 100.0) -> list[dict]:
    """Generate synthetic ascending OHLCV data."""
    prices = []
    from datetime import date, timedelta

    start = date(2023, 1, 1)
    for i in range(n):
        c = base + i * 0.1
        prices.append(
            {
                "date": (start + timedelta(days=i)).isoformat(),
                "open": c - 0.2,
                "high": c + 0.5,
                "low": c - 0.5,
                "close": c,
                "volume": 1_000_000,
                "adj_close": c,
            }
        )
    return prices


# ---------------------------------------------------------------------------
# Unit tests: _grade
# ---------------------------------------------------------------------------


class TestGrade:
    def test_excellent(self):
        assert _grade(80) == "優質"
        assert _grade(100) == "優質"

    def test_good(self):
        assert _grade(79) == "良好"
        assert _grade(60) == "良好"

    def test_neutral(self):
        assert _grade(59) == "中性"
        assert _grade(40) == "中性"

    def test_weak(self):
        assert _grade(39) == "偏弱"
        assert _grade(20) == "偏弱"

    def test_danger(self):
        assert _grade(19) == "危險"
        assert _grade(0) == "危險"


# ---------------------------------------------------------------------------
# Unit tests: _latest_value
# ---------------------------------------------------------------------------


class TestLatestValue:
    def test_empty(self):
        assert _latest_value([]) is None

    def test_single(self):
        assert _latest_value([{"date": "2024-01-01", "value": 42.0}]) == 42.0

    def test_returns_last(self):
        series = [
            {"date": "2024-01-01", "value": 10.0},
            {"date": "2024-01-02", "value": 20.0},
        ]
        assert _latest_value(series) == 20.0


# ---------------------------------------------------------------------------
# Unit tests: _score_valuation
# ---------------------------------------------------------------------------


class TestScoreValuation:
    def test_full_score_on_good_metrics(self):
        score, signals = _score_valuation(_FULL_VALUATION)
        # pe<15 → 10, pb<1.5 → 10, dy>3% → 10 = 30
        assert score == pytest.approx(30.0, abs=0.1)
        types = {s["type"] for s in signals}
        assert "positive" in types
        assert "negative" not in types

    def test_low_score_on_poor_metrics(self):
        score, signals = _score_valuation(_POOR_VALUATION)
        assert score < 10.0
        types = {s["type"] for s in signals}
        assert "negative" in types

    def test_none_metrics_give_neutral_signals(self):
        score, signals = _score_valuation(_EMPTY_VALUATION)
        assert score == pytest.approx(0.0)
        for s in signals:
            assert s["type"] == "neutral"

    def test_pe_boundary_15(self):
        val = {**_EMPTY_VALUATION, "pe_ratio": 15.0}
        score, _ = _score_valuation(val)
        assert score == pytest.approx(10.0, abs=0.1)

    def test_pe_boundary_25(self):
        val = {**_EMPTY_VALUATION, "pe_ratio": 25.0}
        score, _ = _score_valuation(val)
        # At pe=25: pts = 10 - (25-15)*0.5 = 5, clamped to >=2
        assert 4.5 <= score <= 5.5

    def test_dividend_yield_decimal_normalisation(self):
        # 0.04 raw → 4% → max score
        val = {**_EMPTY_VALUATION, "dividend_yield": 0.04}
        score, signals = _score_valuation(val)
        assert score == pytest.approx(10.0)
        assert any("4.00%" in s["message"] for s in signals)

    def test_negative_pe_penalised(self):
        val = {**_EMPTY_VALUATION, "pe_ratio": -5.0}
        score, signals = _score_valuation(val)
        assert score == 0.0
        assert any("虧損" in s["message"] for s in signals)


# ---------------------------------------------------------------------------
# Unit tests: _score_technical
# ---------------------------------------------------------------------------


class TestScoreTechnical:
    def _make_indicators(
        self,
        rsi: float | None = 50.0,
        sma50_val: float | None = 90.0,
        macd_val: float | None = 0.5,
        signal_val: float | None = 0.3,
        bb_upper: float | None = 115.0,
        bb_middle: float | None = 105.0,
        bb_lower: float | None = 95.0,
    ) -> dict:
        def s(v):
            return [{"date": "2024-01-01", "value": v}] if v is not None else []

        return {
            "rsi_14": s(rsi),
            "sma_50": s(sma50_val),
            "sma_200": [],
            "macd": {
                "macd": s(macd_val),
                "signal": s(signal_val),
                "histogram": [],
            },
            "bollinger_bands": {
                "upper": s(bb_upper),
                "middle": s(bb_middle),
                "lower": s(bb_lower),
            },
        }

    def test_full_score_on_ideal_conditions(self):
        prices = _make_prices()
        # close at index -1 is ~100 + 249*0.1 = 124.9; sma50 below that
        indicators = self._make_indicators(
            rsi=50.0,
            sma50_val=100.0,
            macd_val=0.5,
            signal_val=0.3,
            bb_upper=130.0,
            bb_middle=125.0,
            bb_lower=120.0,
        )
        score, _ = _score_technical(prices, indicators)
        # RSI=50 → 10, price>sma → 10, macd>signal → 10, position ~0.5 → ~10
        assert score >= 30.0

    def test_overbought_rsi_penalised(self):
        prices = _make_prices()
        indicators = self._make_indicators(rsi=85.0)
        score, signals = _score_technical(prices, indicators)
        assert any("超買" in s["message"] for s in signals)

    def test_oversold_rsi_penalised(self):
        prices = _make_prices()
        indicators = self._make_indicators(rsi=20.0)
        score, signals = _score_technical(prices, indicators)
        assert any("超賣" in s["message"] for s in signals)

    def test_price_below_sma_penalised(self):
        prices = _make_prices(base=80.0)
        # price ~99.9; sma50=150 > price → penalise
        indicators = self._make_indicators(sma50_val=150.0)
        score, signals = _score_technical(prices, indicators)
        assert any("下降趨勢" in s["message"] for s in signals)

    def test_bearish_macd_penalised(self):
        prices = _make_prices()
        indicators = self._make_indicators(macd_val=-0.5, signal_val=0.1)
        score, signals = _score_technical(prices, indicators)
        assert any("空頭" in s["message"] for s in signals)

    def test_price_near_bb_upper_penalised(self):
        # Price at 124 ≈ upper at 125 → position > 0.9
        prices = _make_prices()
        last_close = prices[-1]["close"]  # ~124.9
        indicators = self._make_indicators(
            bb_upper=last_close + 1.0,
            bb_middle=last_close - 10.0,
            bb_lower=last_close - 20.0,
        )
        score, signals = _score_technical(prices, indicators)
        assert any("上軌" in s["message"] for s in signals)

    def test_empty_prices_returns_zero(self):
        score, signals = _score_technical([], {})
        assert score == 0.0
        assert any("無價格資料" in s["message"] for s in signals)


# ---------------------------------------------------------------------------
# Unit tests: _score_fundamental
# ---------------------------------------------------------------------------


class TestScoreFundamental:
    def test_full_score_on_strong_fundamentals(self):
        score, signals = _score_fundamental(_FULL_VALUATION)
        # profit_margin=20% → 10, eps=5 > 0 → ~10, revenue>0 → 10 = ~30
        assert score >= 28.0
        assert any("正" in s["message"] or "強" in s["message"] for s in signals)

    def test_zero_on_losses(self):
        score, signals = _score_fundamental(_POOR_VALUATION)
        # profit_margin<0 → 0, eps<0 → 0, revenue=0 → 0
        assert score == pytest.approx(0.0)

    def test_none_metrics(self):
        score, signals = _score_fundamental(_EMPTY_VALUATION)
        assert score == pytest.approx(0.0)
        for s in signals:
            assert s["type"] == "neutral"

    def test_profit_margin_decimal_normalisation(self):
        val = {**_EMPTY_VALUATION, "profit_margin": 0.20}  # 20%
        score, signals = _score_fundamental(val)
        assert score == pytest.approx(10.0)
        assert any("20.0%" in s["message"] for s in signals)

    def test_eps_logarithmic_scaling(self):
        val_high = {**_EMPTY_VALUATION, "eps": 100.0}
        val_low = {**_EMPTY_VALUATION, "eps": 0.01}
        score_high, _ = _score_fundamental(val_high)
        score_low, _ = _score_fundamental(val_low)
        assert score_high > score_low

    def test_negative_eps(self):
        val = {**_EMPTY_VALUATION, "eps": -2.0}
        score, signals = _score_fundamental(val)
        assert score == 0.0
        assert any("虧損" in s["message"] for s in signals)


# ---------------------------------------------------------------------------
# Integration tests: StockScorer.score (mocked external calls)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStockScorer:
    """Test StockScorer.score with mocked fetcher and valuation."""

    def _make_scorer_with_mocks(
        self,
        prices: list[dict],
        valuation: dict,
    ) -> StockScorer:
        scorer = StockScorer()
        scorer._fetcher.fetch_history = AsyncMock(return_value=prices)
        scorer._valuation.get_valuation = AsyncMock(return_value=valuation)
        return scorer

    async def test_excellent_stock_returns_high_score(self):
        prices = _make_prices(250)
        scorer = self._make_scorer_with_mocks(prices, _FULL_VALUATION)
        result = await scorer.score("AAPL")

        assert isinstance(result, ScoreResult)
        assert result.overall_score >= 60
        assert result.grade in ("優質", "良好")
        assert result.valuation_score == pytest.approx(30.0, abs=0.1)
        assert 0.0 <= result.technical_score <= 40.0
        assert result.fundamental_score > 20.0

    async def test_poor_stock_returns_low_score(self):
        prices = _make_prices(250, base=200.0)
        # Simulate price below SMA — generate descending prices
        desc_prices = []
        from datetime import date, timedelta

        start = date(2023, 1, 1)
        for i in range(250):
            c = 200.0 - i * 0.3
            desc_prices.append(
                {
                    "date": (start + timedelta(days=i)).isoformat(),
                    "open": c,
                    "high": c + 0.2,
                    "low": c - 0.2,
                    "close": c,
                    "volume": 500_000,
                    "adj_close": c,
                }
            )

        scorer = self._make_scorer_with_mocks(desc_prices, _POOR_VALUATION)
        result = await scorer.score("XBAD")

        assert result.overall_score < 50
        assert result.grade in ("中性", "偏弱", "危險")

    async def test_returns_score_result_dataclass(self):
        prices = _make_prices(250)
        scorer = self._make_scorer_with_mocks(prices, _FULL_VALUATION)
        result = await scorer.score("TEST")

        assert hasattr(result, "overall_score")
        assert hasattr(result, "valuation_score")
        assert hasattr(result, "technical_score")
        assert hasattr(result, "fundamental_score")
        assert hasattr(result, "grade")
        assert hasattr(result, "signals")
        assert isinstance(result.signals, list)

    async def test_signals_have_required_keys(self):
        prices = _make_prices(250)
        scorer = self._make_scorer_with_mocks(prices, _FULL_VALUATION)
        result = await scorer.score("AAPL")

        for sig in result.signals:
            assert "type" in sig
            assert "message" in sig
            assert sig["type"] in ("positive", "negative", "neutral")

    async def test_empty_prices_still_returns_result(self):
        scorer = self._make_scorer_with_mocks([], _FULL_VALUATION)
        result = await scorer.score("NOHIST")

        assert isinstance(result, ScoreResult)
        assert result.overall_score >= 0
        # Technical score should be 0 with no price data
        assert result.technical_score == pytest.approx(0.0)

    async def test_empty_valuation_still_returns_result(self):
        prices = _make_prices(250)
        scorer = self._make_scorer_with_mocks(prices, _EMPTY_VALUATION)
        result = await scorer.score("NOVAL")

        assert isinstance(result, ScoreResult)
        assert result.valuation_score == pytest.approx(0.0)
        assert result.fundamental_score == pytest.approx(0.0)

    async def test_score_bounded_0_to_100(self):
        prices = _make_prices(250)
        for val in (_FULL_VALUATION, _POOR_VALUATION, _EMPTY_VALUATION):
            scorer = self._make_scorer_with_mocks(prices, val)
            result = await scorer.score("BOUND")
            assert 0 <= result.overall_score <= 100

    async def test_fetcher_exception_returns_safe_result(self):
        scorer = StockScorer()
        scorer._fetcher.fetch_history = AsyncMock(side_effect=RuntimeError("network down"))
        scorer._valuation.get_valuation = AsyncMock(return_value=_FULL_VALUATION)
        result = await scorer.score("ERR")

        assert isinstance(result, ScoreResult)
        # Should fall back gracefully
        assert result.overall_score >= 0

    async def test_valuation_exception_returns_safe_result(self):
        prices = _make_prices(50)
        scorer = StockScorer()
        scorer._fetcher.fetch_history = AsyncMock(return_value=prices)
        scorer._valuation.get_valuation = AsyncMock(side_effect=RuntimeError("API error"))
        result = await scorer.score("ERR2")

        assert isinstance(result, ScoreResult)
        assert result.overall_score >= 0

    async def test_grade_consistent_with_overall_score(self):
        prices = _make_prices(250)
        scorer = self._make_scorer_with_mocks(prices, _FULL_VALUATION)
        result = await scorer.score("CHECK")

        expected_grade = (
            "優質"
            if result.overall_score >= 80
            else "良好"
            if result.overall_score >= 60
            else "中性"
            if result.overall_score >= 40
            else "偏弱"
            if result.overall_score >= 20
            else "危險"
        )
        assert result.grade == expected_grade

    async def test_tw_stock_symbol(self):
        """Scorer should work transparently for TW symbols."""
        prices = _make_prices(250)
        scorer = self._make_scorer_with_mocks(prices, _FULL_VALUATION)
        result = await scorer.score("2330")
        assert isinstance(result, ScoreResult)
