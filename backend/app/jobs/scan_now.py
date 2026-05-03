import logging

from app.db.session import SessionLocal
from app.jobs.celery_app import celery_app
from app.services.scanner import ScannerService

logger = logging.getLogger(__name__)


@celery_app.task(name="app.jobs.scan_now.scan_now")
def scan_now(scan_run_id: int) -> dict[str, object]:
    db = SessionLocal()
    service = ScannerService(db)

    try:
        service.mark_running(scan_run_id)
        db.commit()
        summary = service.run(scan_run_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        failed_run = service.mark_failed(scan_run_id, exc)
        db.commit()
        logger.exception("Scan failed: scan_run_id=%s", scan_run_id)
        return {
            "scan_id": failed_run.id,
            "status": failed_run.status,
            "error_message": failed_run.error_message,
        }
    finally:
        db.close()

    logger.info(
        "Scan completed: scan_run_id=%s events=%s markets=%s snapshots=%s opportunities=%s",
        summary.scan_id,
        summary.events_processed,
        summary.markets_processed,
        summary.snapshots_saved,
        summary.opportunities_found,
    )

    return summary.as_dict()
