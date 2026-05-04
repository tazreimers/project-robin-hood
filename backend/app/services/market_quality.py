from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.constants import (
    MARKET_QUALITY_REJECTED,
    MARKET_QUALITY_RISKY,
    MARKET_QUALITY_STALE,
    MARKET_QUALITY_VERIFIED,
)
from app.models import Event, Market, MarketQualityCheck, OddsSnapshot

SUPPORTED_MARKET_OUTCOME_COUNTS = {2, 3}
CONFIDENCE_PRECISION = Decimal("0.0001")
MIN_VALID_DECIMAL_ODDS = Decimal("1.01")


@dataclass(frozen=True)
class MarketQualityResult:
    status: str
    confidence_score: Decimal
    reasons: dict[str, Any]
    check: MarketQualityCheck


class MarketQualityService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def validate_market(
        self,
        event_id: int,
        market_type: str,
        line: Decimal | None,
        snapshots: list[OddsSnapshot],
        checked_at: datetime | None = None,
    ) -> MarketQualityResult:
        now = ensure_aware(checked_at or datetime.now(timezone.utc))
        reasons: dict[str, Any] = {
            "failures": [],
            "warnings": [],
            "checks": [],
            "leg_freshness": [],
        }
        confidence = Decimal("1.0000")
        stale_failure = False

        deduped_snapshots, duplicate_count = dedupe_snapshots(snapshots)
        if duplicate_count:
            reasons["warnings"].append(f"Collapsed {duplicate_count} duplicate outcome quote(s).")
            confidence -= Decimal("0.0500")

        if not deduped_snapshots:
            reasons["failures"].append("No odds snapshots were available for this market.")

        event = self.db.get(Event, event_id)
        if event is None:
            reasons["failures"].append("Event was not found.")

        if any(snapshot.market_type != market_type for snapshot in deduped_snapshots):
            reasons["failures"].append("Market type does not match across all bookmaker quotes.")
        else:
            reasons["checks"].append("Market type matches across bookmaker quotes.")

        if any(not lines_equal(snapshot.line, line) for snapshot in deduped_snapshots):
            reasons["failures"].append("Line does not match exactly across all bookmaker quotes.")
        else:
            reasons["checks"].append("Line matches across bookmaker quotes.")

        outcomes = {snapshot.outcome_name for snapshot in deduped_snapshots}
        if len(outcomes) not in SUPPORTED_MARKET_OUTCOME_COUNTS:
            reasons["failures"].append(
                f"Expected a two-way or three-way market, found {len(outcomes)} unique outcome(s)."
            )
        elif event is not None and (event.home_team not in outcomes or event.away_team not in outcomes):
            reasons["failures"].append("Required home and away outcomes are not both present.")
        else:
            reasons["checks"].append("Required market outcomes are present.")

        invalid_odds = [
            {
                "bookmaker_id": snapshot.bookmaker_id,
                "outcome_name": snapshot.outcome_name,
                "decimal_odds": str(snapshot.decimal_odds),
            }
            for snapshot in deduped_snapshots
            if not valid_decimal_odds(snapshot.decimal_odds)
        ]
        if invalid_odds:
            reasons["failures"].append("One or more decimal odds are invalid or not above 1.01.")
            reasons["invalid_odds"] = invalid_odds
        else:
            reasons["checks"].append("Decimal odds are valid.")

        max_odds_age_seconds = self.settings.max_odds_age_seconds
        stale_quotes: list[dict[str, Any]] = []
        for snapshot in deduped_snapshots:
            captured_at = ensure_aware(snapshot.captured_at)
            age_seconds = max(0, int((now - captured_at).total_seconds()))
            freshness = {
                "bookmaker_id": snapshot.bookmaker_id,
                "outcome_name": snapshot.outcome_name,
                "captured_at": captured_at.isoformat(),
                "odds_age_seconds": age_seconds,
                "fresh": age_seconds <= max_odds_age_seconds,
            }
            reasons["leg_freshness"].append(freshness)
            if not freshness["fresh"]:
                stale_quotes.append(freshness)

        if stale_quotes:
            stale_failure = True
            reasons["failures"].append("One or more odds quotes are stale.")
        else:
            reasons["checks"].append("Odds quotes are fresh.")

        suspended_quotes = [
            {
                "bookmaker_id": snapshot.bookmaker_id,
                "outcome_name": snapshot.outcome_name,
            }
            for snapshot in deduped_snapshots
            if self.is_suspended(snapshot)
        ]
        if suspended_quotes:
            reasons["failures"].append("One or more opportunity legs are suspended.")
            reasons["suspended_quotes"] = suspended_quotes
        else:
            reasons["checks"].append("No matching market leg is suspended.")

        event_start_result = self.validate_event_start_times(event_id, deduped_snapshots)
        if event_start_result["status"] == "failed":
            reasons["failures"].append(event_start_result["reason"])
        elif event_start_result["status"] == "warning":
            reasons["warnings"].append(event_start_result["reason"])
            confidence -= Decimal("0.0500")
        else:
            reasons["checks"].append(event_start_result["reason"])

        if reasons["failures"]:
            confidence = Decimal("0.0000")
            status = MARKET_QUALITY_STALE if stale_failure else MARKET_QUALITY_REJECTED
        else:
            confidence = max(Decimal("0.0000"), confidence).quantize(CONFIDENCE_PRECISION, rounding=ROUND_HALF_UP)
            status = MARKET_QUALITY_VERIFIED if confidence >= Decimal("0.9900") else MARKET_QUALITY_RISKY

        check = MarketQualityCheck(
            event_id=event_id,
            market_type=market_type,
            line=line,
            status=status,
            confidence_score=confidence,
            reasons=reasons,
            checked_at=now,
        )
        self.db.add(check)
        self.db.flush()
        return MarketQualityResult(status=status, confidence_score=confidence, reasons=reasons, check=check)

    def validate_event_start_times(self, event_id: int, snapshots: list[OddsSnapshot]) -> dict[str, str]:
        event_ids = {event_id, *(snapshot.event_id for snapshot in snapshots)}
        events = list(self.db.scalars(select(Event).where(Event.id.in_(event_ids))).all())
        if not events:
            return {"status": "failed", "reason": "No event start time was available."}

        start_times = [ensure_aware(event.start_time) for event in events]
        start_delta_seconds = int((max(start_times) - min(start_times)).total_seconds())
        max_delta_seconds = self.settings.max_event_start_time_diff_minutes * 60
        if start_delta_seconds > max_delta_seconds:
            return {
                "status": "failed",
                "reason": (
                    "Event start times differ by "
                    f"{start_delta_seconds // 60} minute(s), above the configured tolerance."
                ),
            }
        if start_delta_seconds > 0:
            return {
                "status": "warning",
                "reason": f"Event start times differ by {start_delta_seconds // 60} minute(s).",
            }
        return {"status": "passed", "reason": "Event start times match."}

    def is_suspended(self, snapshot: OddsSnapshot) -> bool:
        query = select(Market).where(
            Market.event_id == snapshot.event_id,
            Market.bookmaker_id == snapshot.bookmaker_id,
            Market.market_type == snapshot.market_type,
        )
        query = query.where(Market.line.is_(None)) if snapshot.line is None else query.where(Market.line == snapshot.line)
        market = self.db.scalar(query)
        return bool(market and market.is_suspended)


def dedupe_snapshots(snapshots: list[OddsSnapshot]) -> tuple[list[OddsSnapshot], int]:
    by_quote: dict[tuple[int, str, Decimal | None, int, str], list[OddsSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        by_quote[
            (
                snapshot.event_id,
                snapshot.market_type,
                snapshot.line,
                snapshot.bookmaker_id,
                snapshot.outcome_name,
            )
        ].append(snapshot)

    deduped: list[OddsSnapshot] = []
    duplicate_count = 0
    for quote_snapshots in by_quote.values():
        duplicate_count += max(0, len(quote_snapshots) - 1)
        deduped.append(
            sorted(
                quote_snapshots,
                key=lambda snapshot: (ensure_aware(snapshot.captured_at), snapshot.id or 0),
                reverse=True,
            )[0]
        )
    return deduped, duplicate_count


def lines_equal(left: Decimal | None, right: Decimal | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return Decimal(str(left)) == Decimal(str(right))


def valid_decimal_odds(value: Decimal) -> bool:
    decimal_value = Decimal(str(value))
    return decimal_value.is_finite() and decimal_value > MIN_VALID_DECIMAL_ODDS


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
