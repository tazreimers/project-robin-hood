from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import create_opportunity_execution, update_execution_leg
from app.models import ArbitrageLeg, ArbitrageOpportunity, Base, Bookmaker, Event, Sport
from app.schemas.execution import ExecutionLegPatch, OpportunityExecutionCreate


class ExecutionWorkflowTest(unittest.TestCase):
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
            start_time=self.now + timedelta(hours=4),
            normalized_event_key="test-sport:2026-01-01:home:away",
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
            ]
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_create_execution_from_opportunity(self) -> None:
        execution = create_opportunity_execution(
            self.opportunity_id,
            OpportunityExecutionCreate(notes="Manual plan"),
            db=self.db,
        )

        self.assertEqual(execution.status, "PLANNED")
        self.assertEqual(execution.total_stake_planned, Decimal("1000.00"))
        self.assertEqual(execution.expected_profit, Decimal("100.00"))
        self.assertEqual(execution.notes, "Manual plan")
        self.assertEqual(len(execution.legs), 2)
        self.assertTrue(all(leg.status == "PLANNED" for leg in execution.legs))

    def test_update_actual_odds_and_stakes_calculates_actual_profit(self) -> None:
        execution = create_opportunity_execution(
            self.opportunity_id,
            OpportunityExecutionCreate(),
            db=self.db,
        )

        for leg in execution.legs:
            execution = update_execution_leg(
                execution.id,
                leg.id,
                ExecutionLegPatch(
                    actual_odds=Decimal("2.1000"),
                    actual_stake=Decimal("500.00"),
                    status="PLACED",
                ),
                db=self.db,
            )

        self.assertEqual(execution.status, "ACTIONED")
        self.assertEqual(execution.total_stake_actual, Decimal("1000.00"))
        self.assertEqual(execution.actual_profit, Decimal("50.00"))
        self.assertTrue(all(leg.actual_odds == Decimal("2.1000") for leg in execution.legs))
        self.assertTrue(all(leg.actual_stake == Decimal("500.00") for leg in execution.legs))

    def test_mark_odds_changed(self) -> None:
        execution = create_opportunity_execution(
            self.opportunity_id,
            OpportunityExecutionCreate(),
            db=self.db,
        )

        updated = update_execution_leg(
            execution.id,
            execution.legs[0].id,
            ExecutionLegPatch(status="ODDS_CHANGED", actual_odds=Decimal("2.0000")),
            db=self.db,
        )

        self.assertEqual(updated.status, "ODDS_CHANGED")
        self.assertEqual(updated.legs[0].status, "ODDS_CHANGED")
        self.assertIsNone(updated.actual_profit)


if __name__ == "__main__":
    unittest.main()
