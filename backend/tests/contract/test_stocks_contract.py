"""Contract tests for the /api/v1/stocks endpoints.

Shape tests (envelope structure, HTTP status codes, query-param handling)
pass against the current stub implementation.

Tests that require real data from the Data Engineer are marked xfail.
"""

import pytest


# ---------------------------------------------------------------------------
# GET /api/v1/stocks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestListStocksContract:
    async def test_returns_200(self, client):
        response = await client.get("/api/v1/stocks")
        assert response.status_code == 200

    async def test_response_has_data_key(self, client):
        body = (await client.get("/api/v1/stocks")).json()
        assert "data" in body

    async def test_data_is_list(self, client):
        body = (await client.get("/api/v1/stocks")).json()
        assert isinstance(body["data"], list)

    async def test_response_has_meta_key(self, client):
        body = (await client.get("/api/v1/stocks")).json()
        assert "meta" in body

    async def test_meta_has_required_integer_fields(self, client):
        meta = (await client.get("/api/v1/stocks")).json()["meta"]
        for field in ("total", "page", "limit"):
            assert field in meta, f"meta missing '{field}'"
            assert isinstance(meta[field], int), f"meta.{field} must be int"

    async def test_default_market_param_is_accepted(self, client):
        """Calling without ?market should not raise an error."""
        response = await client.get("/api/v1/stocks")
        assert response.status_code == 200

    async def test_market_tw_param_accepted(self, client):
        """?market=TW must be accepted (not 422)."""
        response = await client.get("/api/v1/stocks?market=TW")
        assert response.status_code == 200

    async def test_market_us_param_accepted(self, client):
        response = await client.get("/api/v1/stocks?market=US")
        assert response.status_code == 200

    async def test_query_search_param_accepted(self, client):
        """?q=apple must be accepted without validation error."""
        response = await client.get("/api/v1/stocks?q=apple")
        assert response.status_code == 200

    async def test_pagination_params_accepted(self, client):
        response = await client.get("/api/v1/stocks?page=1&limit=10")
        assert response.status_code == 200

    # -- tests that require real data -----------------------------------------

    @pytest.mark.xfail(reason="Awaiting Data Engineer: market filter not implemented")
    async def test_market_tw_filters_to_tw_stocks(self, client):
        body = (await client.get("/api/v1/stocks?market=TW")).json()
        assert len(body["data"]) > 0
        for item in body["data"]:
            assert item["market"] == "TW"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: market filter not implemented")
    async def test_market_us_filters_to_us_stocks(self, client):
        body = (await client.get("/api/v1/stocks?market=US")).json()
        assert len(body["data"]) > 0
        for item in body["data"]:
            assert item["market"] == "US"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: search not implemented")
    async def test_search_returns_matching_symbols(self, client):
        body = (await client.get("/api/v1/stocks?q=apple")).json()
        assert len(body["data"]) > 0

    @pytest.mark.xfail(reason="Awaiting Data Engineer: search not implemented")
    async def test_tw_search_returns_matching_stocks(self, client):
        body = (await client.get("/api/v1/stocks?market=TW&q=台積電")).json()
        assert len(body["data"]) > 0


# ---------------------------------------------------------------------------
# GET /api/v1/stocks/{symbol}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStockDetailContract:
    async def test_returns_200_or_404(self, client):
        """Stub may return 200 with null data; 404 is also valid."""
        response = await client.get("/api/v1/stocks/AAPL")
        assert response.status_code in (200, 404)

    async def test_200_response_has_data_key(self, client):
        response = await client.get("/api/v1/stocks/AAPL")
        if response.status_code == 200:
            assert "data" in response.json()

    @pytest.mark.xfail(reason="Awaiting Data Engineer: stock detail not implemented")
    async def test_known_us_symbol_returns_data(self, client, sample_stock_data):
        response = await client.get("/api/v1/stocks/AAPL")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data is not None
        assert data["symbol"] == "AAPL"
        assert data["market"] == "US"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: stock detail not implemented")
    async def test_known_tw_symbol_returns_data(self, client, sample_tw_stock_data):
        """台積電 (2330) must be retrievable."""
        response = await client.get("/api/v1/stocks/2330")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data is not None
        assert data["symbol"] == "2330"
        assert data["market"] == "TW"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: 404 handling not implemented")
    async def test_unknown_symbol_returns_404(self, client):
        response = await client.get("/api/v1/stocks/INVALID_SYMBOL_XYZ123")
        assert response.status_code == 404

    @pytest.mark.xfail(reason="Awaiting Data Engineer: error envelope not implemented")
    async def test_unknown_symbol_error_has_detail(self, client):
        response = await client.get("/api/v1/stocks/INVALID_SYMBOL_XYZ123")
        body = response.json()
        assert "detail" in body

    @pytest.mark.xfail(reason="Awaiting Data Engineer: stock detail schema not finalized")
    async def test_stock_detail_required_fields(self, client):
        """Stock detail must contain symbol, name, and market."""
        response = await client.get("/api/v1/stocks/AAPL")
        data = response.json()["data"]
        for field in ("symbol", "name", "market"):
            assert field in data, f"stock detail missing '{field}'"


