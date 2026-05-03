import logging

from app.db import SessionLocal
from app.jobs.celery_app import celery_app
from app.services.arbitrage import ArbitrageDetectionService

logger = logging.getLogger(__name__)


@celery_app.task(name="app.jobs.detect_arbitrage.detect_arbitrage")
def detect_arbitrage() -> dict[str, object]:
    db = SessionLocal()
    try:
        service = ArbitrageDetectionService(db)
        summary = service.detect()
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Arbitrage detection failed")
        raise
    finally:
        db.close()

    logger.info(
        "Detected arbitrage: opportunities=%s legs=%s markets_checked=%s",
        summary.opportunities_created,
        summary.legs_created,
        summary.markets_checked,
    )

    return {
        "status": "completed",
        **summary.as_dict(),
    }
