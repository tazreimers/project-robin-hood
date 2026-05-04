from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bookmaker, Event, Market, OddsSnapshot, Outcome, Sport
from app.services.normalization import NormalizationService, NormalizedEvent, provider_key
from app.providers import OddsProvider, ProviderBookmaker, ProviderEvent, ProviderMarket, ProviderSport
from app.providers.the_odds_api import TheOddsApiProvider
from app.services.quota_guard import QuotaGuard

DECIMAL_ODDS_PRECISION = Decimal("0.0001")
LINE_PRECISION = Decimal("0.0001")


@dataclass
class IngestionSummary:
    sports_saved: int = 0
    bookmakers_saved: int = 0
    events_saved: int = 0
    markets_saved: int = 0
    outcomes_saved: int = 0
    snapshots_saved: int = 0

    def merge(self, other: IngestionSummary) -> None:
        self.sports_saved += other.sports_saved
        self.bookmakers_saved += other.bookmakers_saved
        self.events_saved += other.events_saved
        self.markets_saved += other.markets_saved
        self.outcomes_saved += other.outcomes_saved
        self.snapshots_saved += other.snapshots_saved

    def as_dict(self) -> dict[str, int]:
        return {
            "sports_saved": self.sports_saved,
            "bookmakers_saved": self.bookmakers_saved,
            "events_saved": self.events_saved,
            "markets_saved": self.markets_saved,
            "outcomes_saved": self.outcomes_saved,
            "snapshots_saved": self.snapshots_saved,
        }


