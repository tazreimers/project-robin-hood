from app.config import get_settings
from app.jobs.fetch_odds import fetch_odds
from app.jobs.celery_app import celery_app


@celery_app.task(name="app.jobs.scan_odds.scan_odds")
def scan_odds() -> dict[str, str]:
    settings = get_settings()
    if not settings.odds_api_key:
        return {"status": "skipped", "reason": "ODDS_API_KEY is not configured"}

    result = fetch_odds.delay()
    return {"status": "queued", "task_id": result.id}
