"""Contract tests for the /api/v1/watchlists endpoints.

Shape tests pass against the current stub implementation.
Tests that depend on persistence are marked xfail.
"""

import pytest


# ---------------------------------------------------------------------------
# GET /api/v1/watchlists  (list)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestListWatchlistsContract:
    async def test_returns_200(self, client):
        response = await client.get("/api/v1/watchlists")
        assert response.status_code == 200

    async def test_response_has_data_key(self, client):
        body = (await client.get("/api/v1/watchlists")).json()
        assert "data" in body

    async def test_data_is_list(self, client):
        body = (await client.get("/api/v1/watchlists")).json()
        assert isinstance(body["data"], list)

    async def test_response_has_meta_key(self, client):
        body = (await client.get("/api/v1/watchlists")).json()
        assert "meta" in body

    async def test_meta_has_required_integer_fields(self, client):
        meta = (await client.get("/api/v1/watchlists")).json()["meta"]
        for field in ("total", "page", "limit"):
            assert field in meta, f"meta missing '{field}'"
            assert isinstance(meta[field], int), f"meta.{field} must be int"


# ---------------------------------------------------------------------------
# POST /api/v1/watchlists  (create)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreateWatchlistContract:
    async def test_create_returns_200_or_201(self, client, sample_watchlist_payload):
        """POST must return 200 or 201 (stub currently returns 200 with null data)."""
        response = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        assert response.status_code in (200, 201)

    async def test_create_response_has_data_key(self, client, sample_watchlist_payload):
        response = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        if response.status_code in (200, 201):
            assert "data" in response.json()

    @pytest.mark.xfail(reason="Awaiting Data Engineer: watchlist persistence not implemented")
    async def test_create_returns_non_null_data(self, client, sample_watchlist_payload):
        response = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        assert response.status_code in (200, 201)
        assert response.json()["data"] is not None

    @pytest.mark.xfail(reason="Awaiting Data Engineer: watchlist persistence not implemented")
    async def test_created_watchlist_has_required_fields(
        self, client, sample_watchlist_payload
    ):
        response = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        data = response.json()["data"]
        for field in ("id", "name", "symbols"):
            assert field in data, f"created watchlist missing '{field}'"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: watchlist persistence not implemented")
    async def test_created_watchlist_name_matches_payload(
        self, client, sample_watchlist_payload
    ):
        response = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        assert response.json()["data"]["name"] == sample_watchlist_payload["name"]

    @pytest.mark.xfail(reason="Awaiting Data Engineer: watchlist persistence not implemented")
    async def test_created_watchlist_symbols_match_payload(
        self, client, sample_watchlist_payload
    ):
        response = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        assert response.json()["data"]["symbols"] == sample_watchlist_payload["symbols"]

    @pytest.mark.xfail(reason="Awaiting Data Engineer: watchlist id is auto-assigned")
    async def test_created_watchlist_id_is_integer(self, client, sample_watchlist_payload):
        response = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        assert isinstance(response.json()["data"]["id"], int)


# ---------------------------------------------------------------------------
# GET /api/v1/watchlists/{id}  (detail)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetWatchlistContract:
    async def test_returns_200_or_404(self, client):
        """Stub returns 200 with null data; 404 is also valid for unresolved ID."""
        response = await client.get("/api/v1/watchlists/1")
        assert response.status_code in (200, 404)

    async def test_200_response_has_data_key(self, client):
        response = await client.get("/api/v1/watchlists/1")
        if response.status_code == 200:
            assert "data" in response.json()

    @pytest.mark.xfail(reason="Awaiting Data Engineer: watchlist persistence not implemented")
    async def test_existing_id_returns_watchlist(self, client, sample_watchlist_payload):
        """Create then retrieve; the retrieved item must match."""
        create_resp = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        wl_id = create_resp.json()["data"]["id"]
        get_resp = await client.get(f"/api/v1/watchlists/{wl_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["id"] == wl_id

    @pytest.mark.xfail(reason="Awaiting Data Engineer: 404 handling not implemented")
    async def test_nonexistent_id_returns_404(self, client):
        response = await client.get("/api/v1/watchlists/999999")
        assert response.status_code == 404

    @pytest.mark.xfail(reason="Awaiting Data Engineer: error envelope not implemented")
    async def test_nonexistent_id_error_has_detail(self, client):
        response = await client.get("/api/v1/watchlists/999999")
        assert "detail" in response.json()


# ---------------------------------------------------------------------------
# PUT /api/v1/watchlists/{id}  (update)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestUpdateWatchlistContract:
    async def test_returns_200_or_404(self, client):
        response = await client.put("/api/v1/watchlists/1", json={"name": "Updated"})
        assert response.status_code in (200, 404)

    async def test_200_response_has_data_key(self, client):
        response = await client.put("/api/v1/watchlists/1", json={"name": "Updated"})
        if response.status_code == 200:
            assert "data" in response.json()

    @pytest.mark.xfail(reason="Awaiting Data Engineer: watchlist update not implemented")
    async def test_update_changes_watchlist_name(self, client, sample_watchlist_payload):
        create_resp = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        wl_id = create_resp.json()["data"]["id"]
        update_resp = await client.put(
            f"/api/v1/watchlists/{wl_id}", json={"name": "Renamed List"}
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["name"] == "Renamed List"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: 404 handling not implemented")
    async def test_update_nonexistent_id_returns_404(self, client):
        response = await client.put("/api/v1/watchlists/999999", json={"name": "Ghost"})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/watchlists/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeleteWatchlistContract:
    async def test_returns_200_or_204_or_404(self, client):
        response = await client.delete("/api/v1/watchlists/1")
        assert response.status_code in (200, 204, 404)

    async def test_200_response_shape(self, client):
        """Stub returns {"detail": "deleted"}; both that and {"data": ...} are acceptable."""
        response = await client.delete("/api/v1/watchlists/1")
        if response.status_code == 200:
            body = response.json()
            # Accept either confirmation shapes
            has_confirmation = "detail" in body or "data" in body
            assert has_confirmation, "DELETE 200 must have 'detail' or 'data' key"

    @pytest.mark.xfail(reason="Awaiting Data Engineer: delete + 404 not implemented")
    async def test_delete_then_get_returns_404(self, client, sample_watchlist_payload):
        """After deletion, fetching the same ID must return 404."""
        create_resp = await client.post("/api/v1/watchlists", json=sample_watchlist_payload)
        wl_id = create_resp.json()["data"]["id"]
        await client.delete(f"/api/v1/watchlists/{wl_id}")
        get_resp = await client.get(f"/api/v1/watchlists/{wl_id}")
        assert get_resp.status_code == 404

    @pytest.mark.xfail(reason="Awaiting Data Engineer: 404 handling not implemented")
    async def test_delete_nonexistent_id_returns_404(self, client):
        response = await client.delete("/api/v1/watchlists/999999")
        assert response.status_code == 404
