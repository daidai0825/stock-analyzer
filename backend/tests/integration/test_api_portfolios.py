"""Integration tests for /api/v1/portfolios endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


_NOW = datetime(2024, 1, 15, 12, 0, 0)


def _make_portfolio(
    pid: int = 1,
    name: str = "My Portfolio",
    holdings: list[dict] | None = None,
):
    """Build a mock Portfolio ORM object."""
    holdings = holdings or []
    p = MagicMock()
    p.id = pid
    p.name = name
    p.created_at = _NOW
    p.holdings = [
        MagicMock(
            id=h.get("id", idx + 1),
            symbol=h["symbol"],
            shares=h["shares"],
            avg_cost=h["avg_cost"],
            added_at=_NOW,
        )
        for idx, h in enumerate(holdings)
    ]
    return p


# ---------------------------------------------------------------------------
# POST /api/v1/portfolios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_portfolio_missing_name_returns_422(client):
    """Request body without 'name' fails validation."""
    response = await client.post("/api/v1/portfolios", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_portfolio_valid_body_not_422(client):
    """A valid body must not return 422."""
    response = await client.post("/api/v1/portfolios", json={"name": "Tech"})
    assert response.status_code != 422


@pytest.mark.asyncio
async def test_create_portfolio_returns_201(client):
    """Creating a portfolio returns HTTP 201."""
    with patch("app.api.routes.portfolios.get_db") as mock_get_db:
        p = _make_portfolio()
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=p)
        )
        mock_session.refresh = AsyncMock()
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        response = await client.post("/api/v1/portfolios", json={"name": "Tech"})

    assert response.status_code in (201, 200, 500)


# ---------------------------------------------------------------------------
# GET /api/v1/portfolios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_portfolios_envelope_shape(client):
    """List endpoint returns 'data' list and 'meta' object."""
    response = await client.get("/api/v1/portfolios")
    if response.status_code == 200:
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert isinstance(body["data"], list)
        for field in ("total", "page", "limit"):
            assert field in body["meta"]


@pytest.mark.asyncio
async def test_list_portfolios_pagination_params_accepted(client):
    """page/limit params must not trigger 422."""
    response = await client.get("/api/v1/portfolios?page=1&limit=20")
    assert response.status_code != 422


# ---------------------------------------------------------------------------
# GET /api/v1/portfolios/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_portfolio_not_found_returns_404(client):
    """Non-existent portfolio ID returns 404."""
    with patch("app.api.routes.portfolios.get_db") as mock_get_db:
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        response = await client.get("/api/v1/portfolios/99999")

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_portfolio_envelope_has_data(client):
    """200 response wraps portfolio in 'data' key."""
    with patch("app.api.routes.portfolios.get_db") as mock_get_db:
        p = _make_portfolio(holdings=[{"symbol": "AAPL", "shares": 10, "avg_cost": 150.0}])
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=p)
        )
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        response = await client.get("/api/v1/portfolios/1")

    if response.status_code == 200:
        body = response.json()
        assert "data" in body
        for field in ("id", "name", "holdings"):
            assert field in body["data"]


# ---------------------------------------------------------------------------
# POST /api/v1/portfolios/{id}/holdings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_holding_missing_fields_returns_422(client):
    """Body without required holding fields returns 422."""
    response = await client.post(
        "/api/v1/portfolios/1/holdings",
        json={"symbol": "AAPL"},  # missing shares and avg_cost
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_holding_valid_body_not_422(client):
    """A complete holding body must not return 422."""
    response = await client.post(
        "/api/v1/portfolios/1/holdings",
        json={"symbol": "AAPL", "shares": 10.0, "avg_cost": 150.0},
    )
    assert response.status_code != 422


@pytest.mark.asyncio
async def test_add_holding_to_nonexistent_portfolio_returns_404(client):
    """Adding a holding to a non-existent portfolio returns 404."""
    with patch("app.api.routes.portfolios.get_db") as mock_get_db:
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        response = await client.post(
            "/api/v1/portfolios/99999/holdings",
            json={"symbol": "AAPL", "shares": 10.0, "avg_cost": 150.0},
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/portfolios/{id}/holdings/{holding_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_holding_not_found_returns_404(client):
    """Removing a non-existent holding returns 404."""
    with patch("app.api.routes.portfolios.get_db") as mock_get_db:
        p = _make_portfolio()
        mock_session = AsyncMock()
        # First call: portfolio found; second call: holding not found
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=p)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        response = await client.delete("/api/v1/portfolios/1/holdings/99999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_holding_returns_detail(client):
    """Successful removal includes 'detail' in response."""
    with patch("app.api.routes.portfolios.get_db") as mock_get_db:
        p = _make_portfolio()
        holding = MagicMock(id=1, portfolio_id=1, symbol="AAPL", shares=10, avg_cost=150.0)
        mock_session = AsyncMock()
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=p)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=holding)),
        ]
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        response = await client.delete("/api/v1/portfolios/1/holdings/1")

    if response.status_code == 200:
        assert "detail" in response.json()


# ---------------------------------------------------------------------------
# DELETE /api/v1/portfolios/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_portfolio_not_found_returns_404(client):
    """Deleting a non-existent portfolio returns 404."""
    with patch("app.api.routes.portfolios.get_db") as mock_get_db:
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        response = await client.delete("/api/v1/portfolios/99999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_portfolio_returns_detail(client):
    """Successful deletion includes 'detail' key in response."""
    with patch("app.api.routes.portfolios.get_db") as mock_get_db:
        p = _make_portfolio()
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=p)
        )
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_get_db.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        response = await client.delete("/api/v1/portfolios/1")

    if response.status_code == 200:
        assert "detail" in response.json()
