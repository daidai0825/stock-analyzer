"""Integration tests for POST /api/v1/backtest."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.backtester import BacktestConfig, BacktestResult, Trade


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_backtest_result(symbol: str = "AAPL") -> BacktestResult:
    """Build a minimal BacktestResult for mocking."""
    config = BacktestConfig(
        symbol=symbol,
        strategy="buy_and_hold",
        start_date="2023-01-01",
        end_date="2023-12-31",
        initial_capital=100_000.0,
    )
    return BacktestResult(
        config=config,
        trades=[
            Trade(
                date="2023-01-03",
                action="buy",
                price=130.0,
                shares=769,
                commission=14.26,
                value=99970.0,
            ),
            Trade(
                date="2023-12-29",
                action="sell",
                price=192.0,
                shares=769,
                commission=35.55,
                value=147648.0,
            ),
        ],
        equity_curve=[
            {"date": "2023-01-03", "value": 100_000.0},
            {"date": "2023-12-29", "value": 147_500.0},
        ],
        total_return=47.5,
        annualized_return=47.5,
        max_drawdown=-8.3,
        sharpe_ratio=1.85,
        win_rate=100.0,
        total_trades=1,
        final_value=147_500.0,
    )


VALID_REQUEST = {
    "symbol": "AAPL",
    "strategy": "buy_and_hold",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "initial_capital": 100000.0,
    "commission": 0.001425,
    "tax": 0.0,
    "params": {},
}


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backtest_missing_symbol_returns_422(client):
    """Body without 'symbol' fails Pydantic validation → 422."""
    body = {**VALID_REQUEST}
    del body["symbol"]
    response = await client.post("/api/v1/backtest", json=body)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_backtest_missing_strategy_returns_422(client):
    body = {**VALID_REQUEST}
    del body["strategy"]
    response = await client.post("/api/v1/backtest", json=body)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_backtest_missing_dates_returns_422(client):
    body = {**VALID_REQUEST}
    del body["start_date"]
    response = await client.post("/api/v1/backtest", json=body)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backtest_returns_200_with_envelope(client):
    """Backtest returns 200 with a 'data' envelope."""
    with (
        patch("app.api.routes.backtest.get_db"),
        patch("app.api.routes.backtest.get_backtester") as mock_get_backtester,
    ):
        mock_bt = MagicMock()
        mock_bt.run = AsyncMock(return_value=_make_backtest_result())
        mock_get_backtester.return_value = mock_bt

        response = await client.post("/api/v1/backtest", json=VALID_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert "data" in body


@pytest.mark.asyncio
async def test_backtest_result_required_metric_fields(client):
    """The result object must contain all required performance metric keys."""
    with (
        patch("app.api.routes.backtest.get_db"),
        patch("app.api.routes.backtest.get_backtester") as mock_get_backtester,
    ):
        mock_bt = MagicMock()
        mock_bt.run = AsyncMock(return_value=_make_backtest_result())
        mock_get_backtester.return_value = mock_bt

        response = await client.post("/api/v1/backtest", json=VALID_REQUEST)

    data = response.json()["data"]
    required = (
        "symbol",
        "strategy",
        "start_date",
        "end_date",
        "initial_capital",
        "final_value",
        "total_return",
        "annualized_return",
        "max_drawdown",
        "sharpe_ratio",
        "win_rate",
        "total_trades",
        "trades",
        "equity_curve",
    )
    for field in required:
        assert field in data, f"backtest result missing '{field}'"


@pytest.mark.asyncio
async def test_backtest_trades_is_list(client):
    """'trades' field must be a list."""
    with (
        patch("app.api.routes.backtest.get_db"),
        patch("app.api.routes.backtest.get_backtester") as mock_get_backtester,
    ):
        mock_bt = MagicMock()
        mock_bt.run = AsyncMock(return_value=_make_backtest_result())
        mock_get_backtester.return_value = mock_bt

        response = await client.post("/api/v1/backtest", json=VALID_REQUEST)

    assert isinstance(response.json()["data"]["trades"], list)


@pytest.mark.asyncio
async def test_backtest_equity_curve_is_list(client):
    """'equity_curve' field must be a list of date/value objects."""
    with (
        patch("app.api.routes.backtest.get_db"),
        patch("app.api.routes.backtest.get_backtester") as mock_get_backtester,
    ):
        mock_bt = MagicMock()
        mock_bt.run = AsyncMock(return_value=_make_backtest_result())
        mock_get_backtester.return_value = mock_bt

        response = await client.post("/api/v1/backtest", json=VALID_REQUEST)

    equity_curve = response.json()["data"]["equity_curve"]
    assert isinstance(equity_curve, list)
    for point in equity_curve:
        assert "date" in point
        assert "value" in point
        assert isinstance(point["value"], (int, float))


@pytest.mark.asyncio
async def test_backtest_trade_fields(client):
    """Each trade must have the expected fields."""
    with (
        patch("app.api.routes.backtest.get_db"),
        patch("app.api.routes.backtest.get_backtester") as mock_get_backtester,
    ):
        mock_bt = MagicMock()
        mock_bt.run = AsyncMock(return_value=_make_backtest_result())
        mock_get_backtester.return_value = mock_bt

        response = await client.post("/api/v1/backtest", json=VALID_REQUEST)

    trades = response.json()["data"]["trades"]
    assert len(trades) > 0
    for trade in trades:
        for field in ("date", "action", "price", "shares", "commission", "value"):
            assert field in trade, f"trade missing '{field}'"


@pytest.mark.asyncio
async def test_backtest_default_capital_used(client):
    """When initial_capital is omitted it defaults to 100,000."""
    with (
        patch("app.api.routes.backtest.get_db"),
        patch("app.api.routes.backtest.get_backtester") as mock_get_backtester,
    ):
        mock_bt = MagicMock()
        mock_bt.run = AsyncMock(return_value=_make_backtest_result())
        mock_get_backtester.return_value = mock_bt

        await client.post(
            "/api/v1/backtest",
            json={
                "symbol": "AAPL",
                "strategy": "buy_and_hold",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            },
        )

        call_args = mock_bt.run.call_args
        if call_args is not None:
            config = call_args.args[0]
            assert config.initial_capital == 100_000.0


@pytest.mark.asyncio
async def test_backtest_sma_crossover_strategy_accepted(client):
    """sma_crossover strategy must be accepted without 422."""
    with (
        patch("app.api.routes.backtest.get_db"),
        patch("app.api.routes.backtest.get_backtester") as mock_get_backtester,
    ):
        mock_bt = MagicMock()
        mock_bt.run = AsyncMock(return_value=_make_backtest_result())
        mock_get_backtester.return_value = mock_bt

        response = await client.post(
            "/api/v1/backtest",
            json={
                **VALID_REQUEST,
                "strategy": "sma_crossover",
                "params": {"short_period": 10, "long_period": 50},
            },
        )

    assert response.status_code != 422
