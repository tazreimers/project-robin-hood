from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import ArbitrageLeg, ArbitrageOpportunity, OddsSnapshot

FRESH = "FRESH"
STALE = "STALE"
RISKY = "RISKY"
EXPIRED = "EXPIRED"
RISKY_EVENT_START_MINUTES = 10
RELIABILITY_PRECISION = Decimal("0.01")


@dataclass(frozen=True)
class LegValidation:
    leg_id: int
    bookmaker_name: str
    outcome_name: str
    required_odds: Decimal
    latest_odds: Decimal | None
    captured_at: datetime | None
    odds_age_seconds: int | None
    available: bool


@dataclass(frozen=True)
class OpportunityValidationResult:
    odds_age_seconds: int | None
    event_start_minutes: int | None
    market_consistency_score: float
    event_matching_confidence: float
    all_legs_available: bool
    recommended_status: str
    reliability_score: Decimal
    validation_reasons: dict[str, Any]
    latest_snapshot_at: datetime | None


class OpportunityValidator:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.max_odds_age_seconds = self.settings.max_odds_age_seconds
        self.min_arbitrage_margin = Decimal(str(self.settings.min_arbitrage_margin))

    def validate(
        self,
        opportunity: ArbitrageOpportunity,
        now: datetime | None = None,
    ) -> OpportunityValidationResult:
        validated_at = ensure_aware(now or datetime.now(timezone.utc))
        legs = list(opportunity.legs)
        leg_validations = [self._validate_leg(opportunity, leg, validated_at) for leg in legs]

        latest_snapshot_at = max(
            (leg.captured_at for leg in leg_validations if leg.captured_at is not None),
            default=None,
        )
        odds_age_seconds = max(
            (leg.odds_age_seconds for leg in leg_validations if leg.odds_age_seconds is not None),
            default=None,
        )
        stale_leg_validations = [
            leg
            for leg in leg_validations
            if leg.odds_age_seconds is not None and leg.odds_age_seconds > self.max_odds_age_seconds
        ]
        all_legs_available = bool(legs) and all(leg.available for leg in leg_validations)
        available_leg_count = sum(1 for leg in leg_validations if leg.available)
        market_consistency_score = round(available_leg_count / len(legs), 4) if legs else 0.0
        event_matching_confidence = self._event_matching_confidence(opportunity)

        event_start_minutes = self._event_start_minutes(opportunity, validated_at)
        event_starts_soon = (
            event_start_minutes is not None
            and (ensure_aware(opportunity.event.start_time) - validated_at).total_seconds()
            <= RISKY_EVENT_START_MINUTES * 60
        )
        margin_is_low = Decimal(str(opportunity.margin)) < self.min_arbitrage_margin

        reasons: list[str] = []
        if not legs:
            reasons.append("Opportunity has no required legs.")

        for leg in leg_validations:
            if leg.available:
                continue
            if leg.latest_odds is None:
                reasons.append(f"{leg.bookmaker_name} {leg.outcome_name} odds are missing.")
            else:
                reasons.append(
                    f"{leg.bookmaker_name} {leg.outcome_name} odds are {leg.latest_odds}, "
                    f"below required {leg.required_odds}."
                )

        for leg in stale_leg_validations:
            reasons.append(
                f"{leg.bookmaker_name} {leg.outcome_name} odds are "
                f"{leg.odds_age_seconds} seconds old."
            )

        if event_starts_soon and event_start_minutes is not None:
            if event_start_minutes < 0:
                reasons.append(f"Event started {abs(event_start_minutes)} minutes ago.")
            else:
                reasons.append(f"Event starts in {event_start_minutes} minutes.")

        if margin_is_low:
            reasons.append(
                f"Margin {format_percent(opportunity.margin)} is below minimum "
                f"{format_percent(self.min_arbitrage_margin)}."
            )

        if not all_legs_available:
            recommended_status = EXPIRED
        elif stale_leg_validations:
            recommended_status = STALE
        elif event_starts_soon or margin_is_low:
            recommended_status = RISKY
        else:
            recommended_status = FRESH

        if not reasons:
            reasons.append("All legs pass validation.")

        reliability_score = self._reliability_score(
            recommended_status=recommended_status,
            odds_age_seconds=odds_age_seconds,
            market_consistency_score=market_consistency_score,
            event_matching_confidence=event_matching_confidence,
            event_starts_soon=event_starts_soon,
            margin_is_low=margin_is_low,
        )
        validation_reasons = {
            "odds_age_seconds": odds_age_seconds,
            "event_start_minutes": event_start_minutes,
            "market_consistency_score": market_consistency_score,
            "event_matching_confidence": event_matching_confidence,
            "all_legs_available": all_legs_available,
            "recommended_status": recommended_status,
            "reasons": reasons,
            "leg_checks": [leg_validation_to_json(leg) for leg in leg_validations],
        }

        return OpportunityValidationResult(
            odds_age_seconds=odds_age_seconds,
            event_start_minutes=event_start_minutes,
            market_consistency_score=market_consistency_score,
            event_matching_confidence=event_matching_confidence,
            all_legs_available=all_legs_available,
            recommended_status=recommended_status,
            reliability_score=reliability_score,
            validation_reasons=validation_reasons,
            latest_snapshot_at=latest_snapshot_at,
        )

    def validate_and_apply(
        self,
        opportunity: ArbitrageOpportunity,
        now: datetime | None = None,
    ) -> OpportunityValidationResult:
        validated_at = ensure_aware(now or datetime.now(timezone.utc))
        result = self.validate(opportunity, now=validated_at)
        opportunity.reliability_score = result.reliability_score
        opportunity.validation_status = result.recommended_status
        opportunity.validation_reasons = result.validation_reasons
        opportunity.last_validated_at = validated_at
        return result

    def _validate_leg(
        self,
        opportunity: ArbitrageOpportunity,
        leg: ArbitrageLeg,
        now: datetime,
    ) -> LegValidation:
        snapshot = self._latest_leg_snapshot(opportunity, leg)
        captured_at = ensure_aware(snapshot.captured_at) if snapshot is not None else None
        odds_age_seconds = max(0, int((now - captured_at).total_seconds())) if captured_at is not None else None
        latest_odds = Decimal(str(snapshot.decimal_odds)) if snapshot is not None else None
        required_odds = Decimal(str(leg.decimal_odds))

        return LegValidation(
            leg_id=leg.id,
            bookmaker_name=leg.bookmaker.name if leg.bookmaker is not None else f"Bookmaker {leg.bookmaker_id}",
            outcome_name=leg.outcome_name,
            required_odds=required_odds,
            latest_odds=latest_odds,
            captured_at=captured_at,
            odds_age_seconds=odds_age_seconds,
            available=latest_odds is not None and latest_odds >= required_odds,
        )

    def _latest_leg_snapshot(
        self,
        opportunity: ArbitrageOpportunity,
        leg: ArbitrageLeg,
    ) -> OddsSnapshot | None:
        query = (
            select(OddsSnapshot)
            .where(OddsSnapshot.event_id == opportunity.event_id)
            .where(OddsSnapshot.market_type == opportunity.market_type)
            .where(OddsSnapshot.bookmaker_id == leg.bookmaker_id)
            .where(OddsSnapshot.outcome_name == leg.outcome_name)
            .order_by(OddsSnapshot.captured_at.desc(), OddsSnapshot.id.desc())
        )
        query = query.where(OddsSnapshot.line.is_(None)) if opportunity.line is None else query.where(
            OddsSnapshot.line == opportunity.line
        )
        return self.db.scalars(query.limit(1)).first()

    def _event_matching_confidence(self, opportunity: ArbitrageOpportunity) -> float:
        event = opportunity.event
        if event is None:
            return 0.0
        if event.external_id and event.normalized_event_key:
            return 1.0
        return 0.75

    def _event_start_minutes(self, opportunity: ArbitrageOpportunity, now: datetime) -> int | None:
        event = opportunity.event
        if event is None:
            return None

        seconds_until_start = int((ensure_aware(event.start_time) - now).total_seconds())
        if seconds_until_start >= 0:
            return math.ceil(seconds_until_start / 60)
        return math.floor(seconds_until_start / 60)

    def _reliability_score(
        self,
        recommended_status: str,
        odds_age_seconds: int | None,
        market_consistency_score: float,
        event_matching_confidence: float,
        event_starts_soon: bool,
        margin_is_low: bool,
    ) -> Decimal:
        if recommended_status == EXPIRED:
            return Decimal("0.00")

        score = Decimal("100.00") * Decimal(str(market_consistency_score)) * Decimal(str(event_matching_confidence))

        if odds_age_seconds is None:
            score -= Decimal("35")
        elif odds_age_seconds > self.max_odds_age_seconds:
            score -= Decimal("35")
        elif self.max_odds_age_seconds > 0:
            age_penalty = Decimal("15") * Decimal(str(odds_age_seconds)) / Decimal(str(self.max_odds_age_seconds))
            score -= age_penalty

        if event_starts_soon:
            score -= Decimal("20")
        if margin_is_low:
            score -= Decimal("20")

        return max(Decimal("0.00"), min(Decimal("100.00"), score)).quantize(
            RELIABILITY_PRECISION,
            rounding=ROUND_HALF_UP,
        )


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_percent(value: Decimal) -> str:
    return f"{(Decimal(str(value)) * Decimal('100')).quantize(Decimal('0.01'))}%"


def leg_validation_to_json(leg: LegValidation) -> dict[str, Any]:
    return {
        "leg_id": leg.leg_id,
        "bookmaker_name": leg.bookmaker_name,
        "outcome_name": leg.outcome_name,
        "required_odds": str(leg.required_odds),
        "latest_odds": str(leg.latest_odds) if leg.latest_odds is not None else None,
        "captured_at": leg.captured_at.isoformat() if leg.captured_at is not None else None,
        "odds_age_seconds": leg.odds_age_seconds,
        "available": leg.available,
    }
