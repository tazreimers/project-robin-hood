from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import ArbitrageLeg, ArbitrageOpportunity, OddsSnapshot
from app.services.market_quality import MarketQualityService
from app.services.opportunity_validator import OpportunityValidator

IMPLIED_PROBABILITY_PRECISION = Decimal("0.000001")
MONEY_PRECISION = Decimal("0.01")
SUPPORTED_OUTCOME_COUNTS = {2, 3}


@dataclass(frozen=True)
class ArbitrageCandidateLeg:
    bookmaker: str
    outcome: str
    odds: Decimal
    implied_probability: Decimal


@dataclass(frozen=True)
class ArbitrageCandidateResult:
    implied_probability_total: Decimal
    margin: Decimal
    legs: list[ArbitrageCandidateLeg]


@dataclass(frozen=True)
class BestSnapshot:
    bookmaker_id: int
    outcome_name: str
    decimal_odds: Decimal
    implied_probability: Decimal
    captured_at: datetime


@dataclass(frozen=True)
class StakeAllocation:
    bookmaker_id: int
    outcome_name: str
    decimal_odds: Decimal
    stake: Decimal
    expected_return: Decimal


@dataclass
class ArbitrageDetectionSummary:
    markets_checked: int = 0
    opportunities_created: int = 0
    legs_created: int = 0
    opportunities_expired: int = 0
    stale_snapshots_ignored: int = 0
    quality_rejected: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "markets_checked": self.markets_checked,
            "opportunities_created": self.opportunities_created,
            "legs_created": self.legs_created,
            "opportunities_expired": self.opportunities_expired,
            "stale_snapshots_ignored": self.stale_snapshots_ignored,
            "quality_rejected": self.quality_rejected,
        }


def find_arbitrage(outcomes_by_bookmaker: Mapping[str, Mapping[str, Decimal]]) -> ArbitrageCandidateResult | None:
    """Return the best cross-bookmaker arbitrage for a two- or three-way market."""
    best_by_outcome: dict[str, ArbitrageCandidateLeg] = {}

    for bookmaker, outcomes in outcomes_by_bookmaker.items():
        for outcome, odds in outcomes.items():
            if odds <= 0:
                continue

            current = best_by_outcome.get(outcome)
            if current is None or odds > current.odds:
                best_by_outcome[outcome] = ArbitrageCandidateLeg(
                    bookmaker=bookmaker,
                    outcome=outcome,
                    odds=odds,
                    implied_probability=Decimal("1") / odds,
                )

    if len(best_by_outcome) not in SUPPORTED_OUTCOME_COUNTS:
        return None

    # Arbitrage exists when the best available odds imply less than a 100% total probability.
    implied_probability_total = sum((leg.implied_probability for leg in best_by_outcome.values()), Decimal("0"))
    if implied_probability_total >= Decimal("1"):
        return None

    return ArbitrageCandidateResult(
        implied_probability_total=implied_probability_total,
        margin=Decimal("1") - implied_probability_total,
        legs=list(best_by_outcome.values()),
    )


