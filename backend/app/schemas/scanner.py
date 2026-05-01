from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanRunRead(BaseModel):
    id: int
    scan_id: int
    status: str
    sports_scanned: int
    events_processed: int
    markets_processed: int
    snapshots_saved: int
    opportunities_found: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
