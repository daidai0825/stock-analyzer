"""Tests for CacheManager using fakeredis (no real Redis required)."""

import pytest
import fakeredis.aioredis as fakeredis

from app.core.cache import CacheManager, _TTL_DAILY, _TTL_REALTIME


@pytest.fixture
async def cache() -> CacheManager:
    """Return a CacheManager wired to an in-memory fakeredis server."""
    manager = CacheManager(redis_url="redis://localhost:6379/0")
    # Replace the real Redis client with a fake one.
    manager._client = fakeredis.FakeRedis(decode_responses=True)
    yield manager
    await manager.close()


# ---------------------------------------------------------------------------
# Low-level get / set / delete
# ---------------------------------------------------------------------------


class TestGetSetDelete:
    async def test_set_and_get_dict(self, cache):
        await cache.set("key1", {"foo": "bar"})
        result = await cache.get("key1")
        assert result == {"foo": "bar"}

    async def test_set_and_get_list(self, cache):
        data = [{"a": 1}, {"b": 2}]
        await cache.set("list_key", data)
        result = await cache.get("list_key")
        assert result == data

    async def test_get_missing_key_returns_none(self, cache):
        result = await cache.get("nonexistent")
        assert result is None

    async def test_delete_removes_key(self, cache):
        await cache.set("to_delete", {"x": 1})
        await cache.delete("to_delete")
        result = await cache.get("to_delete")
        assert result is None

    async def test_delete_nonexistent_key_no_error(self, cache):
        # Should not raise
        await cache.delete("never_existed")

    async def test_set_with_custom_ttl(self, cache):
        await cache.set("ttl_key", {"v": 42}, ttl=10)
        result = await cache.get("ttl_key")
        assert result == {"v": 42}
        # Verify TTL was applied by fakeredis
        ttl = await cache.client.ttl("ttl_key")
        assert 0 < ttl <= 10

    async def test_exists_true_for_set_key(self, cache):
        await cache.set("exists_key", {"y": 1})
        assert await cache.exists("exists_key") is True

    async def test_exists_false_for_missing_key(self, cache):
        assert await cache.exists("not_here") is False

    async def test_set_serialises_non_string_values(self, cache):
        """Non-string values (int, float, None) should round-trip via JSON."""
        await cache.set("numeric", 12345)
        assert await cache.get("numeric") == 12345

        await cache.set("float_val", 3.14)
        assert abs(await cache.get("float_val") - 3.14) < 1e-9


# ---------------------------------------------------------------------------
# Stock-data helpers
# ---------------------------------------------------------------------------


class TestStockDataHelpers:
    async def test_set_and_get_stock_data(self, cache):
        records = [
            {"date": "2024-01-02", "open": 100.0, "close": 103.0, "volume": 1_000_000}
        ]
        await cache.set_stock_data("AAPL", "1y", records)
        result = await cache.get_stock_data("AAPL", "1y")
        assert result == records

    async def test_get_stock_data_missing_returns_none(self, cache):
        result = await cache.get_stock_data("TSLA", "6mo")
        assert result is None

    async def test_stock_key_is_uppercase_normalised(self, cache):
        records = [{"date": "2024-01-02"}]
        await cache.set_stock_data("aapl", "1y", records)
        # Lower-case and upper-case lookups should resolve to the same key.
        assert await cache.get_stock_data("AAPL", "1y") == records
        assert await cache.get_stock_data("aapl", "1y") == records

    async def test_default_ttl_is_one_hour(self, cache):
        await cache.set_stock_data("MSFT", "1y", [{"date": "2024-01-02"}])
        ttl = await cache.client.ttl(CacheManager._stock_key("MSFT", "1y"))
        assert 3500 <= ttl <= _TTL_DAILY

    async def test_custom_ttl_applied(self, cache):
        await cache.set_stock_data("NVDA", "1d", [{}], ttl=60)
        ttl = await cache.client.ttl(CacheManager._stock_key("NVDA", "1d"))
        assert 0 < ttl <= 60

    async def test_invalidate_stock_removes_all_periods(self, cache):
        await cache.set_stock_data("2330", "1y", [{"date": "2024-01-02"}])
        await cache.set_stock_data("2330", "6mo", [{"date": "2024-01-02"}])
        await cache.invalidate_stock("2330")
        assert await cache.get_stock_data("2330", "1y") is None
        assert await cache.get_stock_data("2330", "6mo") is None

    async def test_invalidate_stock_does_not_affect_other_symbols(self, cache):
        await cache.set_stock_data("AAPL", "1y", [{"v": 1}])
        await cache.set_stock_data("GOOG", "1y", [{"v": 2}])
        await cache.invalidate_stock("AAPL")
        assert await cache.get_stock_data("GOOG", "1y") == [{"v": 2}]


# ---------------------------------------------------------------------------
# Close / lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    async def test_close_resets_client(self, cache):
        # Ensure client is initialised first
        _ = cache.client
        assert cache._client is not None
        await cache.close()
        assert cache._client is None

    async def test_close_idempotent(self, cache):
        await cache.close()
        await cache.close()  # second close should not raise