class ArbitrageDetectionService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.total_stake = quantize_money(self.settings.default_total_stake)
        self.min_margin = Decimal(str(self.settings.min_arbitrage_margin))
        self.min_market_confidence = Decimal(str(self.settings.min_market_confidence))
        self.max_odds_age_seconds = self.settings.max_odds_age_seconds

    def detect(self, now: datetime | None = None) -> ArbitrageDetectionSummary:
        """Detect quality-approved arbitrage opportunities from recent odds snapshots."""
        detected_at = ensure_aware(now or datetime.now(timezone.utc))
        cutoff = detected_at - timedelta(seconds=self.max_odds_age_seconds)
        summary = ArbitrageDetectionSummary()

        summary.opportunities_expired = self._expire_open_opportunities(detected_at)
        snapshots = self._load_current_snapshots(cutoff)
        summary.stale_snapshots_ignored = self._count_stale_snapshots(cutoff)

        for market_key, market_snapshots in self._group_current_market_snapshots(snapshots).items():
            summary.markets_checked += 1
            result = self._find_market_arbitrage(market_snapshots)
            if result is None or result.margin < self.min_margin:
                continue

            event_id, market_type, line = market_key
            quality_result = MarketQualityService(self.db, settings=self.settings).validate_market(
                event_id=event_id,
                market_type=market_type,
                line=line,
                snapshots=market_snapshots,
                checked_at=detected_at,
            )
            if quality_result.confidence_score < self.min_market_confidence:
                summary.quality_rejected += 1
                continue

            self._create_opportunity(
                event_id=event_id,
                market_type=market_type,
                line=line,
                result=result,
                detected_at=detected_at,
            )
            summary.opportunities_created += 1
            summary.legs_created += len(result.legs)

        self.db.flush()
        return summary

    def _load_current_snapshots(self, cutoff: datetime) -> list[OddsSnapshot]:
        query = (
            select(OddsSnapshot)
            .where(OddsSnapshot.captured_at >= cutoff)
            .where(OddsSnapshot.decimal_odds > Decimal("1"))
            .order_by(OddsSnapshot.captured_at.desc(), OddsSnapshot.id.desc())
        )
        return list(self.db.scalars(query).all())

    def _count_stale_snapshots(self, cutoff: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.count(OddsSnapshot.id))
                .where(OddsSnapshot.captured_at < cutoff)
                .where(OddsSnapshot.decimal_odds > Decimal("1"))
            )
            or 0
        )

    def _group_current_market_snapshots(
        self,
        snapshots: list[OddsSnapshot],
    ) -> dict[tuple[int, str, Decimal | None], list[OddsSnapshot]]:
        latest_by_quote: dict[tuple[int, str, Decimal | None, int, str], OddsSnapshot] = {}

        for snapshot in snapshots:
            key = (
                snapshot.event_id,
                snapshot.market_type,
                snapshot.line,
                snapshot.bookmaker_id,
                snapshot.outcome_name,
            )
            if key not in latest_by_quote:
                latest_by_quote[key] = snapshot

        grouped: dict[tuple[int, str, Decimal | None], list[OddsSnapshot]] = defaultdict(list)
        for snapshot in latest_by_quote.values():
            grouped[(snapshot.event_id, snapshot.market_type, snapshot.line)].append(snapshot)

        return dict(grouped)

    def _find_market_arbitrage(self, snapshots: list[OddsSnapshot]) -> MarketArbitrageResult | None:
        best_by_outcome: dict[str, BestSnapshot] = {}

        for snapshot in snapshots:
            odds = Decimal(str(snapshot.decimal_odds))
            if odds <= Decimal("1"):
                continue

            current = best_by_outcome.get(snapshot.outcome_name)
            if current is None or odds > current.decimal_odds:
                best_by_outcome[snapshot.outcome_name] = BestSnapshot(
                    bookmaker_id=snapshot.bookmaker_id,
                    outcome_name=snapshot.outcome_name,
                    decimal_odds=odds,
                    implied_probability=Decimal("1") / odds,
                    captured_at=ensure_aware(snapshot.captured_at),
                )

        if len(best_by_outcome) not in SUPPORTED_OUTCOME_COUNTS:
            return None

        best_snapshots = sorted(best_by_outcome.values(), key=lambda snapshot: snapshot.outcome_name)
        # Sum 1 / decimal_odds across the best price for each outcome.
        # A total below one leaves margin for a guaranteed return if all legs are placeable.
        implied_probability_total = sum(
            (snapshot.implied_probability for snapshot in best_snapshots),
            Decimal("0"),
        )
        if implied_probability_total >= Decimal("1"):
            return None

        return MarketArbitrageResult(
            implied_probability_total=implied_probability_total,
            margin=Decimal("1") - implied_probability_total,
            legs=best_snapshots,
        )

    def _create_opportunity(
        self,
        event_id: int,
        market_type: str,
        line: Decimal | None,
        result: MarketArbitrageResult,
        detected_at: datetime,
    ) -> ArbitrageOpportunity:
        allocations = allocate_stakes(
            legs=result.legs,
            total_stake=self.total_stake,
            implied_probability_total=result.implied_probability_total,
        )
        guaranteed_return = min((allocation.expected_return for allocation in allocations), default=Decimal("0.00"))
        guaranteed_profit = guaranteed_return - self.total_stake

        opportunity = ArbitrageOpportunity(
            event_id=event_id,
            market_type=market_type,
            line=line,
            implied_probability_total=quantize_probability(result.implied_probability_total),
            margin=quantize_probability(result.margin),
            total_stake=self.total_stake,
            guaranteed_return=guaranteed_return,
            guaranteed_profit=guaranteed_profit,
            status="open",
            detected_at=detected_at,
            expires_at=detected_at + timedelta(seconds=self.max_odds_age_seconds),
        )
        self.db.add(opportunity)
        self.db.flush()

        for allocation in allocations:
            self.db.add(
                ArbitrageLeg(
                    opportunity_id=opportunity.id,
                    bookmaker_id=allocation.bookmaker_id,
                    outcome_name=allocation.outcome_name,
                    decimal_odds=allocation.decimal_odds,
                    stake=allocation.stake,
                    expected_return=allocation.expected_return,
                )
            )

        self.db.flush()
        OpportunityValidator(self.db, settings=self.settings).validate_and_apply(opportunity, now=detected_at)
        self.db.flush()
        return opportunity

    def _expire_open_opportunities(self, now: datetime) -> int:
        result = self.db.execute(
            update(ArbitrageOpportunity)
            .where(ArbitrageOpportunity.status == "open")
            .values(status="expired", expires_at=now)
        )
        return result.rowcount or 0


@dataclass(frozen=True)
class MarketArbitrageResult:
    implied_probability_total: Decimal
    margin: Decimal
    legs: list[BestSnapshot]


def allocate_stakes(
    legs: list[BestSnapshot],
    total_stake: Decimal,
    implied_probability_total: Decimal,
) -> list[StakeAllocation]:
    """Allocate stake so each winning outcome returns approximately the same amount."""
    # Stakes are proportional to each leg's implied probability. The rounding delta is assigned to the
    # largest raw stake so the final recommendation still matches the configured total stake exactly.
    raw_stakes = [
        total_stake * (leg.implied_probability / implied_probability_total)
        for leg in legs
    ]
    stakes = [quantize_money(stake) for stake in raw_stakes]
    stake_delta = total_stake - sum(stakes, Decimal("0.00"))
    if stakes and stake_delta != Decimal("0.00"):
        largest_index = max(range(len(raw_stakes)), key=lambda index: raw_stakes[index])
        stakes[largest_index] = quantize_money(stakes[largest_index] + stake_delta)

    return [
        StakeAllocation(
            bookmaker_id=leg.bookmaker_id,
            outcome_name=leg.outcome_name,
            decimal_odds=quantize_odds(leg.decimal_odds),
            stake=stake,
            expected_return=quantize_money(stake * leg.decimal_odds),
        )
        for leg, stake in zip(legs, stakes, strict=True)
    ]


def quantize_probability(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(IMPLIED_PROBABILITY_PRECISION, rounding=ROUND_HALF_UP)


def quantize_money(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


def quantize_odds(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
