from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "project_robin_hood",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.jobs.fetch_odds", "app.jobs.scan_odds"],
)

celery_app.conf.update(
    accept_content=["json"],
    result_serializer="json",
    task_serializer="json",
    timezone="UTC",
)
