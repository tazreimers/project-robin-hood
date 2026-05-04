from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApiUsageLogRead(BaseModel):
    id: int
    provider: str
    endpoint: str
    sport_key: str | None
    regions: str
    markets: str
    requests_remaining: int | None
    requests_used: int | None
    requests_last: int | None
    estimated_cost: int
    captured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiUsageRead(BaseModel):
    latest_remaining_quota: int | None
    used_quota: int | None
    last_request_cost: int | None
    estimated_scans_remaining: int | None
    usage_logs: list[ApiUsageLogRead]
