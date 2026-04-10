"""Celery application factory and beat schedule configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "stock_analyzer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.data_tasks", "app.tasks.alert_tasks"],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="Asia/Taipei",
    enable_utc=True,
    # Retry defaults
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat schedule
    beat_schedule={
        # Fetch latest daily prices at 18:00 Taipei time, after TW market close
        # (TW closes at 13:30; US close handled by separate offset if needed).
        "fetch-daily-prices": {
            "task": "app.tasks.data_tasks.fetch_daily_prices",
            "schedule": crontab(hour=18, minute=0),
            "options": {"expires": 3600},
        },
        # Clean expired cache entries every 6 hours.
        "cleanup-old-cache": {
            "task": "app.tasks.data_tasks.cleanup_old_cache",
            "schedule": crontab(minute=0, hour="*/6"),
            "options": {"expires": 1800},
        },
        # Evaluate all active alerts every 15 minutes.
        "check-alerts": {
            "task": "app.tasks.alert_tasks.check_active_alerts",
            "schedule": crontab(minute="*/15"),
            "options": {"expires": 600},
        },
    },
)
