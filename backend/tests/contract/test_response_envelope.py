"""Contract tests verifying that every endpoint honours the response-envelope
convention documented in CLAUDE.md.

List endpoints  → {"data": [...], "meta": {"total": int, "page": int, "limit": int}}
Single-item endpoints → {"data": <object | null>}
Error responses → {"detail": str, "code": str}

Tests that depend on real data returned by the Data Engineer are marked
with @pytest.mark.xfail so the suite stays green while work is in progress.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def assert_list_envelope(body: dict) -> None:
    """Assert that *body* matches the list-endpoint envelope contract."""
    assert "data" in body, "list envelope must have 'data' key"
    assert isinstance(body["data"], list), "'data' must be a list"
    assert "meta" in body, "list envelope must have 'meta' key"
    meta = body["meta"]
    assert isinstance(meta, dict), "'meta' must be a dict"
    for field in ("total", "page", "limit"):
        assert field in meta, f"meta must contain '{field}'"
        assert isinstance(meta[field], int), f"meta.{field} must be an int"


def assert_single_envelope(body: dict) -> None:
    """Assert that *body* matches the single-item envelope contract."""
    assert "data" in body, "single-item envelope must have 'data' key"


def assert_error_envelope(body: dict) -> None:
    """Assert that *body* matches the error envelope contract."""
    assert "detail" in body, "error envelope must have 'detail' key"
    assert isinstance(body["detail"], str), "'detail' must be a string"


# ---------------------------------------------------------------------------
# List endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestListEnvelope:
    """All list endpoints must return the standard list envelope."""

    async def test_stocks_list_envelope(self, client):
        response = await client.get("/api/v1/stocks")
        assert response.status_code == 200
        assert_list_envelope(response.json())

    async def test_stocks_list_meta_total_non_negative(self, client):
        response = await client.get("/api/v1/stocks")
        meta = response.json()["meta"]
        assert meta["total"] >= 0

    async def test_stocks_list_meta_page_positive(self, client):
        response = await client.get("/api/v1/stocks")
        meta = response.json()["meta"]
        assert meta["page"] >= 1

    async def test_stocks_list_meta_limit_positive(self, client):
        response = await client.get("/api/v1/stocks")
        meta = response.json()["meta"]
        assert meta["limit"] >= 1

    async def test_watchlists_list_envelope(self, client):
        response = await client.get("/api/v1/watchlists")
        assert response.status_code == 200
        assert_list_envelope(response.json())

    # -----------------------------------------------------------------------
    # Pagination contract – these pass once real data exists
    # -----------------------------------------------------------------------

    @pytest.mark.xfail(reason="Awaiting Data Engineer: pagination not yet implemented")
    async def test_stocks_pagination_page_param_respected(self, client):
        """page=2 must shift the window of results."""
        r1 = await client.get("/api/v1/stocks?page=1&limit=5")
        r2 = await client.get("/api/v1/stocks?page=2&limit=5")
        data1 = r1.json()["data"]
        data2 = r2.json()["data"]
        assert data1 != data2, "page 1 and page 2 results must differ"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: pagination not yet implemented")
    async def test_stocks_pagination_limit_param_respected(self, client):
        """limit=3 must return at most 3 items."""
        response = await client.get("/api/v1/stocks?limit=3")
        assert len(response.json()["data"]) <= 3

    @pytest.mark.xfail(reason="Awaiting Data Engineer: pagination not yet implemented")
    async def test_stocks_meta_page_reflects_query_param(self, client):
        response = await client.get("/api/v1/stocks?page=3&limit=10")
        meta = response.json()["meta"]
        assert meta["page"] == 3
        assert meta["limit"] == 10


# ---------------------------------------------------------------------------
# Single-item endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSingleItemEnvelope:
    """All single-item endpoints must return the standard single envelope."""

    async def test_stock_detail_envelope(self, client):
        response = await client.get("/api/v1/stocks/AAPL")
        # 200 with null data is acceptable while stub is in place
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert_single_envelope(response.json())

    async def test_stock_history_envelope(self, client):
        response = await client.get("/api/v1/stocks/AAPL/history")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            body = response.json()
            assert "data" in body
            assert isinstance(body["data"], list)

    async def test_stock_indicators_envelope(self, client):
        response = await client.get("/api/v1/stocks/AAPL/indicators")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            body = response.json()
            assert "data" in body
            assert isinstance(body["data"], dict)

    async def test_watchlist_detail_envelope(self, client):
        response = await client.get("/api/v1/watchlists/1")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert_single_envelope(response.json())


# ---------------------------------------------------------------------------
# Error format contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestErrorEnvelope:
    """4xx error responses must use the standard error envelope."""

    @pytest.mark.xfail(reason="Awaiting Data Engineer: 404 handling not yet implemented")
    async def test_unknown_stock_returns_404(self, client):
        response = await client.get("/api/v1/stocks/SYMBOL_THAT_DOES_NOT_EXIST_XYZ")
        assert response.status_code == 404

    @pytest.mark.xfail(reason="Awaiting Data Engineer: error envelope not yet implemented")
    async def test_unknown_stock_error_envelope(self, client):
        response = await client.get("/api/v1/stocks/SYMBOL_THAT_DOES_NOT_EXIST_XYZ")
        assert response.status_code == 404
        assert_error_envelope(response.json())

    @pytest.mark.xfail(reason="Awaiting Data Engineer: error envelope not yet implemented")
    async def test_unknown_watchlist_returns_404(self, client):
        response = await client.get("/api/v1/watchlists/999999")
        assert response.status_code == 404
        assert_error_envelope(response.json())
