"""Integration tests for POST /api/v1/screener."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


VALID_REQUEST = {
    "conditions": [
        {"indicator": "rsi", "operator": "lt", "value": 30},
    ],
    "market": "US",
    "limit": 10,
}


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_screener_missing_conditions_returns_422(client):
    """A body without 'conditions' must fail with 422."""
    response = await client.post("/api/v1/screener", json={"market": "US"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_screener_invalid_operator_returns_422(client):
    """An unknown operator value must fail Pydantic validation."""
    response = await client.post(
        "/api/v1/screener",
        json={
            "conditions": [{"indicator": "rsi", "operator": "invalid_op", "value": 30}],
            "market": "US",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_screener_all_valid_operators_accepted(client):
    """Each valid operator must be accepted without 422."""
    valid_ops = ["gt", "gte", "lt", "lte", "eq", "above", "below"]
    with (
        patch("app.api.routes.screener.get_db"),
        patch("app.api.routes.screener.get_screener") as mock_get_screener,
    ):
        mock_screener = MagicMock()
        mock_screener.screen = AsyncMock(return_value=[])
        mock_get_screener.return_value = mock_screener

        for op in valid_ops:
            response = await client.post(
                "/api/v1/screener",
                json={
                    "conditions": [{"indicator": "rsi", "operator": op, "value": 30}],
                    "market": "US",
                },
            )
            assert response.status_code != 422, f"operator={op!r} caused 422"


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_screener_returns_200_with_envelope(client):
    """Screener returns 200 with 'data' list and 'meta' object."""
    with (
        patch("app.api.routes.screener.get_db"),
        patch("app.api.routes.screener.get_screener") as mock_get_screener,
    ):
        mock_screener = MagicMock()
        mock_screener.screen = AsyncMock(return_value=[])
        mock_get_screener.return_value = mock_screener

        response = await client.post("/api/v1/screener", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert isinstance(body["data"], list)
    for field in ("total", "page", "limit"):
        assert field in body["meta"]


@pytest.mark.asyncio
async def test_screener_returns_matching_symbols(client):
    """Screener results include symbol and indicators keys."""
    screener_results = [
        {"symbol": "AAPL", "indicators": {"rsi": 25.3, "sma_20": 180.5}},
        {"symbol": "MSFT", "indicators": {"rsi": 28.1, "sma_20": 415.0}},
    ]

    with (
        patch("app.api.routes.screener.get_db"),
        patch("app.api.routes.screener.get_screener") as mock_get_screener,
    ):
        mock_screener = MagicMock()
        mock_screener.screen = AsyncMock(return_value=screener_results)
        mock_get_screener.return_value = mock_screener

        response = await client.post("/api/v1/screener", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total"] == 2
    for item in body["data"]:
        assert "symbol" in item
        assert "indicators" in item


@pytest.mark.asyncio
async def test_screener_meta_total_matches_result_count(client):
    """meta.total must equal len(data)."""
    with (
        patch("app.api.routes.screener.get_db"),
        patch("app.api.routes.screener.get_screener") as mock_get_screener,
    ):
        mock_screener = MagicMock()
        mock_screener.screen = AsyncMock(
            return_value=[
                {"symbol": "TSLA", "indicators": {}},
            ]
        )
        mock_get_screener.return_value = mock_screener

        response = await client.post("/api/v1/screener", json=VALID_REQUEST)

    body = response.json()
    assert body["meta"]["total"] == len(body["data"])


@pytest.mark.asyncio
async def test_screener_default_market_is_us(client):
    """When market is omitted it defaults to US; screener is called with 'US'."""
    with (
        patch("app.api.routes.screener.get_db"),
        patch("app.api.routes.screener.get_screener") as mock_get_screener,
    ):
        mock_screener = MagicMock()
        mock_screener.screen = AsyncMock(return_value=[])
        mock_get_screener.return_value = mock_screener

        await client.post(
            "/api/v1/screener",
            json={"conditions": [{"indicator": "rsi", "operator": "lt", "value": 30}]},
        )

        call_kwargs = mock_screener.screen.call_args
        if call_kwargs is not None:
            assert call_kwargs.kwargs.get("market", "US") == "US"


@pytest.mark.asyncio
async def test_screener_tw_market_accepted(client):
    """market=TW must be forwarded to the screener without 422."""
    with (
        patch("app.api.routes.screener.get_db"),
        patch("app.api.routes.screener.get_screener") as mock_get_screener,
    ):
        mock_screener = MagicMock()
        mock_screener.screen = AsyncMock(return_value=[])
        mock_get_screener.return_value = mock_screener

        response = await client.post(
            "/api/v1/screener",
            json={
                "conditions": [{"indicator": "rsi", "operator": "lt", "value": 30}],
                "market": "TW",
                "limit": 5,
            },
        )

    assert response.status_code != 422
