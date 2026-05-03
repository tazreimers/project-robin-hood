from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import ArbitrageOpportunity, Base, ScanRun
from app.services.providers import (
    OddsProvider,
    ProviderBookmaker,
    ProviderEvent,
    ProviderMarket,
    ProviderOutcome,
    ProviderSport,
)
from app.services.scanner import ScannerService


class FakeOddsProvider(OddsProvider):
    def __init__(self, event_start_time: datetime) -> None:
        self.event_start_time = event_start_time

    def fetch_sports(self) -> list[ProviderSport]:
        return [ProviderSport(key="test_sport", name="Test Sport", is_active=True)]

    def fetch_odds(self, sport_key: str) -> list[ProviderEvent]:
        return [
            ProviderEvent(
                external_id="event-1",
                sport_key=sport_key,
                sport_name="Test Sport",
                home_team="Home",
                away_team="Away",
                start_time=self.event_start_time,
                bookmakers=[
                    ProviderBookmaker(
                        key="bookmaker_a",
                        name="Bookmaker A",
                        region="au",
                        markets=[
                            ProviderMarket(
                                market_type="h2h",
                                outcomes=[
                                    ProviderOutcome(name="Home", decimal_odds=Decimal("2.20")),
                                    ProviderOutcome(name="Away", decimal_odds=Decimal("1.75")),
                                ],
                            )
                        ],
                    ),
                    ProviderBookmaker(
                        key="bookmaker_b",
                        name="Bookmaker B",
                        region="au",
                        markets=[
                            ProviderMarket(
                                market_type="h2h",
                                outcomes=[
                                    ProviderOutcome(name="Home", decimal_odds=Decimal("1.75")),
                                    ProviderOutcome(name="Away", decimal_odds=Decimal("2.20")),
                                ],
                            )
                        ],
                    ),
                ],
            )
        ]


class ScannerServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db: Session = self.session_factory()
        self.settings = Settings(
            sport_keys="test_sport",
            default_total_stake=Decimal("1000"),
            min_arbitrage_margin=Decimal("0.01"),
            max_odds_age_seconds=60,
        )
        self.provider = FakeOddsProvider(datetime.now(timezone.utc) + timedelta(days=1))

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_complete_scan_fetches_odds_and_detects_arbitrage(self) -> None:
        service = ScannerService(self.db, settings=self.settings, provider=self.provider)
        scan_run = service.create_scan_run()
        service.mark_running(scan_run.id)
        summary = service.run(scan_run.id)
        self.db.commit()

        saved_run = self.db.get(ScanRun, scan_run.id)
        self.assertIsNotNone(saved_run)
        self.assertEqual(summary.scan_id, scan_run.id)
        self.assertEqual(summary.status, "completed")
        self.assertEqual(saved_run.status, "completed")
        self.assertEqual(saved_run.sports_scanned, 1)
        self.assertEqual(saved_run.events_processed, 1)
        self.assertEqual(saved_run.markets_processed, 2)
        self.assertEqual(saved_run.snapshots_saved, 4)
        self.assertEqual(saved_run.opportunities_found, 1)
        self.assertIsNone(saved_run.error_message)
        self.assertIsNotNone(saved_run.completed_at)
        self.assertEqual(len(self.db.scalars(select(ArbitrageOpportunity)).all()), 1)

    def test_scan_requires_sport_keys(self) -> None:
        service = ScannerService(
            self.db,
            settings=Settings(sport_keys=""),
            provider=self.provider,
        )
        scan_run = service.create_scan_run()

        with self.assertRaisesRegex(ValueError, "SPORT_KEYS"):
            service.run(scan_run.id)


if __name__ == "__main__":
    unittest.main()