class OddsIngestionService:
    def __init__(
        self,
        db: Session,
        provider: OddsProvider | None = None,
        quota_guard: QuotaGuard | None = None,
    ) -> None:
        self.db = db
        self.provider = provider or TheOddsApiProvider(
            usage_callback=quota_guard.log_api_response if quota_guard else None,
        )
        self.provider_name = provider_key(self.provider)
        self.normalizer = NormalizationService(db)

    def fetch_sports(self) -> list[ProviderSport]:
        return self.provider.fetch_sports()

    def fetch_upcoming_events(self, sport_key: str) -> list[ProviderEvent]:
        now = datetime.now(timezone.utc)
        return [event for event in self.provider.fetch_odds(sport_key) if event.start_time > now]

    def fetch_odds(self, sport_key: str) -> list[ProviderEvent]:
        return self.provider.fetch_odds(sport_key)

    def ingest_sports(self) -> IngestionSummary:
        summary = IngestionSummary()

        for provider_sport in self.fetch_sports():
            sport = self._get_sport(provider_sport.key)
            if sport is None:
                sport = Sport(key=provider_sport.key, name=provider_sport.name, is_active=provider_sport.is_active)
                self.db.add(sport)
            else:
                sport.name = provider_sport.name
                sport.is_active = provider_sport.is_active

            summary.sports_saved += 1

        self.db.flush()
        return summary

    def ingest_configured_sports(self, sport_keys: list[str]) -> IngestionSummary:
        summary = self.ingest_sports()

        for sport_key in sport_keys:
            summary.merge(self.ingest_sport_odds(sport_key))

        self.db.flush()
        return summary

    def ingest_sport_odds(self, sport_key: str) -> IngestionSummary:
        summary = IngestionSummary()
        captured_at = datetime.now(timezone.utc)

        for provider_event in self.fetch_upcoming_events(sport_key):
            normalized_event = self.normalizer.normalize_event(provider_event)
            sport = self._get_or_create_sport(provider_event, normalized_event.sport_key)
            event = self._upsert_event(provider_event, normalized_event, sport)
            summary.events_saved += 1

            for provider_bookmaker in provider_event.bookmakers:
                bookmaker = self._upsert_bookmaker(provider_bookmaker)
                summary.bookmakers_saved += 1

                for provider_market in provider_bookmaker.markets:
                    normalized_market = self.normalizer.normalize_market_name(
                        self.provider_name,
                        provider_market.market_type,
                    )
                    if not self._should_store_market(provider_market, normalized_market.canonical_market_type):
                        continue

                    valid_outcomes = [
                        (
                            self._normalize_outcome_name(
                                normalized_event.sport_key,
                                normalized_market.canonical_market_type,
                                provider_outcome.name,
                            ),
                            decimal_odds,
                        )
                        for provider_outcome in provider_market.outcomes
                        if not provider_outcome.is_suspended
                        for decimal_odds in [normalize_decimal_odds(provider_outcome.decimal_odds)]
                        if decimal_odds is not None
                    ]
                    if not valid_outcomes:
                        continue

                    market = self._upsert_market(
                        event,
                        bookmaker,
                        provider_market,
                        provider_bookmaker,
                        normalized_market.canonical_market_type,
                        captured_at,
                    )
                    summary.markets_saved += 1

                    for outcome_name, decimal_odds in valid_outcomes:
                        self._upsert_outcome(market, outcome_name, decimal_odds)
                        self.db.add(
                            OddsSnapshot(
                                event_id=event.id,
                                bookmaker_id=bookmaker.id,
                                market_type=normalized_market.canonical_market_type,
                                line=normalize_line(provider_market.line),
                                outcome_name=outcome_name,
                                decimal_odds=decimal_odds,
                                captured_at=captured_at,
                            )
                        )
                        summary.outcomes_saved += 1
                        summary.snapshots_saved += 1

        self.db.flush()
        return summary

    def _get_sport(self, sport_key: str) -> Sport | None:
        return self.db.scalar(select(Sport).where(Sport.key == sport_key))

    def _get_or_create_sport(self, provider_event: ProviderEvent, sport_key: str) -> Sport:
        sport = self._get_sport(sport_key)
        if sport is None:
            sport = Sport(key=sport_key, name=provider_event.sport_name, is_active=True)
            self.db.add(sport)
            self.db.flush()
        elif sport.name != provider_event.sport_name:
            sport.name = provider_event.sport_name

        return sport

    def _upsert_bookmaker(self, provider_bookmaker: ProviderBookmaker) -> Bookmaker:
        bookmaker = self.db.scalar(select(Bookmaker).where(Bookmaker.api_key_name == provider_bookmaker.key))
        if bookmaker is None:
            bookmaker = Bookmaker(
                name=provider_bookmaker.name,
                region=provider_bookmaker.region,
                api_key_name=provider_bookmaker.key,
                is_active=True,
            )
            self.db.add(bookmaker)
            self.db.flush()
        else:
            bookmaker.name = provider_bookmaker.name
            bookmaker.region = provider_bookmaker.region
            bookmaker.is_active = True

        return bookmaker

    def _upsert_event(
        self,
        provider_event: ProviderEvent,
        normalized_event: NormalizedEvent,
        sport: Sport,
    ) -> Event:
        event = self.db.scalar(select(Event).where(Event.external_id == provider_event.external_id))
        if event is None:
            event = self.db.scalar(
                select(Event).where(
                    Event.sport_id == sport.id,
                    Event.normalized_event_key == normalized_event.normalized_event_key,
                )
            )

        if event is None:
            event = Event(
                external_id=provider_event.external_id,
                sport_id=sport.id,
                home_team=normalized_event.home_team.canonical_name,
                away_team=normalized_event.away_team.canonical_name,
                start_time=provider_event.start_time,
                normalized_event_key=normalized_event.normalized_event_key,
            )
            self.db.add(event)
            self.db.flush()
        else:
            event.sport_id = sport.id
            event.home_team = normalized_event.home_team.canonical_name
            event.away_team = normalized_event.away_team.canonical_name
            event.start_time = provider_event.start_time
            event.normalized_event_key = normalized_event.normalized_event_key

        return event

    def _upsert_market(
        self,
        event: Event,
        bookmaker: Bookmaker,
        provider_market: ProviderMarket,
        provider_bookmaker: ProviderBookmaker,
        canonical_market_type: str,
        captured_at: datetime,
    ) -> Market:
        line = normalize_line(provider_market.line)
        query = select(Market).where(
            Market.event_id == event.id,
            Market.bookmaker_id == bookmaker.id,
            Market.market_type == canonical_market_type,
            Market.is_live == provider_market.is_live,
        )
        query = query.where(Market.line.is_(None)) if line is None else query.where(Market.line == line)

        market = self.db.scalar(query)
        last_seen_at = provider_bookmaker.last_update or captured_at

        if market is None:
            market = Market(
                event_id=event.id,
                bookmaker_id=bookmaker.id,
                market_type=canonical_market_type,
                line=line,
                is_live=provider_market.is_live,
                is_suspended=False,
                last_seen_at=last_seen_at,
            )
            self.db.add(market)
            self.db.flush()
        else:
            market.is_suspended = False
            market.last_seen_at = last_seen_at

        return market

    def _upsert_outcome(self, market: Market, outcome_name: str, decimal_odds: Decimal) -> Outcome:
        outcome = self.db.scalar(
            select(Outcome).where(
                Outcome.market_id == market.id,
                Outcome.outcome_name == outcome_name,
            )
        )

        if outcome is None:
            outcome = Outcome(
                market_id=market.id,
                outcome_name=outcome_name,
                decimal_odds=decimal_odds,
            )
            self.db.add(outcome)
            self.db.flush()
        else:
            outcome.decimal_odds = decimal_odds

        return outcome

    def _normalize_outcome_name(self, sport_key: str, canonical_market_type: str, outcome_name: str) -> str:
        if canonical_market_type == "h2h":
            return self.normalizer.normalize_team_name(sport_key, outcome_name).canonical_name
        return outcome_name.strip()

    @staticmethod
    def _should_store_market(provider_market: ProviderMarket, canonical_market_type: str) -> bool:
        return (
            canonical_market_type == "h2h"
            and not provider_market.is_live
            and not provider_market.is_suspended
            and len(provider_market.outcomes) > 0
        )


def normalize_decimal_odds(value: Decimal) -> Decimal | None:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

    if not decimal_value.is_finite() or decimal_value <= Decimal("1"):
        return None

    return decimal_value.quantize(DECIMAL_ODDS_PRECISION)


def normalize_line(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None

    try:
        decimal_value = Decimal(str(value))
        if not decimal_value.is_finite():
            return None
        return decimal_value.quantize(LINE_PRECISION)
    except (InvalidOperation, ValueError):
        return None
