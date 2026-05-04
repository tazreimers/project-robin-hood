from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanPriorityEventRead(BaseModel):
    id: int
    home_team: str
    away_team: str
    start_time: datetime

    model_config = ConfigDict(from_attributes=True)


class EventScanPriorityRead(BaseModel):
    id: int
    event_id: int
    sport_key: str
    priority_level: str
    next_scan_at: datetime | None
    last_scan_at: datetime | None
    reason: str
    created_at: datetime
    updated_at: datetime
    event: ScanPriorityEventRead

    model_config = ConfigDict(from_attributes=True)
