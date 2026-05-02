from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BookmakerRead(BaseModel):
    id: int
    name: str
    region: str
    api_key_name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SportRead(BaseModel):
    id: int
    key: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventRead(BaseModel):
    id: int
    external_id: str
    sport_id: int
    home_team: str
    away_team: str
    start_time: datetime
    normalized_event_key: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketRead(BaseModel):
    id: int
    event_id: int
    bookmaker_id: int
    market_type: str
    line: Decimal | None
    is_live: bool
    is_suspended: bool
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutcomeRead(BaseModel):
    id: int
    market_id: int
    outcome_name: str
    decimal_odds: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OddsSnapshotRead(BaseModel):
    id: int
    event_id: int
    bookmaker_id: int
    market_type: str
    line: Decimal | None
    outcome_name: str
    decimal_odds: Decimal
    captured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArbitrageLegRead(BaseModel):
    id: int
    opportunity_id: int
    bookmaker_id: int
    outcome_name: str
    decimal_odds: Decimal
    stake: Decimal
    expected_return: Decimal

    model_config = ConfigDict(from_attributes=True)


class ArbitrageOpportunityRead(BaseModel):
    id: int
    event_id: int
    market_type: str
    line: Decimal | None
    implied_probability_total: Decimal
    margin: Decimal
    total_stake: Decimal
    guaranteed_return: Decimal
    guaranteed_profit: Decimal
    status: str
    reliability_score: Decimal
    validation_status: str
    validation_reasons: dict[str, Any]
    last_validated_at: datetime | None
    detected_at: datetime
    expires_at: datetime | None
    legs: list[ArbitrageLegRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ActiveArbitrageLegRead(BaseModel):
    id: int
    bookmaker: BookmakerRead
    outcome_name: str
    decimal_odds: Decimal
    stake: Decimal
    expected_return: Decimal

    model_config = ConfigDict(from_attributes=True)


class ActiveArbitrageOpportunityRead(BaseModel):
    id: int
    event: EventRead
    market_type: str
    line: Decimal | None
    implied_probability_total: Decimal
    margin: Decimal
    total_stake: Decimal
    guaranteed_profit: Decimal
    guaranteed_return: Decimal
    detected_at: datetime
    latest_snapshot_at: datetime | None
    odds_age_seconds: int | None
    freshness_status: str
    reliability_score: Decimal
    validation_status: str
    validation_reasons: dict[str, Any]
    last_validated_at: datetime | None
    legs: list[ActiveArbitrageLegRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OpportunityInstructionLegRead(BaseModel):
    id: int
    bookmaker: BookmakerRead
    outcome_name: str
    decimal_odds: Decimal
    stake: Decimal
    expected_return: Decimal
    source_last_seen_at: datetime | None
    odds_age_seconds: int | None
    instruction: str

    model_config = ConfigDict(from_attributes=True)


class OpportunityInstructionsRead(BaseModel):
    id: int
    event: EventRead
    market: str
    line: Decimal | None
    total_stake: Decimal
    guaranteed_profit: Decimal
    guaranteed_return: Decimal
    margin: Decimal
    legs: list[OpportunityInstructionLegRead] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    warning: str

    model_config = ConfigDict(from_attributes=True)
