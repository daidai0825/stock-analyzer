"""Contract tests for the health-check endpoint.

These tests verify the exact shape and values that the /api/health endpoint
must always return.  No data-engineer implementation is required for these
to pass.
"""

import pytest


@pytest.mark.asyncio
class TestHealthContract:
    async def test_health_returns_200(self, client):
        """Health endpoint must respond with HTTP 200."""
        response = await client.get("/api/health")
        assert response.status_code == 200

    async def test_health_response_shape(self, client):
        """Health endpoint must return exactly {"status": "ok"}."""
        response = await client.get("/api/health")
        body = response.json()
        assert "status" in body, "response must contain 'status' key"
        assert body["status"] == "ok"

    async def test_health_content_type_is_json(self, client):
        """Health endpoint must respond with application/json."""
        response = await client.get("/api/health")
        assert "application/json" in response.headers.get("content-type", "")
