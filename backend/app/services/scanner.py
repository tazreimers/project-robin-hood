from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import ScanRun
from app.services.arbitrage import ArbitrageDetectionService
from app.services.odds_ingestion import OddsIngestionService
from app.services.providers import OddsProvider


@dataclass(frozen=True)
class ScanSummary:
    scan_id: int
    status: str
    sports_scanned: int
    events_processed: int
    markets_processed: int
    snapshots_saved: int
    opportunities_found: int
    started_at: datetime
    completed_at: datetime | None

    def as_dict(self) -> dict[str, object]:
        return {
            "scan_id": self.scan_id,
            "status": self.status,
            "sports_scanned": self.sports_scanned,
            "events_processed": self.events_processed,
            "markets_processed": self.markets_processed,
            "snapshots_saved": self.snapshots_saved,
            "opportunities_found": self.opportunities_found,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ScannerService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        provider: OddsProvider | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.provider = provider

    def create_scan_run(self, now: datetime | None = None) -> ScanRun:
        started_at = ensure_aware(now or datetime.now(timezone.utc))
        scan_run = ScanRun(
            status="queued",
            sports_scanned=0,
            events_processed=0,
            markets_processed=0,
            snapshots_saved=0,
            opportunities_found=0,
            started_at=started_at,
            completed_at=None,
        )
        self.db.add(scan_run)
        self.db.flush()
        return scan_run

    def mark_running(self, scan_run_id: int, now: datetime | None = None) -> ScanRun:
        scan_run = self.get_scan_run(scan_run_id)
        scan_run.status = "running"
        scan_run.error_message = None
        scan_run.started_at = ensure_aware(now or datetime.now(timezone.utc))
        scan_run.completed_at = None
        self.db.flush()
        return scan_run

    def run(self, scan_run_id: int) -> ScanSummary:
        scan_run = self.get_scan_run(scan_run_id)
        sport_keys = self.settings.sport_key_list
        if not sport_keys:
            raise ValueError("SPORT_KEYS is not configured")

        ingestion = OddsIngestionService(self.db, provider=self.provider).ingest_configured_sports(sport_keys)
        detection = ArbitrageDetectionService(self.db, settings=self.settings).detect()
        completed_at = datetime.now(timezone.utc)

        scan_run.status = "completed"
        scan_run.sports_scanned = len(sport_keys)
        scan_run.events_processed = ingestion.events_saved
        scan_run.markets_processed = ingestion.markets_saved
        scan_run.snapshots_saved = ingestion.snapshots_saved
        scan_run.opportunities_found = detection.opportunities_created
        scan_run.error_message = None
        scan_run.completed_at = completed_at
        self.db.flush()

        return self._summary_from_scan_run(scan_run)

    def mark_failed(self, scan_run_id: int, error: Exception, now: datetime | None = None) -> ScanRun:
        scan_run = self.get_scan_run(scan_run_id)
        scan_run.status = "failed"
        scan_run.error_message = str(error)[:1000]
        scan_run.completed_at = ensure_aware(now or datetime.now(timezone.utc))
        self.db.flush()
        return scan_run

    def get_scan_run(self, scan_run_id: int) -> ScanRun:
        scan_run = self.db.get(ScanRun, scan_run_id)
        if scan_run is None:
            raise ValueError(f"Scan run {scan_run_id} was not found")
        return scan_run

    def _summary_from_scan_run(self, scan_run: ScanRun) -> ScanSummary:
        return ScanSummary(
            scan_id=scan_run.id,
            status=scan_run.status,
            sports_scanned=scan_run.sports_scanned,
            events_processed=scan_run.events_processed,
            markets_processed=scan_run.markets_processed,
            snapshots_saved=scan_run.snapshots_saved,
            opportunities_found=scan_run.opportunities_found,
            started_at=ensure_aware(scan_run.started_at),
            completed_at=ensure_aware(scan_run.completed_at) if scan_run.completed_at else None,
        )


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
