# Celery task package.
# Importing celery_app here ensures beat schedule is registered when
# the worker starts with `celery -A app.tasks worker`.
from app.core.celery_app import celery_app  # noqa: F401
