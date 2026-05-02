from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import list_active_opportunities
from app.config import Settings
from app.models import ArbitrageLeg, ArbitrageOpportunity, Base, Bookmaker, Event, OddsSnapshot, Sport
from app.services.opportunity_validator import EXPIRED, FRESH, RISKY, STALE, OpportunityValidator


class OpportunityValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db: Session = self.session_factory()
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.settings = Settings(
            default_total_stake=Decimal("1000"),
            min_arbitrage_margin=Decimal("0.01"),
            max_odds_age_seconds=60,
        )

        self.sport = Sport(key="test_sport", name="Test Sport", is_active=True)
        self.event = Event(
            external_id="event-1",
            sport=self.sport,
            home_team="Home",
            away_team="Away",
            start_time=self.now + timedelta(days=1),
            normalized_event_key="test-sport:2026-01-02:home:away",
        )
        self.bookmaker_a = Bookmaker(name="Bookmaker A", region="au", api_key_name="bookmaker_a", is_active=True)
        self.bookmaker_b = Bookmaker(name="Bookmaker B", region="au", api_key_name="bookmaker_b", is_active=True)
        self.db.add_all([self.sport, self.event, self.bookmaker_a, self.bookmaker_b])
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_fresh_when_all_legs_pass_validation(self) -> None:
        opportunity = self.create_opportunity()
        self.add_leg_snapshots(opportunity, captured_at=self.now - timedelta(seconds=20))

        result = self.validate(opportunity)

        self.assertEqual(result.recommended_status, FRESH)
        self.assertTrue(result.all_legs_available)
        self.assertEqual(result.odds_age_seconds, 20)
        self.assertGreater(result.reliability_score, Decimal("90.00"))

    def test_stale_when_any_leg_odds_are_too_old(self) -> None:
        opportunity = self.create_opportunity()
        self.add_leg_snapshots(
            opportunity,
            captured_at=self.now - timedelta(seconds=20),
            bookmaker=self.bookmaker_a,
            outcomes={"Home": "2.2000"},
        )
        self.add_leg_snapshots(
            opportunity,
            captured_at=self.now - timedelta(seconds=75),
            bookmaker=self.bookmaker_b,
            outcomes={"Away": "2.2000"},
        )

        result = self.validate(opportunity)

        self.assertEqual(result.recommended_status, STALE)
        self.assertEqual(result.odds_age_seconds, 75)
        self.assertIn("Bookmaker B Away odds are 75 seconds old.", result.validation_reasons["reasons"])

    def test_risky_when_event_starts_soon(self) -> None:
        opportunity = self.create_opportunity(event_start_time=self.now + timedelta(minutes=9, seconds=30))
        self.add_leg_snapshots(opportunity, captured_at=self.now)

        result = self.validate(opportunity)

        self.assertEqual(result.recommended_status, RISKY)
        self.assertEqual(result.event_start_minutes, 10)

    def test_risky_when_margin_is_below_minimum(self) -> None:
        opportunity = self.create_opportunity(margin=Decimal("0.005000"))
        self.add_leg_snapshots(opportunity, captured_at=self.now)

        result = self.validate(opportunity)

        self.assertEqual(result.recommended_status, RISKY)
        self.assertIn("below minimum", " ".join(result.validation_reasons["reasons"]))

    def test_expired_when_required_leg_is_missing(self) -> None:
        opportunity = self.create_opportunity()
        self.add_leg_snapshots(
            opportunity,
            captured_at=self.now,
            bookmaker=self.bookmaker_a,
            outcomes={"Home": "2.2000"},
        )

        result = self.validate(opportunity)

        self.assertEqual(result.recommended_status, EXPIRED)
        self.assertFalse(result.all_legs_available)
        self.assertEqual(result.reliability_score, Decimal("0.00"))

    def test_active_opportunities_exclude_stale_by_default(self) -> None:
        now = datetime.now(timezone.utc)
        fresh = self.create_opportunity(event_start_time=now + timedelta(days=1))
        stale = self.create_opportunity(external_id="event-2", event_start_time=now + timedelta(days=1))
        self.add_leg_snapshots(fresh, captured_at=now)
        self.add_leg_snapshots(stale, captured_at=now - timedelta(seconds=75))
        self.db.commit()

        default_response = list_active_opportunities(db=self.db)
        include_stale_response = list_active_opportunities(include_stale=True, db=self.db)

        self.assertEqual([opportunity.id for opportunity in default_response], [fresh.id])
        self.assertEqual({opportunity.validation_status for opportunity in include_stale_response}, {FRESH, STALE})

    def validate(self, opportunity: ArbitrageOpportunity):
        return OpportunityValidator(self.db, settings=self.settings).validate_and_apply(opportunity, now=self.now)

    def create_opportunity(
        self,
        *,
        external_id: str = "event-1",
        event_start_time: datetime | None = None,
        margin: Decimal = Decimal("0.090909"),
    ) -> ArbitrageOpportunity:
        if external_id == self.event.external_id:
            event = self.event
        else:
            event = Event(
                external_id=external_id,
                sport=self.sport,
                home_team="Home",
                away_team="Away",
                start_time=event_start_time or self.now + timedelta(days=1),
                normalized_event_key=f"test-sport:{external_id}:home:away",
            )
            self.db.add(event)
            self.db.flush()

        if event_start_time is not None:
            event.start_time = event_start_time

        opportunity = ArbitrageOpportunity(
            event_id=event.id,
            market_type="h2h",
            line=None,
            implied_probability_total=Decimal("0.909091"),
            margin=margin,
            total_stake=Decimal("1000.00"),
            guaranteed_return=Decimal("1100.00"),
            guaranteed_profit=Decimal("100.00"),
            status="open",
            detected_at=self.now,
            expires_at=self.now + timedelta(seconds=60),
        )
        self.db.add(opportunity)
        self.db.flush()
        self.db.add_all(
            [
                ArbitrageLeg(
                    opportunity_id=opportunity.id,
                    bookmaker_id=self.bookmaker_a.id,
                    outcome_name="Home",
                    decimal_odds=Decimal("2.2000"),
                    stake=Decimal("500.00"),
                    expected_return=Decimal("1100.00"),
                ),
                ArbitrageLeg(
                    opportunity_id=opportunity.id,
                    bookmaker_id=self.bookmaker_b.id,
                    outcome_name="Away",
                    decimal_odds=Decimal("2.2000"),
                    stake=Decimal("500.00"),
                    expected_return=Decimal("1100.00"),
                ),
            ]
        )
        self.db.flush()
        self.db.refresh(opportunity)
        return opportunity

    def add_leg_snapshots(
        self,
        opportunity: ArbitrageOpportunity,
        *,
        captured_at: datetime,
        bookmaker: Bookmaker | None = None,
        outcomes: dict[str, str] | None = None,
    ) -> None:
        bookmaker_outcomes = outcomes
        if bookmaker_outcomes is None:
            bookmaker_outcomes = {"Home": "2.2000", "Away": "2.2000"}

        for outcome_name, decimal_odds in bookmaker_outcomes.items():
            selected_bookmaker = bookmaker
            if selected_bookmaker is None:
                selected_bookmaker = self.bookmaker_a if outcome_name == "Home" else self.bookmaker_b

            self.db.add(
                OddsSnapshot(
                    event_id=opportunity.event_id,
                    bookmaker_id=selected_bookmaker.id,
                    market_type=opportunity.market_type,
                    line=opportunity.line,
                    outcome_name=outcome_name,
                    decimal_odds=Decimal(decimal_odds),
                    captured_at=captured_at,
                )
            )
        self.db.flush()


if __name__ == "__main__":
    unittest.main()
