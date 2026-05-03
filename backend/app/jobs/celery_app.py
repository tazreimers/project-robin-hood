from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

celery_app = Celery(
    "project_robin_hood",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.jobs.detect_arbitrage", "app.jobs.fetch_odds", "app.jobs.scan_now", "app.jobs.scan_odds"],
)

celery_app.conf.update(
    accept_content=["json"],
    result_serializer="json",
    task_serializer="json",
    timezone="UTC",
)
