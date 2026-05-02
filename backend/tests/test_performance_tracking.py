from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import (
    build_dashboard_metrics,
    create_bet_record,
    create_opportunity_action,
    mark_opportunity_actioned,
    update_bet_record,
)
from app.models import ArbitrageLeg, ArbitrageOpportunity, Base, BetRecord, Bookmaker, Event, OpportunityAction, Sport
from app.schemas.odds import BetRecordCreate, BetRecordPatch, OpportunityActionCreate


class PerformanceTrackingTest(unittest.TestCase):
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
            normalized_event_key="test-sport:2026-01-02:away:home",
        )
        self.bookmaker_a = Bookmaker(name="Bookmaker A", region="au", api_key_name="bookmaker_a", is_active=True)
        self.bookmaker_b = Bookmaker(name="Bookmaker B", region="au", api_key_name="bookmaker_b", is_active=True)
        self.db.add_all([sport, event, self.bookmaker_a, self.bookmaker_b])
        self.db.flush()

        self.opportunity = ArbitrageOpportunity(
            event_id=event.id,
            market_type="h2h",
            line=None,
            implied_probability_total=Decimal("0.909091"),
            margin=Decimal("0.090909"),
            total_stake=Decimal("1000.00"),
            guaranteed_return=Decimal("1100.00"),
            guaranteed_profit=Decimal("100.00"),
            status="open",
            reliability_score=Decimal("92.50"),
            validation_status="FRESH",
            validation_reasons={"odds_age_seconds": 12},
            detected_at=self.now,
            expires_at=self.now + timedelta(seconds=60),
        )
        self.expired_opportunity = ArbitrageOpportunity(
            event_id=event.id,
            market_type="h2h",
            line=None,
            implied_probability_total=Decimal("0.980000"),
            margin=Decimal("0.020000"),
            total_stake=Decimal("1000.00"),
            guaranteed_return=Decimal("1020.00"),
            guaranteed_profit=Decimal("20.00"),
            status="expired",
            reliability_score=Decimal("0.00"),
            validation_status="EXPIRED",
            validation_reasons={"odds_age_seconds": 90},
            detected_at=self.now,
            expires_at=self.now,
        )
        self.db.add_all([self.opportunity, self.expired_opportunity])
        self.db.flush()
        self.db.add_all(
            [
                ArbitrageLeg(
                    opportunity_id=self.opportunity.id,
                    bookmaker_id=self.bookmaker_a.id,
                    outcome_name="Home",
                    decimal_odds=Decimal("2.2000"),
                    stake=Decimal("500.00"),
                    expected_return=Decimal("1100.00"),
                ),
                ArbitrageLeg(
                    opportunity_id=self.opportunity.id,
                    bookmaker_id=self.bookmaker_b.id,
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

    def test_create_opportunity_action_validates_supported_types(self) -> None:
        action = create_opportunity_action(
            self.opportunity.id,
            OpportunityActionCreate(action_type="viewed", notes="Opened detail page"),
            db=self.db,
        )

        self.assertEqual(action.action_type, "VIEWED")
        self.assertEqual(action.notes, "Opened detail page")

        with self.assertRaises(HTTPException):
            create_opportunity_action(
                self.opportunity.id,
                OpportunityActionCreate(action_type="AUTOMATED_BET", notes=None),
                db=self.db,
            )

    def test_mark_actioned_logs_action(self) -> None:
        opportunity = mark_opportunity_actioned(self.opportunity.id, db=self.db)

        actions = list(self.db.scalars(select(OpportunityAction)).all())
        self.assertEqual(opportunity.status, "ACTIONED")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].action_type, "ACTIONED")

    def test_create_and_patch_bet_record(self) -> None:
        record = create_bet_record(
            self.opportunity.id,
            BetRecordCreate(
                bookmaker_id=self.bookmaker_a.id,
                outcome_name="Home",
                odds_taken=Decimal("2.2000"),
                recommended_stake=Decimal("500.00"),
                actual_stake=Decimal("450.00"),
            ),
            db=self.db,
        )

        updated = update_bet_record(
            record.id,
            BetRecordPatch(
                result_status="won",
                payout=Decimal("990.00"),
                profit_loss=Decimal("540.00"),
                settled_at=self.now,
            ),
            db=self.db,
        )

        self.assertEqual(updated.result_status, "WON")
        self.assertEqual(updated.profit_loss, Decimal("540.00"))
        self.assertEqual(len(self.db.scalars(select(BetRecord)).all()), 1)

    def test_dashboard_metrics(self) -> None:
        mark_opportunity_actioned(self.opportunity.id, db=self.db)
        create_bet_record(
            self.opportunity.id,
            BetRecordCreate(
                bookmaker_id=self.bookmaker_a.id,
                outcome_name="Home",
                odds_taken=Decimal("2.2000"),
                recommended_stake=Decimal("500.00"),
                actual_stake=Decimal("450.00"),
                result_status="WON",
                payout=Decimal("990.00"),
                profit_loss=Decimal("540.00"),
                settled_at=self.now,
            ),
            db=self.db,
        )

        metrics = build_dashboard_metrics(self.db)

        self.assertEqual(metrics.total_opportunities_found, 2)
        self.assertEqual(metrics.opportunities_actioned, 1)
        self.assertEqual(metrics.expired_before_action, 1)
        self.assertEqual(metrics.total_recommended_profit, Decimal("120.00"))
        self.assertEqual(metrics.actual_profit_loss, Decimal("540.00"))
        self.assertEqual(metrics.average_margin, Decimal("0.055455"))
        self.assertEqual(metrics.average_odds_age, Decimal("51.00"))
        self.assertEqual(metrics.best_bookmaker_pairs[0].bookmaker_pair, ["Bookmaker A", "Bookmaker B"])
        self.assertEqual(metrics.recent_activity[0].action_type, "ACTIONED")


if __name__ == "__main__":
    unittest.main()
