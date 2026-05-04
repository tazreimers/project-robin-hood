import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.jobs.celery_app import celery_app
from app.services.odds_ingestion import OddsIngestionService
from app.services.quota_guard import QuotaGuard
from app.providers import OddsProviderConfigurationError

logger = logging.getLogger(__name__)


@celery_app.task(name="app.jobs.fetch_odds.fetch_odds")
def fetch_odds() -> dict[str, object]:
    settings = get_settings()

    if not settings.odds_api_key:
        return {"status": "skipped", "reason": "ODDS_API_KEY is not configured"}

    sport_keys = settings.sport_key_list

    if not sport_keys:
        return {"status": "skipped", "reason": "SPORT_KEYS is not configured"}

    db = SessionLocal()
    try:
        quota_guard = QuotaGuard(db, settings=settings)
        quota_decision = quota_guard.check_scan_allowed()
        if not quota_decision.allowed:
            return {"status": "blocked", "reason": quota_decision.reason or "Scan blocked by quota guard"}

        service = OddsIngestionService(db, quota_guard=quota_guard)
        summary = service.ingest_configured_sports(sport_keys)
        db.commit()
    except OddsProviderConfigurationError as exc:
        db.rollback()
        return {"status": "skipped", "reason": str(exc)}
    except Exception:
        db.rollback()
        logger.exception("Odds ingestion failed")
        raise
    finally:
        db.close()

    logger.info(
        "Fetched odds: events=%s markets=%s outcomes=%s snapshots=%s",
        summary.events_saved,
        summary.markets_saved,
        summary.outcomes_saved,
        summary.snapshots_saved,
    )

    return {
        "status": "completed",
        "sport_keys": sport_keys,
        **summary.as_dict(),
    }
