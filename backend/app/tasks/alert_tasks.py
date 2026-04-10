"""Celery tasks for periodic alert evaluation."""

import asyncio
import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task context."""
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    name="app.tasks.alert_tasks.check_active_alerts",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_active_alerts(self):
    """Check all active alerts and mark triggered ones.

    Queries every alert where ``is_active = True``, evaluates each against
    current market data, and—when the condition is met—sets
    ``triggered_at = now()`` and ``is_active = False`` so the alert fires
    at most once until the user re-activates it.
    """
    try:
        _run_async(_async_check_active_alerts())
    except Exception as exc:
        logger.error("check_active_alerts failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _async_check_active_alerts() -> None:
    """Async implementation of check_active_alerts."""
    # Deferred imports keep Celery worker startup lightweight and avoid
    # circular import issues at module load time.
    from sqlalchemy import select

    from app.db.session import async_session
    from app.models.alert import Alert
    from app.services.alert_evaluator import AlertEvaluationError, AlertEvaluator
    from app.services.data_fetcher import StockDataFetcher
    from app.services.technical_analysis import TechnicalAnalyzer

    fetcher = StockDataFetcher()
    analyzer = TechnicalAnalyzer()
    evaluator = AlertEvaluator(fetcher, analyzer)

    async with async_session() as db:
        result = await db.execute(select(Alert).where(Alert.is_active.is_(True)))
        active_alerts: list[Alert] = list(result.scalars().all())

    logger.info("check_active_alerts: evaluating %d active alerts", len(active_alerts))

    triggered_count = 0
    for alert in active_alerts:
        try:
            triggered, current_value = await evaluator.evaluate(alert)
        except AlertEvaluationError as exc:
            logger.warning(
                "check_active_alerts: cannot evaluate alert id=%d symbol=%s — %s",
                alert.id,
                alert.symbol,
                exc,
            )
            continue
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "check_active_alerts: unexpected error for alert id=%d: %s",
                alert.id,
                exc,
                exc_info=True,
            )
            continue

        if triggered:
            async with async_session() as db:
                # Re-fetch inside the session to attach the instance.
                result = await db.execute(
                    select(Alert).where(Alert.id == alert.id)
                )
                db_alert = result.scalar_one_or_none()
                if db_alert is not None and db_alert.is_active:
                    db_alert.triggered_at = datetime.now(tz=timezone.utc)
                    db_alert.is_active = False
                    await db.commit()
                    triggered_count += 1
                    logger.info(
                        "Alert triggered: id=%d symbol=%s type=%s current_value=%.4f",
                        db_alert.id,
                        db_alert.symbol,
                        db_alert.alert_type,
                        current_value,
                    )

    logger.info(
        "check_active_alerts: done — %d/%d alerts triggered",
        triggered_count,
        len(active_alerts),
    )