# ---------------------------------------------------------------------------
# GET /api/v1/stocks/{symbol}/history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStockHistoryContract:
    async def test_returns_200(self, client):
        response = await client.get("/api/v1/stocks/AAPL/history")
        assert response.status_code == 200

    async def test_response_has_data_key(self, client):
        body = (await client.get("/api/v1/stocks/AAPL/history")).json()
        assert "data" in body

    async def test_data_is_list(self, client):
        body = (await client.get("/api/v1/stocks/AAPL/history")).json()
        assert isinstance(body["data"], list)

    async def test_period_param_accepted(self, client):
        """Various period values must not cause a 422."""
        for period in ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"):
            response = await client.get(f"/api/v1/stocks/AAPL/history?period={period}")
            assert response.status_code == 200, f"period={period} returned {response.status_code}"

    async def test_interval_param_accepted(self, client):
        for interval in ("1d", "1wk", "1mo"):
            response = await client.get(
                f"/api/v1/stocks/AAPL/history?period=1mo&interval={interval}"
            )
            assert response.status_code == 200, (
                f"interval={interval} returned {response.status_code}"
            )

    @pytest.mark.xfail(reason="Awaiting Data Engineer: history data not implemented")
    async def test_us_stock_history_returns_ohlcv(self, client, sample_price_history):
        body = (await client.get("/api/v1/stocks/AAPL/history?period=5d&interval=1d")).json()
        assert len(body["data"]) > 0
        row = body["data"][0]
        for field in ("date", "open", "high", "low", "close", "volume"):
            assert field in row, f"OHLCV row missing '{field}'"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: history data not implemented")
    async def test_tw_stock_history_returns_ohlcv(self, client):
        body = (await client.get("/api/v1/stocks/2330/history?period=5d&interval=1d")).json()
        assert len(body["data"]) > 0
        row = body["data"][0]
        for field in ("date", "open", "high", "low", "close", "volume"):
            assert field in row, f"TW OHLCV row missing '{field}'"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: history data not implemented")
    async def test_history_dates_are_chronological(self, client):
        body = (await client.get("/api/v1/stocks/AAPL/history?period=1mo&interval=1d")).json()
        dates = [row["date"] for row in body["data"]]
        assert dates == sorted(dates), "history must be returned in chronological order"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: history data not implemented")
    async def test_history_numeric_fields_are_numbers(self, client):
        body = (await client.get("/api/v1/stocks/AAPL/history?period=5d&interval=1d")).json()
        for row in body["data"]:
            for field in ("open", "high", "low", "close"):
                assert isinstance(row[field], (int, float)), f"{field} must be numeric"
            assert isinstance(row["volume"], int), "volume must be int"


# ---------------------------------------------------------------------------
# GET /api/v1/stocks/{symbol}/indicators
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStockIndicatorsContract:
    async def test_returns_200(self, client):
        response = await client.get("/api/v1/stocks/AAPL/indicators")
        assert response.status_code == 200

    async def test_response_has_data_key(self, client):
        body = (await client.get("/api/v1/stocks/AAPL/indicators")).json()
        assert "data" in body

    async def test_data_is_dict(self, client):
        body = (await client.get("/api/v1/stocks/AAPL/indicators")).json()
        assert isinstance(body["data"], dict)

    async def test_indicators_param_accepted(self, client):
        """?indicators=sma,rsi must not cause 422."""
        response = await client.get("/api/v1/stocks/AAPL/indicators?indicators=sma,rsi")
        assert response.status_code == 200

    async def test_single_indicator_param_accepted(self, client):
        response = await client.get("/api/v1/stocks/AAPL/indicators?indicators=rsi")
        assert response.status_code == 200

    @pytest.mark.xfail(reason="Awaiting Data Engineer: indicators not implemented")
    async def test_sma_key_present_when_requested(self, client):
        body = (
            await client.get("/api/v1/stocks/AAPL/indicators?indicators=sma")
        ).json()
        assert "sma" in body["data"]

    @pytest.mark.xfail(reason="Awaiting Data Engineer: indicators not implemented")
    async def test_rsi_key_present_when_requested(self, client):
        body = (
            await client.get("/api/v1/stocks/AAPL/indicators?indicators=rsi")
        ).json()
        assert "rsi" in body["data"]

    @pytest.mark.xfail(reason="Awaiting Data Engineer: indicators not implemented")
    async def test_macd_key_present_when_requested(self, client):
        body = (
            await client.get("/api/v1/stocks/AAPL/indicators?indicators=macd")
        ).json()
        assert "macd" in body["data"]

    @pytest.mark.xfail(reason="Awaiting Data Engineer: indicators not implemented")
    async def test_multiple_indicators_all_present(self, client):
        body = (
            await client.get("/api/v1/stocks/AAPL/indicators?indicators=sma,rsi,macd")
        ).json()
        for key in ("sma", "rsi", "macd"):
            assert key in body["data"], f"indicator '{key}' missing from response"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: indicators not implemented")
    async def test_indicator_values_are_lists(self, client):
        body = (
            await client.get("/api/v1/stocks/AAPL/indicators?indicators=sma,rsi")
        ).json()
        for key in ("sma", "rsi"):
            assert isinstance(body["data"][key], list), f"{key} values must be a list"
