from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Event, Market, MarketAlias, OddsSnapshot, TeamAlias
from app.services.normalization import NormalizationService
from app.services.odds_ingestion import OddsIngestionService
from app.providers import (
    OddsProvider,
    ProviderBookmaker,
    ProviderEvent,
    ProviderMarket,
    ProviderOutcome,
    ProviderSport,
)


class DifferentlyNamedEventProvider(OddsProvider):
    provider_name = "test_provider"

    def __init__(self, start_time: datetime) -> None:
        self.start_time = start_time

    def fetch_sports(self) -> list[ProviderSport]:
        return [ProviderSport(key="aussierules_afl", name="AFL", is_active=True)]

    def fetch_odds(self, sport_key: str) -> list[ProviderEvent]:
        return [
            ProviderEvent(
                external_id="provider-a-event",
                sport_key="aussierules_afl",
                sport_name="AFL",
                home_team="Collingwood Magpies",
                away_team="Sydney Swans",
                start_time=self.start_time,
                bookmakers=[
                    ProviderBookmaker(
                        key="bookmaker_a",
                        name="Bookmaker A",
                        region="au",
                        markets=[
                            ProviderMarket(
                                market_type="Head to Head",
                                outcomes=[
                                    ProviderOutcome(name="Collingwood Magpies", decimal_odds=Decimal("2.20")),
                                    ProviderOutcome(name="Sydney Swans", decimal_odds=Decimal("1.75")),
                                ],
                            )
                        ],
                    )
                ],
            ),
            ProviderEvent(
                external_id="provider-b-event",
                sport_key="aussierules_afl",
                sport_name="AFL",
                home_team="COL",
                away_team="SYD",
                start_time=self.start_time,
                bookmakers=[
                    ProviderBookmaker(
                        key="bookmaker_b",
                        name="Bookmaker B",
                        region="au",
                        markets=[
                            ProviderMarket(
                                market_type="Head to Head",
                                outcomes=[
                                    ProviderOutcome(name="COL", decimal_odds=Decimal("1.75")),
                                    ProviderOutcome(name="SYD", decimal_odds=Decimal("2.20")),
                                ],
                            )
                        ],
                    )
                ],
            ),
        ]


class PlayerPropProvider(OddsProvider):
    provider_name = "test_provider"

    def __init__(self, start_time: datetime) -> None:
        self.start_time = start_time

    def fetch_sports(self) -> list[ProviderSport]:
        return [ProviderSport(key="aussierules_afl", name="AFL", is_active=True)]

    def fetch_odds(self, sport_key: str) -> list[ProviderEvent]:
        return [
            ProviderEvent(
                external_id="provider-prop-event",
                sport_key="aussierules_afl",
                sport_name="AFL",
                home_team="Collingwood",
                away_team="Sydney",
                start_time=self.start_time,
                bookmakers=[
                    ProviderBookmaker(
                        key="bookmaker_a",
                        name="Bookmaker A",
                        region="au",
                        markets=[
                            ProviderMarket(
                                market_type="player_disposals_over",
                                outcomes=[
                                    ProviderOutcome(
                                        name="Over",
                                        description="Nick Daicos",
                                        line=Decimal("24.5"),
                                        decimal_odds=Decimal("1.87"),
                                    ),
                                ],
                            )
                        ],
                    )
                ],
            )
        ]


class NormalizationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db: Session = self.session_factory()
        self.start_time = datetime.now(timezone.utc) + timedelta(days=1)
        self.seed_aliases()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_exact_team_alias_match(self) -> None:
        result = NormalizationService(self.db).normalize_team_name("aussierules_afl", "Magpies")

        self.assertEqual(result.canonical_name, "Collingwood")
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.match_type, "exact_alias")

    def test_fuzzy_team_alias_match(self) -> None:
        result = NormalizationService(self.db).normalize_team_name(
            "aussierules_afl",
            "Collngwood Magpies",
        )

        self.assertEqual(result.canonical_name, "Collingwood")
        self.assertEqual(result.match_type, "fuzzy_alias")
        self.assertGreaterEqual(result.confidence, 0.90)

    def test_two_providers_naming_same_event_differently(self) -> None:
        provider = DifferentlyNamedEventProvider(self.start_time)
        service = OddsIngestionService(self.db, provider=provider)

        summary = service.ingest_sport_odds("aussierules_afl")
        self.db.commit()

        events = list(self.db.scalars(select(Event)).all())
        snapshots = list(self.db.scalars(select(OddsSnapshot)).all())
        self.assertEqual(summary.events_saved, 2)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].home_team, "Collingwood")
        self.assertEqual(events[0].away_team, "Sydney")
        self.assertEqual(events[0].normalized_event_key, "aussierules_afl:%s:collingwood:sydney" % self.start_time.date())
        self.assertEqual({snapshot.market_type for snapshot in snapshots}, {"h2h"})
        self.assertEqual({snapshot.outcome_name for snapshot in snapshots}, {"Collingwood", "Sydney"})

    def test_player_prop_outcomes_keep_player_and_line_context(self) -> None:
        provider = PlayerPropProvider(self.start_time)
        service = OddsIngestionService(self.db, provider=provider)

        summary = service.ingest_sport_odds("aussierules_afl")
        self.db.commit()

        market = self.db.scalar(select(Market))
        snapshot = self.db.scalar(select(OddsSnapshot))
        self.assertIsNotNone(market)
        self.assertIsNotNone(snapshot)
        self.assertEqual(summary.markets_saved, 1)
        self.assertEqual(summary.snapshots_saved, 1)
        self.assertEqual(market.market_type, "player_disposals_over")
        self.assertEqual(market.line, Decimal("24.5000"))
        self.assertEqual(snapshot.market_type, "player_disposals_over")
        self.assertEqual(snapshot.line, Decimal("24.5000"))
        self.assertEqual(snapshot.outcome_name, "Nick Daicos - Over")

    def test_event_match_confidence_for_different_aliases(self) -> None:
        first = ProviderEvent(
            external_id="provider-a-event",
            sport_key="aussierules_afl",
            sport_name="AFL",
            home_team="Collingwood Magpies",
            away_team="Sydney Swans",
            start_time=self.start_time,
        )
        second = ProviderEvent(
            external_id="provider-b-event",
            sport_key="aussierules_afl",
            sport_name="AFL",
            home_team="COL",
            away_team="SYD",
            start_time=self.start_time,
        )

        match = NormalizationService(self.db).match_events(first, second)

        self.assertTrue(match.matched)
        self.assertEqual(match.normalized_event_key, "aussierules_afl:%s:collingwood:sydney" % self.start_time.date())
        self.assertEqual(match.reason, "normalized_event_key")
        self.assertEqual(match.confidence, 1.0)

    def test_market_alias_normalization(self) -> None:
        result = NormalizationService(self.db).normalize_market_name("test_provider", "Head to Head")

        self.assertEqual(result.canonical_market_type, "h2h")
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.match_type, "exact_alias")

    def seed_aliases(self) -> None:
        self.db.add_all(
            [
                TeamAlias(
                    sport_key="aussierules_afl",
                    canonical_name="Collingwood",
                    alias="Collingwood",
                ),
                TeamAlias(
                    sport_key="aussierules_afl",
                    canonical_name="Collingwood",
                    alias="Collingwood Magpies",
                ),
                TeamAlias(
                    sport_key="aussierules_afl",
                    canonical_name="Collingwood",
                    alias="Magpies",
                ),
                TeamAlias(
                    sport_key="aussierules_afl",
                    canonical_name="Collingwood",
                    alias="COL",
                ),
                TeamAlias(
                    sport_key="aussierules_afl",
                    canonical_name="Sydney",
                    alias="Sydney",
                ),
                TeamAlias(
                    sport_key="aussierules_afl",
                    canonical_name="Sydney",
                    alias="Sydney Swans",
                ),
                TeamAlias(
                    sport_key="aussierules_afl",
                    canonical_name="Sydney",
                    alias="Swans",
                ),
                TeamAlias(
                    sport_key="aussierules_afl",
                    canonical_name="Sydney",
                    alias="SYD",
                ),
                MarketAlias(
                    provider="test_provider",
                    source_market_name="Head to Head",
                    canonical_market_type="h2h",
                ),
            ]
        )
        self.db.commit()


if __name__ == "__main__":
    unittest.main()
