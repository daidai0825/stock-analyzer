"""Contract tests for GET /api/v1/stocks/{symbol}/score.

Shape tests verify the response envelope structure and field types.
Tests that require a live scorer are mocked so they pass without
network access.

All tests follow the ASGITransport + AsyncClient pattern used by the
other contract tests in this directory.
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


# Minimal valid score payload that the route can build a StockScoreResponse from.
_MOCK_SCORE = {
    "overall_score": 75,
    "valuation_score": 22.5,
    "technical_score": 28.0,
    "fundamental_score": 24.5,
    "grade": "良好",
    "signals": [
        {"type": "positive", "message": "P/E 低，估值吸引"},
        {"type": "neutral", "message": "RSI 處於正常範圍"},
    ],
}


def _mock_scorer(return_value: dict = _MOCK_SCORE):
    """Return a mock StockScorer whose score() coroutine yields *return_value*."""
    mock = MagicMock()
    mock.score = AsyncMock(return_value=return_value)
    return mock


# ---------------------------------------------------------------------------
# GET /api/v1/stocks/{symbol}/score — basic contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScoreEndpointContract:
    async def test_returns_200(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            response = await client.get("/api/v1/stocks/AAPL/score")
        assert response.status_code == 200

    async def test_response_has_data_key(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            body = (await client.get("/api/v1/stocks/AAPL/score")).json()
        assert "data" in body

    async def test_data_is_object(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            body = (await client.get("/api/v1/stocks/AAPL/score")).json()
        assert isinstance(body["data"], dict)

    async def test_data_has_overall_score(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert "overall_score" in data

    async def test_overall_score_is_int(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert isinstance(data["overall_score"], int)

    async def test_data_has_valuation_score(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert "valuation_score" in data

    async def test_valuation_score_is_numeric(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert isinstance(data["valuation_score"], (int, float))

    async def test_data_has_technical_score(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert "technical_score" in data

    async def test_technical_score_is_numeric(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert isinstance(data["technical_score"], (int, float))

    async def test_data_has_fundamental_score(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert "fundamental_score" in data

    async def test_fundamental_score_is_numeric(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert isinstance(data["fundamental_score"], (int, float))

    async def test_data_has_grade(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert "grade" in data

    async def test_grade_is_string(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert isinstance(data["grade"], str)

    async def test_data_has_signals(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert "signals" in data

    async def test_signals_is_list(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert isinstance(data["signals"], list)


# ---------------------------------------------------------------------------
# Score value constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScoreValueConstraints:
    async def test_overall_score_within_0_to_100(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert 0 <= data["overall_score"] <= 100

    async def test_grade_is_one_of_valid_values(self, client):
        valid_grades = {"優質", "良好", "中性", "偏弱", "危險"}
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        assert data["grade"] in valid_grades

    async def test_signal_items_have_type_and_message(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        for sig in data["signals"]:
            assert "type" in sig, "signal missing 'type'"
            assert "message" in sig, "signal missing 'message'"

    async def test_signal_type_is_valid(self, client):
        valid_types = {"positive", "negative", "neutral"}
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            data = (await client.get("/api/v1/stocks/AAPL/score")).json()["data"]
        for sig in data["signals"]:
            assert sig["type"] in valid_types, f"Invalid signal type: {sig['type']}"


# ---------------------------------------------------------------------------
# Symbol variants
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScoreSymbolVariants:
    async def test_us_symbol_aapl_accepted(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            response = await client.get("/api/v1/stocks/AAPL/score")
        assert response.status_code == 200

    async def test_tw_symbol_2330_accepted(self, client):
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            response = await client.get("/api/v1/stocks/2330/score")
        assert response.status_code == 200

    async def test_lowercase_symbol_normalised(self, client):
        """Symbol case should be normalised by the route (aapl → AAPL)."""
        with patch("app.api.routes.stocks.get_scorer", return_value=_mock_scorer()):
            response = await client.get("/api/v1/stocks/aapl/score")
        assert response.status_code == 200

    async def test_empty_signals_is_valid(self, client):
        """Scorer may return an empty signals list — response should still be 200."""
        score_no_signals = {**_MOCK_SCORE, "signals": []}
        with patch(
            "app.api.routes.stocks.get_scorer", return_value=_mock_scorer(score_no_signals)
        ):
            response = await client.get("/api/v1/stocks/AAPL/score")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["signals"] == []


# ---------------------------------------------------------------------------
# xfail tests — require live StockScorer (i.e. no mock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScoreLiveXfail:
    @pytest.mark.xfail(reason="Requires live data sources (yfinance / FinMind)")
    async def test_live_aapl_score_not_none(self, client):
        response = await client.get("/api/v1/stocks/AAPL/score")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["overall_score"] is not None

    @pytest.mark.xfail(reason="Requires live data sources (yfinance / FinMind)")
    async def test_live_2330_score_not_none(self, client):
        response = await client.get("/api/v1/stocks/2330/score")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["overall_score"] is not None
