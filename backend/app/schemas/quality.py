from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class MarketQualityCheckRead(BaseModel):
    id: int
    event_id: int
    market_type: str
    line: Decimal | None
    status: str
    confidence_score: Decimal
    reasons: dict[str, Any]
    checked_at: datetime

    model_config = ConfigDict(from_attributes=True)
