import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.jobs.celery_app import celery_app
from app.providers import OddsProviderConfigurationError
from app.services.scan_scheduler import ScanScheduler

logger = logging.getLogger(__name__)


@celery_app.task(name="app.jobs.adaptive_scan.adaptive_scan")
def adaptive_scan() -> dict[str, object]:
    settings = get_settings()

    if not settings.odds_api_key:
        return {"status": "skipped", "reason": "ODDS_API_KEY is not configured"}

    db = SessionLocal()
    try:
        summary = ScanScheduler(db, settings=settings).run_due_scan()
        db.commit()
    except OddsProviderConfigurationError as exc:
        db.rollback()
        return {"status": "skipped", "reason": str(exc)}
    except Exception:
        db.rollback()
        logger.exception("Adaptive scan failed")
        raise
    finally:
        db.close()

    logger.info(
        "Adaptive scan %s: due_events=%s sports=%s snapshots=%s opportunities=%s",
        summary.status,
        summary.events_due,
        summary.sports_scanned,
        summary.snapshots_saved,
        summary.opportunities_found,
    )
    return summary.as_dict()
