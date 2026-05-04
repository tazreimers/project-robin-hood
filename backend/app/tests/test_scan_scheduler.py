from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import ApiUsageLog, Base, Bookmaker, Event, EventScanPriority, OddsSnapshot, Sport
from app.providers import OddsProvider, ProviderEvent, ProviderSport
from app.services.scan_scheduler import ScanScheduler


class FakeOddsProvider(OddsProvider):
    def __init__(self) -> None:
        self.fetch_odds_called = False

    def fetch_sports(self) -> list[ProviderSport]:
        return []

    def fetch_odds(self, sport_key: str) -> list[ProviderEvent]:
        self.fetch_odds_called = True
        return []


class ScanSchedulerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db: Session = self.session_factory()
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.settings = Settings(
            sport_keys="test_sport",
            odds_regions="au",
            near_arb_threshold=Decimal("0.03"),
            min_requests_remaining_buffer=5,
            daily_quota_budget=100,
            max_scans_per_hour=10,
            enable_quota_guard=True,
        )
        self.sport = Sport(key="test_sport", name="Test Sport", is_active=True)
        self.db.add(self.sport)
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_priority_assignment_by_event_start_time(self) -> None:
        scheduler = ScanScheduler(self.db, settings=self.settings)
        low_event = self.create_event("low", self.now + timedelta(hours=25))
        normal_event = self.create_event("normal", self.now + timedelta(hours=12))
        high_event = self.create_event("high", self.now + timedelta(minutes=90))

        self.assertEqual(scheduler.assign_event_priority(low_event, self.now).priority_level, "LOW")
        self.assertEqual(scheduler.assign_event_priority(normal_event, self.now).priority_level, "NORMAL")
        self.assertEqual(scheduler.assign_event_priority(high_event, self.now).priority_level, "HIGH")

    def test_near_arb_makes_event_urgent(self) -> None:
        event = self.create_event("near-arb", self.now + timedelta(hours=25))
        bookmaker_a = Bookmaker(name="Bookmaker A", region="au", api_key_name="bookmaker_a", is_active=True)
        bookmaker_b = Bookmaker(name="Bookmaker B", region="au", api_key_name="bookmaker_b", is_active=True)
        self.db.add_all([bookmaker_a, bookmaker_b])
        self.db.flush()
        self.db.add_all(
            [
                OddsSnapshot(
                    event_id=event.id,
                    bookmaker_id=bookmaker_a.id,
                    market_type="h2h",
                    line=None,
                    outcome_name="Home",
                    decimal_odds=Decimal("2.0000"),
                    captured_at=self.now,
                ),
                OddsSnapshot(
                    event_id=event.id,
                    bookmaker_id=bookmaker_b.id,
                    market_type="h2h",
                    line=None,
                    outcome_name="Away",
                    decimal_odds=Decimal("1.9600"),
                    captured_at=self.now,
                ),
            ]
        )
        self.db.flush()

        assignment = ScanScheduler(self.db, settings=self.settings).assign_event_priority(event, self.now)

        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.priority_level, "URGENT")
        self.assertIn("arbitrage", assignment.reason)

    def test_expired_events_are_not_due_for_scan(self) -> None:
        event = self.create_event("expired", self.now - timedelta(minutes=5))
        priority = EventScanPriority(
            event_id=event.id,
            sport_key="test_sport",
            priority_level="HIGH",
            next_scan_at=self.now - timedelta(minutes=1),
            last_scan_at=None,
            reason="Previously due",
        )
        self.db.add(priority)
        self.db.commit()

        scheduler = ScanScheduler(self.db, settings=self.settings)
        scheduler.refresh_priorities(self.now)

        self.assertEqual(scheduler.get_due_priorities(self.now), [])
        self.assertIsNone(priority.next_scan_at)

    def test_quota_guard_blocks_adaptive_scan(self) -> None:
        event = self.create_event("due", self.now + timedelta(minutes=90))
        self.db.add(
            EventScanPriority(
                event_id=event.id,
                sport_key="test_sport",
                priority_level="HIGH",
                next_scan_at=self.now - timedelta(seconds=1),
                last_scan_at=None,
                reason="Due",
            )
        )
        self.db.add(
            ApiUsageLog(
                provider="the_odds_api",
                endpoint="/v4/sports/test_sport/odds/",
                sport_key="test_sport",
                regions="au",
                markets="h2h",
                requests_remaining=0,
                requests_used=100,
                requests_last=1,
                estimated_cost=1,
                captured_at=self.now,
            )
        )
        self.db.commit()
        provider = FakeOddsProvider()

        summary = ScanScheduler(self.db, settings=self.settings).run_due_scan(provider=provider, now=self.now)

        self.assertEqual(summary.status, "blocked")
        self.assertFalse(provider.fetch_odds_called)
        self.assertIn("quota", summary.reason or "")

    def create_event(self, external_id: str, start_time: datetime) -> Event:
        event = Event(
            external_id=external_id,
            sport_id=self.sport.id,
            home_team="Home",
            away_team="Away",
            start_time=start_time,
            normalized_event_key=f"test_sport:{external_id}",
        )
        self.db.add(event)
        self.db.flush()
        event.sport = self.sport
        return event


if __name__ == "__main__":
    unittest.main()
