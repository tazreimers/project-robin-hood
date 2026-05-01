from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import ArbitrageOpportunity, Base, Bookmaker, Event, OddsSnapshot, Sport
from app.services.arbitrage import ArbitrageDetectionService


class ArbitrageDetectionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db: Session = self.session_factory()
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

        self.sport = Sport(key="test_sport", name="Test Sport", is_active=True)
        self.event = Event(
            external_id="event-1",
            sport=self.sport,
            home_team="Home",
            away_team="Away",
            start_time=self.now + timedelta(days=1),
            normalized_event_key="test-sport:2026-01-02:home:away",
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

    def test_no_arbitrage(self) -> None:
        self.add_market_snapshot(self.bookmakers[0], {"Home": "1.90", "Away": "1.90"})
        self.add_market_snapshot(self.bookmakers[1], {"Home": "1.88", "Away": "1.88"})

        summary = self.detect()

        self.assertEqual(summary.opportunities_created, 0)
        self.assertEqual(self.count_opportunities(), 0)

    def test_two_way_arbitrage(self) -> None:
        self.add_market_snapshot(self.bookmakers[0], {"Home": "2.20", "Away": "1.75"})
        self.add_market_snapshot(self.bookmakers[1], {"Home": "1.75", "Away": "2.20"})

        summary = self.detect()

        opportunity = self.get_only_opportunity()
        self.assertEqual(summary.opportunities_created, 1)
        self.assertEqual(summary.legs_created, 2)
        self.assertEqual(opportunity.implied_probability_total, Decimal("0.909091"))
        self.assertEqual(opportunity.margin, Decimal("0.090909"))
        self.assertEqual(opportunity.guaranteed_return, Decimal("1100.00"))
        self.assertEqual(opportunity.guaranteed_profit, Decimal("100.00"))
        self.assertEqual(sum((leg.stake for leg in opportunity.legs), Decimal("0.00")), Decimal("1000.00"))

    def test_three_way_arbitrage(self) -> None:
        self.add_market_snapshot(self.bookmakers[0], {"Home": "3.40", "Draw": "3.20", "Away": "3.10"})
        self.add_market_snapshot(self.bookmakers[1], {"Home": "3.10", "Draw": "3.60", "Away": "3.00"})
        self.add_market_snapshot(self.bookmakers[2], {"Home": "3.20", "Draw": "3.30", "Away": "3.80"})

        summary = self.detect()

        opportunity = self.get_only_opportunity()
        self.assertEqual(summary.opportunities_created, 1)
        self.assertEqual(summary.legs_created, 3)
        self.assertEqual({leg.outcome_name for leg in opportunity.legs}, {"Home", "Draw", "Away"})
        self.assertGreater(opportunity.guaranteed_profit, Decimal("0.00"))

    def test_stale_odds_ignored(self) -> None:
        captured_at = self.now - timedelta(seconds=61)
        self.add_market_snapshot(self.bookmakers[0], {"Home": "2.20", "Away": "1.75"}, captured_at=captured_at)
        self.add_market_snapshot(self.bookmakers[1], {"Home": "1.75", "Away": "2.20"}, captured_at=captured_at)

        summary = self.detect()

        self.assertEqual(summary.markets_checked, 0)
        self.assertEqual(summary.opportunities_created, 0)
        self.assertEqual(summary.stale_snapshots_ignored, 4)
        self.assertEqual(self.count_opportunities(), 0)

    def test_minimum_margin_filter(self) -> None:
        self.add_market_snapshot(self.bookmakers[0], {"Home": "2.02", "Away": "1.80"})
        self.add_market_snapshot(self.bookmakers[1], {"Home": "1.80", "Away": "2.02"})

        summary = self.detect()

        self.assertEqual(summary.opportunities_created, 0)
        self.assertEqual(self.count_opportunities(), 0)

    def detect(self):
        service = ArbitrageDetectionService(
            self.db,
            settings=Settings(
                default_total_stake=Decimal("1000"),
                min_arbitrage_margin=Decimal("0.01"),
                max_odds_age_seconds=60,
            ),
        )
        summary = service.detect(now=self.now)
        self.db.commit()
        return summary

    def add_market_snapshot(
        self,
        bookmaker: Bookmaker,
        outcomes: dict[str, str],
        captured_at: datetime | None = None,
    ) -> None:
        for outcome_name, decimal_odds in outcomes.items():
            self.db.add(
                OddsSnapshot(
                    event_id=self.event.id,
                    bookmaker_id=bookmaker.id,
                    market_type="h2h",
                    line=None,
                    outcome_name=outcome_name,
                    decimal_odds=Decimal(decimal_odds),
                    captured_at=captured_at or self.now,
                )
            )
        self.db.commit()

    def count_opportunities(self) -> int:
        return len(self.db.scalars(select(ArbitrageOpportunity)).all())

    def get_only_opportunity(self) -> ArbitrageOpportunity:
        opportunities = list(self.db.scalars(select(ArbitrageOpportunity)).all())
        self.assertEqual(len(opportunities), 1)
        return opportunities[0]


if __name__ == "__main__":
    unittest.main()
