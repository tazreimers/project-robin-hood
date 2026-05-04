from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import Base, Bookmaker, Event, MarketQualityCheck, OddsSnapshot, Sport
from app.services.market_quality import MarketQualityService


class MarketQualityServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db: Session = self.session_factory()
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.settings = Settings(
            max_odds_age_seconds=60,
            min_market_confidence=Decimal("0.85"),
            max_event_start_time_diff_minutes=5,
        )

        self.sport = Sport(key="test_sport", name="Test Sport", is_active=True)
        self.event = Event(
            external_id="event-1",
            sport=self.sport,
            home_team="Home",
            away_team="Away",
            start_time=self.now + timedelta(days=1),
            normalized_event_key="test-sport:event-1",
        )
        self.bookmakers = [
            Bookmaker(name="Bookmaker A", region="au", api_key_name="bookmaker_a", is_active=True),
            Bookmaker(name="Bookmaker B", region="au", api_key_name="bookmaker_b", is_active=True),
            Bookmaker(name="Bookmaker C", region="au", api_key_name="bookmaker_c", is_active=True),
        ]
        self.db.add_all([self.sport, self.event, *self.bookmakers])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_mismatched_line_rejected(self) -> None:
        snapshots = [
            self.snapshot(self.bookmakers[0], "Home", "1.5", "2.1000"),
            self.snapshot(self.bookmakers[1], "Away", "2.5", "2.1000"),
        ]

        result = self.validate(line=Decimal("1.5"), snapshots=snapshots)

        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.confidence_score, Decimal("0.0000"))
        self.assertIn("Line does not match", " ".join(result.reasons["failures"]))

    def test_stale_odds_rejected(self) -> None:
        captured_at = self.now - timedelta(seconds=61)
        snapshots = [
            self.snapshot(self.bookmakers[0], "Home", None, "2.1000", captured_at=captured_at),
            self.snapshot(self.bookmakers[1], "Away", None, "2.1000", captured_at=captured_at),
        ]

        result = self.validate(line=None, snapshots=snapshots)

        self.assertEqual(result.status, "STALE")
        self.assertEqual(result.confidence_score, Decimal("0.0000"))
        self.assertIn("stale", " ".join(result.reasons["failures"]))

    def test_missing_outcome_rejected(self) -> None:
        snapshots = [self.snapshot(self.bookmakers[0], "Home", None, "2.1000")]

        result = self.validate(line=None, snapshots=snapshots)

        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.confidence_score, Decimal("0.0000"))
        self.assertIn("unique outcome", " ".join(result.reasons["failures"]))

    def test_valid_two_way_market_accepted(self) -> None:
        snapshots = [
            self.snapshot(self.bookmakers[0], "Home", None, "2.1000"),
            self.snapshot(self.bookmakers[1], "Away", None, "2.1000"),
        ]

        result = self.validate(line=None, snapshots=snapshots)

        self.assertEqual(result.status, "VERIFIED")
        self.assertEqual(result.confidence_score, Decimal("1.0000"))
        self.assertEqual(len(self.db.scalars(select(MarketQualityCheck)).all()), 1)

    def test_valid_three_way_market_accepted(self) -> None:
        snapshots = [
            self.snapshot(self.bookmakers[0], "Home", None, "3.3000"),
            self.snapshot(self.bookmakers[1], "Draw", None, "3.4000"),
            self.snapshot(self.bookmakers[2], "Away", None, "3.5000"),
        ]

        result = self.validate(line=None, snapshots=snapshots)

        self.assertEqual(result.status, "VERIFIED")
        self.assertEqual(result.confidence_score, Decimal("1.0000"))

    def validate(self, line: Decimal | None, snapshots: list[OddsSnapshot]):
        return MarketQualityService(self.db, settings=self.settings).validate_market(
            event_id=self.event.id,
            market_type="h2h",
            line=line,
            snapshots=snapshots,
            checked_at=self.now,
        )

    def snapshot(
        self,
        bookmaker: Bookmaker,
        outcome_name: str,
        line: str | None,
        decimal_odds: str,
        captured_at: datetime | None = None,
    ) -> OddsSnapshot:
        snapshot = OddsSnapshot(
            event_id=self.event.id,
            bookmaker_id=bookmaker.id,
            market_type="h2h",
            line=Decimal(line) if line is not None else None,
            outcome_name=outcome_name,
            decimal_odds=Decimal(decimal_odds),
            captured_at=captured_at or self.now,
        )
        self.db.add(snapshot)
        self.db.flush()
        return snapshot


if __name__ == "__main__":
    unittest.main()
