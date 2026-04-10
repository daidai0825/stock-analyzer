"""Unit tests for ValuationAnalyzer.

All external I/O (yfinance, FinMind HTTP) is mocked so tests are
deterministic and do not require network access.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.data_fetcher import StockDataFetcher
from app.services.valuation import ValuationAnalyzer, _safe_float


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fetcher() -> StockDataFetcher:
    return StockDataFetcher()


@pytest.fixture
def analyzer(fetcher: StockDataFetcher) -> ValuationAnalyzer:
    return ValuationAnalyzer(fetcher=fetcher)


# ---------------------------------------------------------------------------
# _safe_float helper
# ---------------------------------------------------------------------------


class TestSafeFloat:
    def test_converts_int(self) -> None:
        assert _safe_float(42) == pytest.approx(42.0)

    def test_converts_float(self) -> None:
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_converts_string(self) -> None:
        assert _safe_float("1.5") == pytest.approx(1.5)

    def test_none_returns_none(self) -> None:
        assert _safe_float(None) is None

    def test_nan_returns_none(self) -> None:
        assert _safe_float(float("nan")) is None

    def test_invalid_string_returns_none(self) -> None:
        assert _safe_float("N/A") is None

    def test_zero_is_valid(self) -> None:
        assert _safe_float(0) == pytest.approx(0.0)

    def test_negative_is_valid(self) -> None:
        assert _safe_float(-5.5) == pytest.approx(-5.5)


# ---------------------------------------------------------------------------
# US Valuation (yfinance mocked)
# ---------------------------------------------------------------------------


class TestUSValuation:
    def _mock_info(self) -> dict:
        return {
            "trailingPE": 28.5,
            "priceToBook": 3.2,
            "priceToSalesTrailing12Months": 7.1,
            "dividendYield": 0.0055,
            "marketCap": 2_800_000_000_000,
            "trailingEps": 6.43,
            "totalRevenue": 400_000_000_000,
            "profitMargins": 0.257,
        }

    async def test_us_valuation_all_fields_populated(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        mock_ticker = MagicMock()
        mock_ticker.info = self._mock_info()

        with patch("app.services.valuation.yf.Ticker", return_value=mock_ticker):
            result = await analyzer.get_valuation("AAPL")

        assert result["pe_ratio"] == pytest.approx(28.5)
        assert result["pb_ratio"] == pytest.approx(3.2)
        assert result["ps_ratio"] == pytest.approx(7.1)
        assert result["dividend_yield"] == pytest.approx(0.0055)
        assert result["market_cap"] == pytest.approx(2_800_000_000_000)
        assert result["eps"] == pytest.approx(6.43)
        assert result["revenue"] == pytest.approx(400_000_000_000)
        assert result["profit_margin"] == pytest.approx(0.257)

    async def test_us_valuation_missing_pe_returns_none(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        info = self._mock_info()
        del info["trailingPE"]
        info.pop("forwardPE", None)
        mock_ticker = MagicMock()
        mock_ticker.info = info

        with patch("app.services.valuation.yf.Ticker", return_value=mock_ticker):
            result = await analyzer.get_valuation("AAPL")

        assert result["pe_ratio"] is None

    async def test_us_valuation_empty_info_returns_none_fields(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        mock_ticker = MagicMock()
        mock_ticker.info = {}

        with patch("app.services.valuation.yf.Ticker", return_value=mock_ticker):
            result = await analyzer.get_valuation("AAPL")

        assert result["pe_ratio"] is None
        assert result["pb_ratio"] is None
        assert result["market_cap"] is None
        assert result["revenue"] is None

    async def test_us_valuation_falls_back_to_forward_pe(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        """When trailingPE is absent, forwardPE is used as fallback."""
        info = {"forwardPE": 22.0}
        mock_ticker = MagicMock()
        mock_ticker.info = info

        with patch("app.services.valuation.yf.Ticker", return_value=mock_ticker):
            result = await analyzer.get_valuation("AAPL")

        assert result["pe_ratio"] == pytest.approx(22.0)

    async def test_us_valuation_exception_returns_empty(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        """An exception from yfinance should return all-None dict gracefully."""
        with patch("app.services.valuation.yf.Ticker", side_effect=Exception("network error")):
            result = await analyzer.get_valuation("AAPL")

        assert all(v is None for v in result.values())

    async def test_us_valuation_none_info_returns_empty(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        mock_ticker = MagicMock()
        mock_ticker.info = None

        with patch("app.services.valuation.yf.Ticker", return_value=mock_ticker):
            result = await analyzer.get_valuation("AAPL")

        # info or {} guards against None, so all fields should be None.
        assert result["pe_ratio"] is None


# ---------------------------------------------------------------------------
# TW Valuation (FinMind HTTP mocked)
# ---------------------------------------------------------------------------


class TestTWValuation:
    def _finmind_response(self, dataset: str, rows: list[dict]) -> dict:
        return {"status": 200, "msg": "success", "data": rows}

    def _mock_httpx(
        self, per_rows: list, div_rows: list, fin_rows: list
    ) -> tuple:
        """Return a context-manager-compatible mock for httpx.AsyncClient.

        Each GET call cycles through PER → Dividend → FinancialStatements
        based on the ``dataset`` query parameter.
        """
        async def _mock_get(url, params=None, **kwargs):
            dataset = (params or {}).get("dataset", "")
            if dataset == "TaiwanStockPER":
                payload = self._finmind_response(dataset, per_rows)
            elif dataset == "TaiwanStockDividend":
                payload = self._finmind_response(dataset, div_rows)
            elif dataset == "TaiwanStockFinancialStatements":
                payload = self._finmind_response(dataset, fin_rows)
            else:
                payload = {"status": 200, "data": []}

            resp = MagicMock()
            resp.json.return_value = payload
            resp.raise_for_status = MagicMock()
            return resp

        mock_client = AsyncMock()
        mock_client.get = _mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        return mock_client

    async def test_tw_valuation_all_fields_populated(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        per_rows = [{"PER": 15.3, "PBR": 2.1, "MarketValue": 200.0}]
        div_rows = [{"CashDividend": 5.0}]
        fin_rows = [{"EPS": 8.5, "Revenue": 500_000.0, "NetIncome": 100_000.0}]

        mock_client = self._mock_httpx(per_rows, div_rows, fin_rows)

        # Mock the price fetch used to compute dividend yield.
        price_mock = AsyncMock(
            return_value=[
                {
                    "date": "2024-01-31",
                    "close": 500.0,
                    "open": 498.0,
                    "high": 502.0,
                    "low": 497.0,
                    "volume": 1_000_000,
                    "adj_close": 500.0,
                }
            ]
        )
        analyzer.fetcher.fetch_history = price_mock

        with patch("app.services.valuation.httpx.AsyncClient", return_value=mock_client):
            result = await analyzer.get_valuation("2330")

        assert result["pe_ratio"] == pytest.approx(15.3)
        assert result["pb_ratio"] == pytest.approx(2.1)
        assert result["market_cap"] == pytest.approx(200.0 * 1e8)
        assert result["eps"] == pytest.approx(8.5)
        assert result["revenue"] == pytest.approx(500_000.0 * 1000)
        assert result["profit_margin"] == pytest.approx(100_000.0 / 500_000.0)
        # dividend_yield = CashDividend / close = 5.0 / 500.0 = 0.01
        assert result["dividend_yield"] == pytest.approx(0.01)

    async def test_tw_valuation_missing_per_data_returns_none(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        """Empty PER dataset → pe_ratio, pb_ratio, market_cap are None."""
        mock_client = self._mock_httpx([], [], [])
        analyzer.fetcher.fetch_history = AsyncMock(return_value=[])

        with patch("app.services.valuation.httpx.AsyncClient", return_value=mock_client):
            result = await analyzer.get_valuation("2330")

        assert result["pe_ratio"] is None
        assert result["pb_ratio"] is None
        assert result["market_cap"] is None

    async def test_tw_valuation_no_dividend_data_returns_none_yield(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        per_rows = [{"PER": 15.0, "PBR": 2.0, "MarketValue": 100.0}]
        mock_client = self._mock_httpx(per_rows, [], [])
        analyzer.fetcher.fetch_history = AsyncMock(return_value=[])

        with patch("app.services.valuation.httpx.AsyncClient", return_value=mock_client):
            result = await analyzer.get_valuation("2330")

        assert result["dividend_yield"] is None

    async def test_tw_valuation_symbol_with_suffix(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        """2330.TW should be treated as a TW stock and go through the TW path."""
        per_rows = [{"PER": 20.0, "PBR": 3.0, "MarketValue": 150.0}]
        mock_client = self._mock_httpx(per_rows, [], [])
        analyzer.fetcher.fetch_history = AsyncMock(return_value=[])

        with patch("app.services.valuation.httpx.AsyncClient", return_value=mock_client):
            result = await analyzer.get_valuation("2330.TW")

        # Confirms TW path was taken (ps_ratio is None in TW path).
        assert result["ps_ratio"] is None
        assert result["pe_ratio"] == pytest.approx(20.0)

    async def test_tw_valuation_finmind_non_200_returns_none(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        """FinMind returning status != 200 should yield None fields."""
        async def _failing_get(url, params=None, **kwargs):
            resp = MagicMock()
            resp.json.return_value = {"status": 402, "msg": "Unauthorized"}
            resp.raise_for_status = MagicMock()
            return resp

        mock_client = AsyncMock()
        mock_client.get = _failing_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        analyzer.fetcher.fetch_history = AsyncMock(return_value=[])

        with patch("app.services.valuation.httpx.AsyncClient", return_value=mock_client):
            result = await analyzer.get_valuation("2330")

        assert result["pe_ratio"] is None
        assert result["pb_ratio"] is None

    async def test_tw_valuation_profit_margin_zero_revenue_returns_none(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        """When revenue is 0, profit_margin must not divide-by-zero."""
        per_rows = [{"PER": 10.0, "PBR": 1.0, "MarketValue": 50.0}]
        fin_rows = [{"EPS": 1.0, "Revenue": 0.0, "NetIncome": 100.0}]
        mock_client = self._mock_httpx(per_rows, [], fin_rows)
        analyzer.fetcher.fetch_history = AsyncMock(return_value=[])

        with patch("app.services.valuation.httpx.AsyncClient", return_value=mock_client):
            result = await analyzer.get_valuation("2330")

        assert result["profit_margin"] is None

    async def test_get_valuation_returns_all_expected_keys(
        self, analyzer: ValuationAnalyzer
    ) -> None:
        """The returned dict must always have all 8 expected keys."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}

        with patch("app.services.valuation.yf.Ticker", return_value=mock_ticker):
            result = await analyzer.get_valuation("AAPL")

        expected_keys = {
            "pe_ratio",
            "pb_ratio",
            "ps_ratio",
            "dividend_yield",
            "market_cap",
            "eps",
            "revenue",
            "profit_margin",
        }
        assert set(result.keys()) == expected_keys
