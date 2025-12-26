"""Celery application configuration."""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "poster_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.workers.tasks']  # ← CRITICAL: Import tasks module
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    broker_connection_retry_on_startup=True,  # Fix the warning
)

# Auto-discover tasks in the tasks module
celery_app.autodiscover_tasks(['app.workers'])