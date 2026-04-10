"""Tests for StockDataFetcher — all external I/O is mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.services.data_fetcher import StockDataFetcher


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fetcher() -> StockDataFetcher:
    return StockDataFetcher()


def _make_yf_df() -> pd.DataFrame:
    """Return a minimal DataFrame that mimics yfinance Ticker.history() output."""
    idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [105.0, 106.0],
            "Low": [99.0, 100.0],
            "Close": [103.0, 104.0],
            "Volume": [1_000_000, 900_000],
            "Adj Close": [103.0, 104.0],
        },
        index=idx,
    )


def _finmind_payload(symbol: str) -> dict:
    return {
        "status": 200,
        "msg": "success",
        "data": [
            {
                "date": "2024-01-02",
                "open": 500.0,
                "max": 510.0,
                "min": 498.0,
                "close": 505.0,
                "Trading_Volume": 20_000_000,
            },
            {
                "date": "2024-01-03",
                "open": 505.0,
                "max": 515.0,
                "min": 502.0,
                "close": 510.0,
                "Trading_Volume": 18_000_000,
            },
        ],
    }


# ---------------------------------------------------------------------------
# _is_tw_stock
# ---------------------------------------------------------------------------


class TestIsTwStock:
    def test_pure_digit_is_tw(self, fetcher):
        assert fetcher._is_tw_stock("2330") is True

    def test_tw_suffix_is_tw(self, fetcher):
        assert fetcher._is_tw_stock("2330.TW") is True

    def test_two_suffix_is_tw(self, fetcher):
        assert fetcher._is_tw_stock("6531.TWO") is True

    def test_us_ticker_is_not_tw(self, fetcher):
        assert fetcher._is_tw_stock("AAPL") is False

    def test_us_ticker_with_digits_is_not_tw(self, fetcher):
        # "3M" contains digits but is not pure-digit
        assert fetcher._is_tw_stock("3M") is False

    def test_case_insensitive(self, fetcher):
        assert fetcher._is_tw_stock("2330.tw") is True


# ---------------------------------------------------------------------------
# US fetching (yfinance mocked)
# ---------------------------------------------------------------------------


class TestFetchUS:
    async def test_fetch_history_us_returns_records(self, fetcher):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_yf_df()

        with patch("app.services.data_fetcher.yf.Ticker", return_value=mock_ticker):
            records = await fetcher.fetch_history("AAPL", period="5d")

        assert len(records) == 2
        first = records[0]
        assert first["date"] == "2024-01-02"
        assert first["open"] == 100.0
        assert first["high"] == 105.0
        assert first["low"] == 99.0
        assert first["close"] == 103.0
        assert first["volume"] == 1_000_000
        assert first["adj_close"] == 103.0

    async def test_fetch_history_us_empty_df_returns_empty_list(self, fetcher):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()

        with patch("app.services.data_fetcher.yf.Ticker", return_value=mock_ticker):
            records = await fetcher.fetch_history("INVALID_SYM")

        assert records == []

    async def test_fetch_stock_info_us(self, fetcher):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "industry": "Consumer Electronics",
            "longBusinessSummary": "Apple designs Mac computers.",
        }

        with patch("app.services.data_fetcher.yf.Ticker", return_value=mock_ticker):
            info = await fetcher.fetch_stock_info("AAPL")

        assert info["symbol"] == "AAPL"
        assert info["name"] == "Apple Inc."
        assert info["industry"] == "Consumer Electronics"
        assert info["market"] == "US"

    async def test_fetch_history_us_exception_returns_empty_list(self, fetcher):
        with patch(
            "app.services.data_fetcher.yf.Ticker", side_effect=Exception("network error")
        ):
            records = await fetcher.fetch_history("AAPL")

        assert records == []


# ---------------------------------------------------------------------------
# TW fetching (FinMind HTTP mocked via httpx)
# ---------------------------------------------------------------------------


class TestFetchTW:
    async def test_fetch_history_tw_bare_symbol(self, fetcher):
        mock_response = MagicMock()
        mock_response.json.return_value = _finmind_payload("2330")
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.data_fetcher.httpx.AsyncClient", return_value=mock_client):
            records = await fetcher.fetch_history("2330", period="1y")

        assert len(records) == 2
        first = records[0]
        assert first["date"] == "2024-01-02"
        assert first["open"] == 500.0
        assert first["high"] == 510.0
        assert first["low"] == 498.0
        assert first["close"] == 505.0
        assert first["volume"] == 20_000_000
        # adj_close falls back to close for FinMind data
        assert first["adj_close"] == 505.0

    async def test_fetch_history_tw_with_suffix(self, fetcher):
        """'2330.TW' should strip suffix and hit FinMind with bare '2330'."""
        mock_response = MagicMock()
        mock_response.json.return_value = _finmind_payload("2330")
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.data_fetcher.httpx.AsyncClient", return_value=mock_client):
            records = await fetcher.fetch_history("2330.TW", period="6mo")

        # Verify the API was called with the bare symbol (data_id=2330)
        call_kwargs = mock_client.get.call_args
        params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
        assert params["data_id"] == "2330"
        assert len(records) == 2

    async def test_fetch_history_tw_non_200_status(self, fetcher):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": 402, "msg": "Unauthorized"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.data_fetcher.httpx.AsyncClient", return_value=mock_client):
            records = await fetcher.fetch_history("2330")

        assert records == []

    async def test_fetch_history_tw_network_error_returns_empty(self, fetcher):
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("connection refused", request=MagicMock())
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.data_fetcher.httpx.AsyncClient", return_value=mock_client):
            records = await fetcher.fetch_history("2330")

        assert records == []

    async def test_fetch_stock_info_tw(self, fetcher):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": 200,
            "data": [
                {
                    "stock_name": "台積電",
                    "industry_category": "半導體",
                    "business_scope": "積體電路製造。",
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.data_fetcher.httpx.AsyncClient", return_value=mock_client):
            info = await fetcher.fetch_stock_info("2330")

        assert info["symbol"] == "2330"
        assert info["name"] == "台積電"
        assert info["industry"] == "半導體"
        assert info["market"] == "TW"
