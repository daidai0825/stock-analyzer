import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async HTTP client for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_stock_data():
    """Sample US stock response matching API schema."""
    return {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "market": "US",
    }


@pytest.fixture
def sample_tw_stock_data():
    """Sample Taiwan stock response matching API schema."""
    return {
        "symbol": "2330",
        "name": "台積電",
        "market": "TW",
    }


@pytest.fixture
def sample_price_history():
    """Sample OHLCV data for two trading days."""
    return [
        {
            "date": "2024-01-02",
            "open": 185.0,
            "high": 186.5,
            "low": 184.0,
            "close": 185.5,
            "volume": 50_000_000,
        },
        {
            "date": "2024-01-03",
            "open": 185.5,
            "high": 187.0,
            "low": 183.5,
            "close": 184.0,
            "volume": 48_000_000,
        },
    ]


@pytest.fixture
def sample_indicators():
    """Sample technical indicator payload."""
    return {
        "sma": [184.5, 185.0],
        "rsi": [55.3, 52.1],
    }


@pytest.fixture
def sample_watchlist_payload():
    """Minimum payload for creating a watchlist."""
    return {
        "name": "My Watchlist",
        "symbols": ["AAPL", "MSFT"],
    }


@pytest.fixture
def sample_watchlist_response():
    """Typical watchlist response body returned by the API."""
    return {
        "id": 1,
        "name": "My Watchlist",
        "symbols": ["AAPL", "MSFT"],
    }
