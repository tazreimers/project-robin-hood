from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BookmakerPairMetricRead(BaseModel):
    bookmaker_pair: list[str] = Field(default_factory=list)
    opportunities: int
    total_recommended_profit: Decimal
    average_margin: Decimal


class RecentActivityRead(BaseModel):
    id: int
    opportunity_id: int
    action_type: str
    notes: str | None
    created_at: datetime


class DashboardMetricsRead(BaseModel):
    total_opportunities_found: int
    opportunities_actioned: int
    expired_before_action: int
    total_recommended_profit: Decimal
    actual_profit_loss: Decimal
    average_margin: Decimal | None
    average_odds_age: Decimal | None
    best_bookmaker_pairs: list[BookmakerPairMetricRead] = Field(default_factory=list)
    recent_activity: list[RecentActivityRead] = Field(default_factory=list)
