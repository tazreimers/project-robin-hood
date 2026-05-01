from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import build_opportunity_instructions, get_opportunity_with_details, mark_opportunity_actioned
from app.models import ArbitrageLeg, ArbitrageOpportunity, Base, Bookmaker, Event, OddsSnapshot, Sport


class OpportunityInstructionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db: Session = self.session_factory()
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

        sport = Sport(key="test_sport", name="Test Sport", is_active=True)
        event = Event(
            external_id="event-1",
            sport=sport,
            home_team="Home",
            away_team="Away",
            start_time=self.now + timedelta(days=1),
            normalized_event_key="test-sport:2026-01-02:home:away",
        )
        bookmaker_a = Bookmaker(name="Bookmaker A", region="au", api_key_name="bookmaker_a", is_active=True)
        bookmaker_b = Bookmaker(name="Bookmaker B", region="au", api_key_name="bookmaker_b", is_active=True)
        self.db.add_all([sport, event, bookmaker_a, bookmaker_b])
        self.db.flush()

        opportunity = ArbitrageOpportunity(
            event_id=event.id,
            market_type="h2h",
            line=None,
            implied_probability_total=Decimal("0.909091"),
            margin=Decimal("0.090909"),
            total_stake=Decimal("1000.00"),
            guaranteed_return=Decimal("1100.00"),
            guaranteed_profit=Decimal("100.00"),
            status="open",
            detected_at=self.now,
            expires_at=self.now + timedelta(seconds=60),
        )
        self.db.add(opportunity)
        self.db.flush()

        self.opportunity_id = opportunity.id
        self.db.add_all(
            [
                ArbitrageLeg(
                    opportunity_id=opportunity.id,
                    bookmaker_id=bookmaker_a.id,
                    outcome_name="Home",
                    decimal_odds=Decimal("2.2000"),
                    stake=Decimal("500.00"),
                    expected_return=Decimal("1100.00"),
                ),
                ArbitrageLeg(
                    opportunity_id=opportunity.id,
                    bookmaker_id=bookmaker_b.id,
                    outcome_name="Away",
                    decimal_odds=Decimal("2.2000"),
                    stake=Decimal("500.00"),
                    expected_return=Decimal("1100.00"),
                ),
                OddsSnapshot(
                    event_id=event.id,
                    bookmaker_id=bookmaker_a.id,
                    market_type="h2h",
                    line=None,
                    outcome_name="Home",
                    decimal_odds=Decimal("2.2000"),
                    captured_at=self.now - timedelta(seconds=12),
                ),
                OddsSnapshot(
                    event_id=event.id,
                    bookmaker_id=bookmaker_b.id,
                    market_type="h2h",
                    line=None,
                    outcome_name="Away",
                    decimal_odds=Decimal("2.2000"),
                    captured_at=self.now - timedelta(seconds=18),
                ),
            ]
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_build_opportunity_instructions(self) -> None:
        opportunity = get_opportunity_with_details(self.opportunity_id, self.db)
        response = build_opportunity_instructions(opportunity=opportunity, db=self.db, now=self.now)

        self.assertEqual(response.event.home_team, "Home")
        self.assertEqual(response.market, "h2h")
        self.assertEqual(response.total_stake, Decimal("1000.00"))
        self.assertEqual(response.guaranteed_profit, Decimal("100.00"))
        self.assertEqual(len(response.legs), 2)
        self.assertEqual(sorted(leg.odds_age_seconds for leg in response.legs), [12, 18])
        self.assertIn("Re-check odds manually", response.warning)
        self.assertTrue(all("only if decimal odds are still" in leg.instruction for leg in response.legs))

    def test_mark_opportunity_actioned(self) -> None:
        opportunity = mark_opportunity_actioned(self.opportunity_id, self.db)

        self.assertEqual(opportunity.status, "ACTIONED")
        self.assertEqual(self.db.get(ArbitrageOpportunity, self.opportunity_id).status, "ACTIONED")


if __name__ == "__main__":
    unittest.main()
