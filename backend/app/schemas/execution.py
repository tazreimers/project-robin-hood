from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.odds import BookmakerRead


class OpportunityExecutionCreate(BaseModel):
    notes: str | None = None


class OpportunityExecutionPatch(BaseModel):
    status: str | None = None
    notes: str | None = None


class ExecutionLegPatch(BaseModel):
    actual_odds: Decimal | None = None
    actual_stake: Decimal | None = None
    status: str | None = None
    notes: str | None = None


class ExecutionLegRead(BaseModel):
    id: int
    execution_id: int
    bookmaker_id: int
    bookmaker: BookmakerRead
    outcome_name: str
    recommended_odds: Decimal
    actual_odds: Decimal | None
    recommended_stake: Decimal
    actual_stake: Decimal | None
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunityExecutionRead(BaseModel):
    id: int
    opportunity_id: int
    status: str
    total_stake_planned: Decimal
    total_stake_actual: Decimal
    expected_profit: Decimal
    actual_profit: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    legs: list[ExecutionLegRead]

    model_config = ConfigDict(from_attributes=True)
