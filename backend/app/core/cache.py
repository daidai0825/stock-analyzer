"""Redis-backed cache manager for stock data."""

import json
import logging
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Default TTLs (seconds)
_TTL_REALTIME = 300      # 5 minutes — quotes that change frequently
_TTL_DAILY = 3_600       # 1 hour   — end-of-day / historical bars


class CacheManager:
    """Async Redis cache with configurable TTL.

    All values are JSON-serialised before storage and deserialised on
    retrieval.  Keys that do not exist (or have expired) return ``None``.

    Usage::

        cache = CacheManager(settings.redis_url)
        await cache.set("key", {"foo": "bar"}, ttl=60)
        value = await cache.get("key")
        await cache.delete("key")

        # Convenience wrappers for stock price lists
        await cache.set_stock_data("AAPL", "1y", records, ttl=3600)
        records = await cache.get_stock_data("AAPL", "1y")
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        # Lazy connection: created on first use via _client property.
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    # ------------------------------------------------------------------
    # Low-level primitives
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Any | None:
        """Return the deserialised value for *key*, or ``None`` if absent."""
        try:
            raw = await self.client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Cache GET failed for key=%s: %s", key, exc)
            return None

    async def set(self, key: str, value: Any, ttl: int = _TTL_REALTIME) -> None:
        """Serialise *value* as JSON and store under *key* with the given TTL.

        Args:
            key:   Redis key string.
            value: Any JSON-serialisable object.
            ttl:   Time-to-live in seconds (default: 5 minutes).
        """
        try:
            serialised = json.dumps(value, default=str)
            await self.client.setex(key, ttl, serialised)
        except Exception as exc:
            logger.warning("Cache SET failed for key=%s: %s", key, exc)

    async def delete(self, key: str) -> None:
        """Remove *key* from cache (no-op if absent)."""
        try:
            await self.client.delete(key)
        except Exception as exc:
            logger.warning("Cache DELETE failed for key=%s: %s", key, exc)

    async def exists(self, key: str) -> bool:
        """Return True when *key* exists in cache."""
        try:
            return bool(await self.client.exists(key))
        except Exception as exc:
            logger.warning("Cache EXISTS failed for key=%s: %s", key, exc)
            return False

    # ------------------------------------------------------------------
    # Stock-data convenience helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _stock_key(symbol: str, period: str) -> str:
        return f"stock:{symbol.upper()}:{period}"

    async def get_stock_data(
        self, symbol: str, period: str
    ) -> list[dict] | None:
        """Return cached OHLCV records for *symbol*/*period*, or ``None``.

        Args:
            symbol: Ticker symbol (e.g. "AAPL", "2330").
            period: Period string (e.g. "1y", "6mo").
        """
        return await self.get(self._stock_key(symbol, period))

    async def set_stock_data(
        self,
        symbol: str,
        period: str,
        data: list[dict],
        ttl: int = _TTL_DAILY,
    ) -> None:
        """Cache *data* OHLCV records for *symbol*/*period*.

        Args:
            symbol: Ticker symbol.
            period: Period string.
            data:   List of OHLCV dicts as returned by StockDataFetcher.
            ttl:    Time-to-live in seconds (default: 1 hour).
        """
        await self.set(self._stock_key(symbol, period), data, ttl=ttl)

    async def invalidate_stock(self, symbol: str) -> None:
        """Remove all cached periods for *symbol* using SCAN + DELETE."""
        pattern = f"stock:{symbol.upper()}:*"
        try:
            cursor = 0
            while True:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning(
                "Cache invalidate_stock failed for symbol=%s: %s", symbol, exc
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying Redis connection pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
