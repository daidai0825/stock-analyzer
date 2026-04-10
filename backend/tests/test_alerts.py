"""Tests for the alert API endpoints and AlertEvaluator service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.alert import Alert
from app.services.alert_evaluator import AlertEvaluationError, AlertEvaluator
from app.services.data_fetcher import StockDataFetcher
from app.services.technical_analysis import TechnicalAnalyzer


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """Async HTTP client backed by the ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_price_records(close: float, volume: int = 1_000_000) -> list[dict]:
    """Return a minimal list of OHLCV records with the given close price."""
    return [
        {
            "date": "2024-01-02",
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": volume,
            "adj_close": close,
        }
    ]


def _make_long_price_records(
    n: int = 120, base_close: float = 100.0
) -> list[dict]:
    """Return *n* daily OHLCV records with gradually increasing closes."""
    records = []
    for i in range(n):
        close = base_close + i * 0.5
        records.append(
            {
                "date": f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1_000_000,
                "adj_close": close,
            }
        )
    return records


# ---------------------------------------------------------------------------
# API — create alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_alert_price_above(client):
    """POST /api/v1/alerts returns 201 and the created alert."""
    payload = {
        "symbol": "AAPL",
        "alert_type": "price_above",
        "condition": {"target_price": 200.0},
    }
    response = await client.post("/api/v1/alerts", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert "data" in body
    data = body["data"]
    assert data["symbol"] == "AAPL"
    assert data["alert_type"] == "price_above"
    assert data["condition"] == {"target_price": 200.0}
    assert data["is_active"] is True
    assert data["triggered_at"] is None
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_alert_invalid_type(client):
    """POST /api/v1/alerts with an unknown alert_type returns 422."""
    payload = {
        "symbol": "AAPL",
        "alert_type": "not_a_valid_type",
        "condition": {"target_price": 100.0},
    }
    response = await client.post("/api/v1/alerts", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# API — list alerts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_alerts_envelope(client):
    """GET /api/v1/alerts returns the standard response envelope."""
    response = await client.get("/api/v1/alerts")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    meta = body["meta"]
    assert "total" in meta
    assert "page" in meta
    assert "limit" in meta


@pytest.mark.asyncio
async def test_list_alerts_filter_by_symbol(client):
    """GET /api/v1/alerts?symbol=X returns only alerts for that symbol."""
    # Create two alerts for different symbols.
    await client.post(
        "/api/v1/alerts",
        json={"symbol": "TSLA", "alert_type": "price_above", "condition": {"target_price": 300.0}},
    )
    await client.post(
        "/api/v1/alerts",
        json={"symbol": "NVDA", "alert_type": "price_below", "condition": {"target_price": 100.0}},
    )

    response = await client.get("/api/v1/alerts", params={"symbol": "TSLA"})
    assert response.status_code == 200
    body = response.json()
    assert all(item["symbol"] == "TSLA" for item in body["data"])


@pytest.mark.asyncio
async def test_list_alerts_filter_by_is_active(client):
    """GET /api/v1/alerts?is_active=true returns only active alerts."""
    response = await client.get("/api/v1/alerts", params={"is_active": True})
    assert response.status_code == 200
    body = response.json()
    assert all(item["is_active"] is True for item in body["data"])


# ---------------------------------------------------------------------------
# API — get single alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_alert_200(client):
    """GET /api/v1/alerts/{id} returns the alert."""
    create_resp = await client.post(
        "/api/v1/alerts",
        json={"symbol": "META", "alert_type": "rsi_above", "condition": {"threshold": 70}},
    )
    alert_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/alerts/{alert_id}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == alert_id


@pytest.mark.asyncio
async def test_get_alert_404(client):
    """GET /api/v1/alerts/99999 returns 404 for a non-existent alert."""
    response = await client.get("/api/v1/alerts/99999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# API — update alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_alert_toggle_active(client):
    """PUT /api/v1/alerts/{id} can toggle is_active."""
    create_resp = await client.post(
        "/api/v1/alerts",
        json={"symbol": "AMZN", "alert_type": "price_below", "condition": {"target_price": 80.0}},
    )
    alert_id = create_resp.json()["data"]["id"]

    response = await client.put(f"/api/v1/alerts/{alert_id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["data"]["is_active"] is False

    response = await client.put(f"/api/v1/alerts/{alert_id}", json={"is_active": True})
    assert response.status_code == 200
    assert response.json()["data"]["is_active"] is True
    # Re-activating should clear triggered_at.
    assert response.json()["data"]["triggered_at"] is None


# ---------------------------------------------------------------------------
# API — delete alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_alert(client):
    """DELETE /api/v1/alerts/{id} removes the alert and returns confirmation."""
    create_resp = await client.post(
        "/api/v1/alerts",
        json={"symbol": "GOOGL", "alert_type": "volume_above", "condition": {"threshold": 5_000_000}},
    )
    alert_id = create_resp.json()["data"]["id"]

    del_resp = await client.delete(f"/api/v1/alerts/{alert_id}")
    assert del_resp.status_code == 200
    assert "detail" in del_resp.json()

    # Subsequent GET should 404.
    get_resp = await client.get(f"/api/v1/alerts/{alert_id}")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# API — check alert now (mocked evaluator)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_alert_now_triggered(client):
    """GET /api/v1/alerts/{id}/check returns triggered=True when condition met."""
    create_resp = await client.post(
        "/api/v1/alerts",
        json={"symbol": "AAPL", "alert_type": "price_above", "condition": {"target_price": 100.0}},
    )
    alert_id = create_resp.json()["data"]["id"]

    mock_evaluator = AsyncMock()
    mock_evaluator.evaluate = AsyncMock(return_value=(True, 185.5))

    with patch("app.api.routes.alerts.get_alert_evaluator", return_value=mock_evaluator):
        from app.api.deps import get_alert_evaluator

        app.dependency_overrides[get_alert_evaluator] = lambda: mock_evaluator
        try:
            response = await client.get(f"/api/v1/alerts/{alert_id}/check")
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["triggered"] is True
    assert body["current_value"] == 185.5


@pytest.mark.asyncio
async def test_check_alert_now_not_triggered(client):
    """GET /api/v1/alerts/{id}/check returns triggered=False when condition not met."""
    create_resp = await client.post(
        "/api/v1/alerts",
        json={"symbol": "AAPL", "alert_type": "price_above", "condition": {"target_price": 500.0}},
    )
    alert_id = create_resp.json()["data"]["id"]

    mock_evaluator = AsyncMock()
    mock_evaluator.evaluate = AsyncMock(return_value=(False, 185.5))

    from app.api.deps import get_alert_evaluator

    app.dependency_overrides[get_alert_evaluator] = lambda: mock_evaluator
    try:
        response = await client.get(f"/api/v1/alerts/{alert_id}/check")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["triggered"] is False
    assert body["current_value"] == 185.5


# ---------------------------------------------------------------------------
# AlertEvaluator unit tests
# ---------------------------------------------------------------------------


def _make_evaluator(fetch_return: list[dict]) -> AlertEvaluator:
    """Build an AlertEvaluator with a mocked StockDataFetcher."""
    fetcher = MagicMock(spec=StockDataFetcher)
    fetcher.fetch_history = AsyncMock(return_value=fetch_return)
    analyzer = TechnicalAnalyzer()
    return AlertEvaluator(fetcher, analyzer)


def _make_alert(
    alert_type: str,
    condition: dict,
    symbol: str = "AAPL",
) -> Alert:
    """Construct an in-memory Alert ORM object (not persisted)."""
    alert = Alert.__new__(Alert)
    alert.id = 1
    alert.symbol = symbol
    alert.alert_type = alert_type
    alert.condition = condition
    alert.is_active = True
    alert.triggered_at = None
    alert.created_at = datetime.now(tz=timezone.utc)
    return alert


@pytest.mark.asyncio
async def test_evaluator_price_above_triggered():
    """AlertEvaluator triggers price_above when close > target."""
    evaluator = _make_evaluator(_make_price_records(close=200.0))
    alert = _make_alert("price_above", {"target_price": 150.0})
    triggered, value = await evaluator.evaluate(alert)
    assert triggered is True
    assert value == pytest.approx(200.0)


@pytest.mark.asyncio
async def test_evaluator_price_above_not_triggered():
    """AlertEvaluator does not trigger price_above when close <= target."""
    evaluator = _make_evaluator(_make_price_records(close=100.0))
    alert = _make_alert("price_above", {"target_price": 150.0})
    triggered, value = await evaluator.evaluate(alert)
    assert triggered is False
    assert value == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_evaluator_price_below_triggered():
    """AlertEvaluator triggers price_below when close < target."""
    evaluator = _make_evaluator(_make_price_records(close=50.0))
    alert = _make_alert("price_below", {"target_price": 100.0})
    triggered, value = await evaluator.evaluate(alert)
    assert triggered is True
    assert value == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_evaluator_rsi_above_triggered():
    """AlertEvaluator triggers rsi_above when RSI > threshold."""
    # Build a price series with enough bars for RSI(14) and a monotonically
    # rising trend to produce a high RSI value.
    records = _make_long_price_records(n=120, base_close=100.0)
    evaluator = _make_evaluator(records)
    alert = _make_alert("rsi_above", {"period": 14, "threshold": 1.0})  # threshold=1 always fires
    triggered, value = await evaluator.evaluate(alert)
    assert triggered is True
    assert 0.0 <= value <= 100.0


@pytest.mark.asyncio
async def test_evaluator_rsi_above_not_triggered():
    """AlertEvaluator does not trigger rsi_above when RSI < threshold."""
    records = _make_long_price_records(n=120, base_close=100.0)
    evaluator = _make_evaluator(records)
    alert = _make_alert("rsi_above", {"period": 14, "threshold": 99.9})  # threshold so high it never fires
    triggered, value = await evaluator.evaluate(alert)
    assert triggered is False


@pytest.mark.asyncio
async def test_evaluator_volume_above_triggered():
    """AlertEvaluator triggers volume_above when volume > threshold."""
    records = _make_price_records(close=100.0, volume=5_000_000)
    evaluator = _make_evaluator(records)
    alert = _make_alert("volume_above", {"threshold": 1_000_000})
    triggered, value = await evaluator.evaluate(alert)
    assert triggered is True
    assert value == pytest.approx(5_000_000.0)


@pytest.mark.asyncio
async def test_evaluator_volume_above_not_triggered():
    """AlertEvaluator does not trigger volume_above when volume <= threshold."""
    records = _make_price_records(close=100.0, volume=500_000)
    evaluator = _make_evaluator(records)
    alert = _make_alert("volume_above", {"threshold": 1_000_000})
    triggered, value = await evaluator.evaluate(alert)
    assert triggered is False
    assert value == pytest.approx(500_000.0)


@pytest.mark.asyncio
async def test_evaluator_unknown_type_raises():
    """AlertEvaluator raises AlertEvaluationError for unknown alert_type."""
    evaluator = _make_evaluator([])
    alert = _make_alert("nonexistent_type", {})
    with pytest.raises(AlertEvaluationError):
        await evaluator.evaluate(alert)


@pytest.mark.asyncio
async def test_evaluator_no_data_raises():
    """AlertEvaluator raises AlertEvaluationError when fetcher returns no data."""
    evaluator = _make_evaluator([])  # empty list simulates data fetch failure
    alert = _make_alert("price_above", {"target_price": 100.0})
    with pytest.raises(AlertEvaluationError):
        await evaluator.evaluate(alert)
