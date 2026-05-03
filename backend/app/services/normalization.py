from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketAlias, TeamAlias
from app.providers.base import ProviderEvent

TEAM_FUZZY_THRESHOLD = 0.82
MARKET_FUZZY_THRESHOLD = 0.82
EVENT_START_TOLERANCE_SECONDS = 3 * 60 * 60
SPORT_KEY_ALIASES = {
    "afl": "aussierules_afl",
}


@dataclass(frozen=True)
class NormalizedTeam:
    source_name: str
    canonical_name: str
    confidence: float
    match_type: str


@dataclass(frozen=True)
class NormalizedMarket:
    provider: str
    source_market_name: str
    canonical_market_type: str
    confidence: float
    match_type: str


@dataclass(frozen=True)
class NormalizedEvent:
    sport_key: str
    home_team: NormalizedTeam
    away_team: NormalizedTeam
    start_time: datetime
    normalized_event_key: str
    confidence: float


@dataclass(frozen=True)
class EventMatch:
    matched: bool
    confidence: float
    normalized_event_key: str | None
    reason: str


class NormalizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def normalize_team_name(self, sport_key: str, team_name: str) -> NormalizedTeam:
        source_name = team_name.strip()
        aliases = self._team_aliases_for_sport(sport_key)

        for alias in aliases:
            if source_name == alias.alias:
                return NormalizedTeam(source_name, alias.canonical_name, 1.0, "exact_alias")

        cleaned_source = cleanup_text(source_name)
        for alias in aliases:
            if cleaned_source == cleanup_text(alias.alias):
                return NormalizedTeam(source_name, alias.canonical_name, 0.95, "cleaned_alias")

        best_alias: TeamAlias | None = None
        best_score = 0.0
        for alias in aliases:
            score = similarity(cleaned_source, cleanup_text(alias.alias))
            if score > best_score:
                best_alias = alias
                best_score = score

        if best_alias is not None and best_score >= TEAM_FUZZY_THRESHOLD:
            return NormalizedTeam(source_name, best_alias.canonical_name, round(best_score, 4), "fuzzy_alias")

        canonical_name = source_name or cleaned_source.title()
        return NormalizedTeam(source_name, canonical_name, 0.5 if canonical_name else 0.0, "fallback")

    def normalize_market_name(self, provider: str, source_market_name: str) -> NormalizedMarket:
        normalized_provider = provider_key(provider)
        source_name = source_market_name.strip()
        aliases = self._market_aliases_for_provider(normalized_provider)

        for alias in aliases:
            if source_name == alias.source_market_name:
                return NormalizedMarket(
                    normalized_provider,
                    source_name,
                    alias.canonical_market_type,
                    1.0,
                    "exact_alias",
                )

        cleaned_source = cleanup_text(source_name)
        for alias in aliases:
            if cleaned_source == cleanup_text(alias.source_market_name):
                return NormalizedMarket(
                    normalized_provider,
                    source_name,
                    alias.canonical_market_type,
                    0.95,
                    "cleaned_alias",
                )

        best_alias: MarketAlias | None = None
        best_score = 0.0
        for alias in aliases:
            score = similarity(cleaned_source, cleanup_text(alias.source_market_name))
            if score > best_score:
                best_alias = alias
                best_score = score

        if best_alias is not None and best_score >= MARKET_FUZZY_THRESHOLD:
            return NormalizedMarket(
                normalized_provider,
                source_name,
                best_alias.canonical_market_type,
                round(best_score, 4),
                "fuzzy_alias",
            )

        canonical_market_type = normalize_key_part(source_name).replace("-", "_")
        return NormalizedMarket(
            normalized_provider,
            source_name,
            canonical_market_type,
            0.5 if canonical_market_type else 0.0,
            "fallback",
        )

    def normalize_event(self, provider_event: ProviderEvent) -> NormalizedEvent:
        sport_key = canonical_sport_key(provider_event.sport_key)
        home_team = self.normalize_team_name(sport_key, provider_event.home_team)
        away_team = self.normalize_team_name(sport_key, provider_event.away_team)
        normalized_event_key = build_event_key(
            sport_key=sport_key,
            start_time=provider_event.start_time,
            team_names=[home_team.canonical_name, away_team.canonical_name],
        )
        confidence = round((home_team.confidence + away_team.confidence) / 2, 4)

        return NormalizedEvent(
            sport_key=sport_key,
            home_team=home_team,
            away_team=away_team,
            start_time=provider_event.start_time,
            normalized_event_key=normalized_event_key,
            confidence=confidence,
        )

    def normalize_event_key(self, provider_event: ProviderEvent) -> str:
        return self.normalize_event(provider_event).normalized_event_key

    def match_events(self, first: ProviderEvent, second: ProviderEvent) -> EventMatch:
        first_event = self.normalize_event(first)
        second_event = self.normalize_event(second)

        if first_event.normalized_event_key == second_event.normalized_event_key:
            confidence = round((first_event.confidence + second_event.confidence) / 2, 4)
            return EventMatch(True, confidence, first_event.normalized_event_key, "normalized_event_key")

        first_teams = {
            normalize_key_part(first_event.home_team.canonical_name),
            normalize_key_part(first_event.away_team.canonical_name),
        }
        second_teams = {
            normalize_key_part(second_event.home_team.canonical_name),
            normalize_key_part(second_event.away_team.canonical_name),
        }
        start_delta = abs((first_event.start_time - second_event.start_time).total_seconds())
        if first_teams == second_teams and start_delta <= EVENT_START_TOLERANCE_SECONDS:
            time_confidence = max(0.7, 1 - (start_delta / EVENT_START_TOLERANCE_SECONDS))
            confidence = round(((first_event.confidence + second_event.confidence) / 2) * time_confidence, 4)
            return EventMatch(True, confidence, first_event.normalized_event_key, "team_set_and_start_time")

        return EventMatch(False, 0.0, None, "teams_or_start_time_differ")

    def _team_aliases_for_sport(self, sport_key: str) -> list[TeamAlias]:
        sport_keys = {sport_key, canonical_sport_key(sport_key)}
        return list(
            self.db.scalars(
                select(TeamAlias)
                .where(TeamAlias.sport_key.in_(sport_keys))
                .order_by(TeamAlias.canonical_name, TeamAlias.alias)
            ).all()
        )

    def _market_aliases_for_provider(self, provider: str) -> list[MarketAlias]:
        return list(
            self.db.scalars(
                select(MarketAlias)
                .where(MarketAlias.provider == provider)
                .order_by(MarketAlias.canonical_market_type, MarketAlias.source_market_name)
            ).all()
        )


def canonical_sport_key(sport_key: str) -> str:
    cleaned_key = sport_key.strip()
    return SPORT_KEY_ALIASES.get(cleaned_key, cleaned_key)


def provider_key(provider: object) -> str:
    if isinstance(provider, str):
        return cleanup_key(provider)

    configured_name = getattr(provider, "provider_name", None)
    if configured_name:
        return cleanup_key(str(configured_name))

    class_name = provider.__class__.__name__
    snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    if snake_name.endswith("_provider"):
        snake_name = snake_name.removesuffix("_provider")
    return cleanup_key(snake_name)


def build_event_key(sport_key: str, start_time: datetime, team_names: list[str]) -> str:
    event_date = start_time.date().isoformat()
    teams = sorted(normalize_key_part(team_name) for team_name in team_names)
    return f"{canonical_sport_key(sport_key)}:{event_date}:{':'.join(teams)}"


def cleanup_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def cleanup_key(value: str) -> str:
    return cleanup_text(value).replace(" ", "_")


def normalize_key_part(value: str) -> str:
    return cleanup_text(value).replace(" ", "-")


def similarity(first: str, second: str) -> float:
    if not first or not second:
        return 0.0
    return SequenceMatcher(None, first, second).ratio()
