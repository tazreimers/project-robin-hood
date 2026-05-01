from datetime import datetime
from decimal import Decimal

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
    detected_at: datetime
    expires_at: datetime | None
    legs: list[ArbitrageLegRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
