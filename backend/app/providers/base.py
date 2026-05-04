from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


class OddsProviderError(Exception):
    """Base exception for provider failures."""


class OddsProviderConfigurationError(OddsProviderError):
    """Raised when a provider is missing required configuration."""


@dataclass(frozen=True)
class ProviderApiUsage:
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


@dataclass(frozen=True)
class ProviderSport:
    key: str
    name: str
    is_active: bool


@dataclass(frozen=True)
class ProviderOutcome:
    name: str
    decimal_odds: Decimal
    is_suspended: bool = False


@dataclass(frozen=True)
class ProviderMarket:
    market_type: str
    outcomes: list[ProviderOutcome] = field(default_factory=list)
    line: Decimal | None = None
    is_live: bool = False
    is_suspended: bool = False


@dataclass(frozen=True)
class ProviderBookmaker:
    key: str
    name: str
    region: str
    markets: list[ProviderMarket] = field(default_factory=list)
    last_update: datetime | None = None


@dataclass(frozen=True)
class ProviderEvent:
    external_id: str
    sport_key: str
    sport_name: str
    home_team: str
    away_team: str
    start_time: datetime
    bookmakers: list[ProviderBookmaker] = field(default_factory=list)


class OddsProvider(ABC):
    @abstractmethod
    def fetch_sports(self) -> list[ProviderSport]:
        raise NotImplementedError

    @abstractmethod
    def fetch_odds(self, sport_key: str) -> list[ProviderEvent]:
        raise NotImplementedError
