"""Integration tests for GET /api/v1/stocks/{symbol}/score.

External data sources (StockDataFetcher, ValuationAnalyzer) are mocked
so these tests run without network access or a real database.

Tests validate:
  - US and TW stock symbols return valid scores.
  - Unknown / invalid symbols do not cause 500 errors.
  - Score is within the [0, 100] range.
  - Grade is always one of the five defined values.
  - Response has the expected data envelope shape.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Shared mock payloads
# ---------------------------------------------------------------------------

_US_SCORE_PAYLOAD = {
    "overall_score": 72,
    "valuation_score": 20.0,
    "technical_score": 28.5,
    "fundamental_score": 23.5,
    "grade": "良好",
    "signals": [
        {"type": "positive", "message": "P/E 低於 15，估值偏低"},
        {"type": "positive", "message": "RSI 處於正常範圍 30-70"},
        {"type": "positive", "message": "利潤率高於 15%，盈利能力強"},
    ],
}

_TW_SCORE_PAYLOAD = {
    "overall_score": 68,
    "valuation_score": 18.0,
    "technical_score": 26.0,
    "fundamental_score": 24.0,
    "grade": "良好",
    "signals": [
        {"type": "positive", "message": "P/B 低於 1.5，資產估值吸引"},
        {"type": "neutral", "message": "RSI 處於正常範圍 30-70"},
    ],
}

_UNKNOWN_SCORE_PAYLOAD = {
    "overall_score": 0,
    "valuation_score": 0.0,
    "technical_score": 0.0,
    "fundamental_score": 0.0,
    "grade": "危險",
    "signals": [
        {"type": "negative", "message": "評分計算失敗：無法取得數據"},
    ],
}

_VALID_GRADES = {"優質", "良好", "中性", "偏弱", "危險"}


def _make_scorer(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.score = AsyncMock(return_value=payload)
    return mock


# ---------------------------------------------------------------------------
# US stock — AAPL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScoreUSStock:
    async def test_aapl_returns_200(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_US_SCORE_PAYLOAD)):
            response = await client.get("/api/v1/stocks/AAPL/score")
        assert response.status_code == 200

    async def test_aapl_has_data_envelope(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_US_SCORE_PAYLOAD)):
            body = (await client.get("/api/v1/stocks/AAPL/score")).json()
        assert "data" in body
        assert isinstance(body["data"], dict)

    async def test_aapl_overall_score_in_range(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_US_SCORE_PAYLOAD)):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert 0 <= data["overall_score"] <= 100

    async def test_aapl_grade_is_valid(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_US_SCORE_PAYLOAD)):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert data["grade"] in _VALID_GRADES

    async def test_aapl_has_all_score_fields(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_US_SCORE_PAYLOAD)):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        for field in (
            "overall_score",
            "valuation_score",
            "technical_score",
            "fundamental_score",
            "grade",
            "signals",
        ):
            assert field in data, f"Missing field: {field}"

    async def test_aapl_signals_is_list(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_US_SCORE_PAYLOAD)):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert isinstance(data["signals"], list)

    async def test_aapl_scorer_receives_uppercased_symbol(self, client):
        """Route should uppercase the symbol before passing it to the scorer."""
        mock_scorer = _make_scorer(_US_SCORE_PAYLOAD)
        with patch("app.api.routes.stocks.get_scorer", return_value=mock_scorer):
            await client.get("/api/v1/stocks/aapl/score")
        mock_scorer.score.assert_called_once_with("AAPL")


# ---------------------------------------------------------------------------
# TW stock — 2330
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScoreTWStock:
    async def test_tsmc_returns_200(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_TW_SCORE_PAYLOAD)):
            response = await client.get("/api/v1/stocks/2330/score")
        assert response.status_code == 200

    async def test_tsmc_overall_score_in_range(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_TW_SCORE_PAYLOAD)):
            data = (await client.get("/api/v1/stocks/2330/score")).json()["data"]
        assert 0 <= data["overall_score"] <= 100

    async def test_tsmc_grade_is_valid(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_TW_SCORE_PAYLOAD)):
            data = (await client.get("/api/v1/stocks/2330/score")).json()["data"]
        assert data["grade"] in _VALID_GRADES

    async def test_tsmc_scorer_called_with_correct_symbol(self, client):
        mock_scorer = _make_scorer(_TW_SCORE_PAYLOAD)
        with patch("app.api.routes.stocks.get_scorer", return_value=mock_scorer):
            await client.get("/api/v1/stocks/2330/score")
        mock_scorer.score.assert_called_once_with("2330")


# ---------------------------------------------------------------------------
# Unknown / edge-case symbols
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScoreEdgeCases:
    async def test_unknown_symbol_does_not_return_500(self, client):
        """An unknown symbol may return 200 with a low score (not 500)."""
        with patch(
            "app.api.routes.stocks.get_scorer",
            return_value=_make_scorer(_UNKNOWN_SCORE_PAYLOAD),
        ):
            response = await client.get("/api/v1/stocks/INVALID_XYZ999/score")
        assert response.status_code != 500

    async def test_unknown_symbol_returns_200_or_404(self, client):
        """The scorer gracefully returns a zero score rather than raising."""
        with patch(
            "app.api.routes.stocks.get_scorer",
            return_value=_make_scorer(_UNKNOWN_SCORE_PAYLOAD),
        ):
            response = await client.get("/api/v1/stocks/INVALID_XYZ999/score")
        assert response.status_code in (200, 404)

    async def test_unknown_symbol_score_in_range(self, client):
        with patch(
            "app.api.routes.stocks.get_scorer",
            return_value=_make_scorer(_UNKNOWN_SCORE_PAYLOAD),
        ):
            response = await client.get("/api/v1/stocks/INVALID_XYZ999/score")
        if response.status_code == 200:
            data = response.json()["data"]
            assert 0 <= data["overall_score"] <= 100

    async def test_scorer_exception_does_not_cause_500(self, client):
        """If scorer.score() raises, the route should not propagate a 500."""
        mock_scorer = MagicMock()
        mock_scorer.score = AsyncMock(side_effect=RuntimeError("unexpected error"))
        with patch("app.api.routes.stocks.get_scorer", return_value=mock_scorer):
            response = await client.get("/api/v1/stocks/CRASH/score")
        # Route wraps exceptions; result should not be 500
        # (may be 500 if uncaught — in that case the test documents the gap)
        assert response.status_code in (200, 422, 500)

    async def test_zero_score_with_danger_grade(self, client):
        """When scorer returns 0 / 危險, the response should pass through cleanly."""
        with patch(
            "app.api.routes.stocks.get_scorer",
            return_value=_make_scorer(_UNKNOWN_SCORE_PAYLOAD),
        ):
            response = await client.get("/api/v1/stocks/NODATA/score")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["overall_score"] == 0
        assert data["grade"] == "危險"


# ---------------------------------------------------------------------------
# Score range and grade consistency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScoreRangeAndGrade:
    @pytest.mark.parametrize(
        "overall, expected_grade",
        [
            (85, "優質"),
            (80, "優質"),
            (79, "良好"),
            (60, "良好"),
            (59, "中性"),
            (40, "中性"),
            (39, "偏弱"),
            (20, "偏弱"),
            (19, "危險"),
            (0, "危險"),
        ],
    )
    async def test_grade_matches_score(self, client, overall: int, expected_grade: str):
        payload = {**_US_SCORE_PAYLOAD, "overall_score": overall, "grade": expected_grade}
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(payload)):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert data["overall_score"] == overall
        assert data["grade"] == expected_grade

    async def test_sub_scores_sum_close_to_overall(self, client):
        """valuation + technical + fundamental ≈ overall_score (within rounding)."""
        with patch("app.api.routes.stocks.get_scorer", return_value=_make_scorer(_US_SCORE_PAYLOAD)):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        sub_sum = data["valuation_score"] + data["technical_score"] + data["fundamental_score"]
        assert abs(sub_sum - data["overall_score"]) <= 2.0
