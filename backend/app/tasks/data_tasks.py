"""Celery tasks for periodic data fetching and cache maintenance."""

import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    name="app.tasks.data_tasks.fetch_daily_prices",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes between retries
)
def fetch_daily_prices(self):
    """Fetch latest daily prices for all tracked stocks.

    Queries the ``stocks`` table for every persisted symbol, fetches the most
    recent OHLCV bar from the appropriate data source (yfinance or FinMind),
    and bulk-upserts it into ``daily_prices``.

    This task is scheduled to run at 18:00 Taipei time (after TW market close
    at 13:30 and close enough to US pre-market open to capture the previous
    US session's data).
    """
    try:
        _run_async(_async_fetch_daily_prices())
    except Exception as exc:
        logger.error("fetch_daily_prices failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _async_fetch_daily_prices() -> None:
    """Async implementation of fetch_daily_prices."""
    # Deferred imports to avoid circular imports at module load time and to
    # keep the Celery worker startup lightweight.
    from sqlalchemy import select

    from app.db.session import async_session
    from app.models.stock import Stock
    from app.services.data_fetcher import StockDataFetcher
    from app.services.data_processor import DataProcessor

    fetcher = StockDataFetcher()
    processor = DataProcessor()

    async with async_session() as db:
        result = await db.execute(select(Stock.symbol, Stock.market))
        stocks = result.all()

    logger.info("fetch_daily_prices: processing %d symbols", len(stocks))

    for symbol, market in stocks:
        try:
            # Fetch only 5 days to get the most recent session efficiently.
            records = await fetcher.fetch_history(symbol, period="5d", interval="1d")
            if records:
                async with async_session() as db:
                    saved = await processor.process_and_store(symbol, records, db)
                    logger.debug(
                        "fetch_daily_prices: symbol=%s saved=%d rows", symbol, saved
                    )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "fetch_daily_prices: error processing symbol=%s: %s", symbol, exc
            )
            # Continue with remaining symbols rather than aborting the whole task.


@celery_app.task(
    name="app.tasks.data_tasks.cleanup_old_cache",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def cleanup_old_cache(self):
    """Clean expired cache entries from Redis.

    Redis TTL-based expiry handles most cleanup automatically.  This task
    provides an explicit sweep for any leaked keys (e.g. keys written without
    TTL) by scanning for the ``stock:*`` namespace and removing entries whose
    associated data is stale.

    Currently this simply logs a heartbeat; extend with pattern-based SCAN +
    DELETE logic when non-TTL keys are introduced.
    """
    try:
        _run_async(_async_cleanup_old_cache())
    except Exception as exc:
        logger.error("cleanup_old_cache failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _async_cleanup_old_cache() -> None:
    """Async implementation of cleanup_old_cache."""
    from app.core.cache import CacheManager
    from app.core.config import settings

    cache = CacheManager(settings.redis_url)
    try:
        # Redis TTL handles expiry automatically for keys written via
        # CacheManager.set / set_stock_data.  Force-sweep any keyless
        # patterns that might have accumulated without TTL.
        pattern = "stock:*:max"
        client = cache.client
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=200)
            if keys:
                await client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        logger.info("cleanup_old_cache: removed %d stale 'max' period keys", deleted)
    finally:
        await cache.close()
