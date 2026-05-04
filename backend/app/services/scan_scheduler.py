from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.constants import (
    SCAN_PRIORITY_HIGH,
    SCAN_PRIORITY_LOW,
    SCAN_PRIORITY_NORMAL,
    SCAN_PRIORITY_URGENT,
)
from app.models import ArbitrageOpportunity, Event, EventScanPriority, OddsSnapshot
from app.providers import OddsProvider
from app.services.arbitrage import ArbitrageDetectionService, SUPPORTED_OUTCOME_COUNTS
from app.services.normalization import canonical_sport_key
from app.services.odds_ingestion import IngestionSummary, OddsIngestionService
from app.services.quota_guard import QuotaGuard

RECENT_SIGNAL_WINDOW = timedelta(hours=1)
PRIORITY_RANK = {
    SCAN_PRIORITY_LOW: 1,
    SCAN_PRIORITY_NORMAL: 2,
    SCAN_PRIORITY_HIGH: 3,
    SCAN_PRIORITY_URGENT: 4,
}


@dataclass(frozen=True)
class PriorityAssignment:
    priority_level: str
    reason: str


@dataclass
class AdaptiveScanSummary:
    status: str
    events_due: int = 0
    sports_scanned: int = 0
    sport_keys: list[str] = field(default_factory=list)
    events_processed: int = 0
    markets_processed: int = 0
    snapshots_saved: int = 0
    opportunities_found: int = 0
    priorities_updated: int = 0
    next_scan_at: datetime | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "events_due": self.events_due,
            "sports_scanned": self.sports_scanned,
            "sport_keys": self.sport_keys,
            "events_processed": self.events_processed,
            "markets_processed": self.markets_processed,
            "snapshots_saved": self.snapshots_saved,
            "opportunities_found": self.opportunities_found,
            "priorities_updated": self.priorities_updated,
            "next_scan_at": self.next_scan_at.isoformat() if self.next_scan_at else None,
            "reason": self.reason,
        }


class ScanScheduler:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.near_arb_threshold = Decimal(str(self.settings.near_arb_threshold))

    def run_due_scan(
        self,
        provider: OddsProvider | None = None,
        now: datetime | None = None,
    ) -> AdaptiveScanSummary:
        scan_time = ensure_aware(now or datetime.now(timezone.utc))
        self.refresh_priorities(scan_time)
        due_priorities = self.get_due_priorities(scan_time)
        if not due_priorities:
            return AdaptiveScanSummary(
                status="skipped",
                reason="No events are due for adaptive scanning.",
                next_scan_at=self.next_scheduled_scan(scan_time),
            )

        sport_keys = sorted({priority.sport_key for priority in due_priorities})
        quota_guard = QuotaGuard(self.db, settings=self.settings)
        quota_decision = quota_guard.check_scan_allowed(now=scan_time, sport_keys=sport_keys)
        if not quota_decision.allowed:
            return AdaptiveScanSummary(
                status="blocked",
                events_due=len(due_priorities),
                sports_scanned=0,
                sport_keys=sport_keys,
                reason=quota_decision.reason or "Adaptive scan blocked by quota guard.",
                next_scan_at=self.next_scheduled_scan(scan_time),
            )

        ingestion_service = OddsIngestionService(
            self.db,
            provider=provider,
            quota_guard=quota_guard,
        )
        ingestion_summary = IngestionSummary()
        for sport_key in sport_keys:
            ingestion_summary.merge(ingestion_service.ingest_sport_odds(sport_key))

        detection_summary = ArbitrageDetectionService(self.db, settings=self.settings).detect(now=scan_time)
        priorities_updated = self.mark_scanned(due_priorities, scan_time)

        return AdaptiveScanSummary(
            status="completed",
            events_due=len(due_priorities),
            sports_scanned=len(sport_keys),
            sport_keys=sport_keys,
            events_processed=ingestion_summary.events_saved,
            markets_processed=ingestion_summary.markets_saved,
            snapshots_saved=ingestion_summary.snapshots_saved,
            opportunities_found=detection_summary.opportunities_created,
            priorities_updated=priorities_updated,
            next_scan_at=self.next_scheduled_scan(scan_time),
        )

    def refresh_priorities(self, now: datetime | None = None) -> list[EventScanPriority]:
        checked_at = ensure_aware(now or datetime.now(timezone.utc))
        events = list(
            self.db.scalars(
                select(Event)
                .options(selectinload(Event.sport), selectinload(Event.scan_priority))
                .order_by(Event.start_time)
            ).all()
        )
        priorities: list[EventScanPriority] = []
        for event in events:
            priority = self.upsert_event_priority(event, checked_at)
            if priority is not None:
                priorities.append(priority)

        self.db.flush()
        return priorities

    def assign_event_priority(self, event: Event, now: datetime | None = None) -> PriorityAssignment | None:
        checked_at = ensure_aware(now or datetime.now(timezone.utc))
        start_time = ensure_aware(event.start_time)
        if start_time <= checked_at:
            return None

        sport_key = event.sport.key if event.sport else ""
        if not self.is_configured_sport(sport_key):
            return None

        if self.has_recent_arbitrage(event.id, checked_at):
            return PriorityAssignment(SCAN_PRIORITY_URGENT, "Recent arbitrage detected.")

        if self.has_recent_near_arbitrage(event.id, checked_at):
            return PriorityAssignment(
                SCAN_PRIORITY_URGENT,
                f"Recent odds are within {format_percent(self.near_arb_threshold)} of arbitrage.",
            )

        time_until_start = start_time - checked_at
        if time_until_start > timedelta(hours=24):
            assignment = PriorityAssignment(SCAN_PRIORITY_LOW, "Event starts more than 24 hours from now.")
        elif time_until_start > timedelta(hours=2):
            assignment = PriorityAssignment(SCAN_PRIORITY_NORMAL, "Event starts within 2 to 24 hours.")
        else:
            assignment = PriorityAssignment(SCAN_PRIORITY_HIGH, "Event starts in under 2 hours.")

        if self.has_significant_odds_movement(event.id, checked_at) and is_lower_priority(
            assignment.priority_level,
            SCAN_PRIORITY_HIGH,
        ):
            return PriorityAssignment(
                SCAN_PRIORITY_HIGH,
                f"Recent odds moved by at least {format_percent(self.near_arb_threshold)}.",
            )

        return assignment

    def upsert_event_priority(self, event: Event, now: datetime | None = None) -> EventScanPriority | None:
        checked_at = ensure_aware(now or datetime.now(timezone.utc))
        sport_key = event.sport.key if event.sport else ""
        assignment = self.assign_event_priority(event, checked_at)
        existing = event.scan_priority or self.db.scalar(
            select(EventScanPriority).where(EventScanPriority.event_id == event.id)
        )

        if assignment is None:
            if existing is None:
                return None

            existing.sport_key = sport_key
            existing.priority_level = SCAN_PRIORITY_LOW
            existing.next_scan_at = None
            existing.reason = "Event is expired or not enabled for adaptive scanning."
            self.db.flush()
            return existing

        if existing is None:
            existing = EventScanPriority(
                event_id=event.id,
                sport_key=sport_key,
                priority_level=assignment.priority_level,
                next_scan_at=checked_at,
                last_scan_at=None,
                reason=assignment.reason,
            )
            self.db.add(existing)
        else:
            existing.sport_key = sport_key
            existing.priority_level = assignment.priority_level
            existing.reason = assignment.reason
            if existing.next_scan_at is None:
                existing.next_scan_at = checked_at
            elif assignment.priority_level == SCAN_PRIORITY_URGENT and ensure_aware(existing.next_scan_at) > checked_at:
                existing.next_scan_at = checked_at

        self.db.flush()
        return existing

    def get_due_priorities(self, now: datetime | None = None) -> list[EventScanPriority]:
        checked_at = ensure_aware(now or datetime.now(timezone.utc))
        query = (
            select(EventScanPriority)
            .join(Event)
            .options(selectinload(EventScanPriority.event).selectinload(Event.sport))
            .where(EventScanPriority.next_scan_at.is_not(None))
            .where(EventScanPriority.next_scan_at <= checked_at)
            .where(Event.start_time > checked_at)
            .order_by(EventScanPriority.next_scan_at, Event.start_time)
        )
        return [
            priority
            for priority in self.db.scalars(query).all()
            if self.is_configured_sport(priority.sport_key)
        ]

    def list_priorities(self) -> list[EventScanPriority]:
        return list(
            self.db.scalars(
                select(EventScanPriority)
                .join(Event)
                .options(selectinload(EventScanPriority.event))
                .order_by(Event.start_time, EventScanPriority.id)
            ).all()
        )

    def mark_scanned(self, priorities: list[EventScanPriority], now: datetime | None = None) -> int:
        scanned_at = ensure_aware(now or datetime.now(timezone.utc))
        updated = 0
        for priority in priorities:
            priority.event = priority.event or self.db.get(Event, priority.event_id)
            if priority.event is None:
                continue

            assignment = self.assign_event_priority(priority.event, scanned_at)
            priority.last_scan_at = scanned_at
            if assignment is None:
                priority.priority_level = SCAN_PRIORITY_LOW
                priority.next_scan_at = None
                priority.reason = "Event is expired or not enabled for adaptive scanning."
            else:
                priority.priority_level = assignment.priority_level
                priority.reason = assignment.reason
                priority.next_scan_at = scanned_at + self.interval_for_priority(assignment.priority_level)
            updated += 1

        self.db.flush()
        return updated

    def next_scheduled_scan(self, now: datetime | None = None) -> datetime | None:
        checked_at = ensure_aware(now or datetime.now(timezone.utc))
        return self.db.scalar(
            select(func.min(EventScanPriority.next_scan_at))
            .where(EventScanPriority.next_scan_at.is_not(None))
            .where(EventScanPriority.next_scan_at >= checked_at)
        )

    def has_recent_arbitrage(self, event_id: int, now: datetime) -> bool:
        cutoff = now - RECENT_SIGNAL_WINDOW
        count = self.db.scalar(
            select(func.count(ArbitrageOpportunity.id)).where(
                ArbitrageOpportunity.event_id == event_id,
                ArbitrageOpportunity.detected_at >= cutoff,
            )
        )
        return bool(count)

    def has_recent_near_arbitrage(self, event_id: int, now: datetime) -> bool:
        snapshots = self.recent_snapshots(event_id, now)
        for market_snapshots in group_latest_market_snapshots(snapshots).values():
            implied_probability_total = best_market_implied_probability(market_snapshots)
            if implied_probability_total is not None and implied_probability_total <= Decimal("1") + self.near_arb_threshold:
                return True
        return False

    def has_significant_odds_movement(self, event_id: int, now: datetime) -> bool:
        snapshots = self.recent_snapshots(event_id, now)
        by_quote: dict[tuple[str, Decimal | None, int, str], list[OddsSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            key = (
                snapshot.market_type,
                snapshot.line,
                snapshot.bookmaker_id,
                snapshot.outcome_name,
            )
            by_quote[key].append(snapshot)

        for quote_snapshots in by_quote.values():
            if len(quote_snapshots) < 2:
                continue

            latest, previous = quote_snapshots[0], quote_snapshots[1]
            previous_odds = Decimal(str(previous.decimal_odds))
            if previous_odds <= Decimal("0"):
                continue

            latest_odds = Decimal(str(latest.decimal_odds))
            movement = abs(latest_odds - previous_odds) / previous_odds
            if movement >= self.near_arb_threshold:
                return True

        return False

    def recent_snapshots(self, event_id: int, now: datetime) -> list[OddsSnapshot]:
        cutoff = now - RECENT_SIGNAL_WINDOW
        return list(
            self.db.scalars(
                select(OddsSnapshot)
                .where(OddsSnapshot.event_id == event_id)
                .where(OddsSnapshot.captured_at >= cutoff)
                .where(OddsSnapshot.decimal_odds > Decimal("1"))
                .order_by(OddsSnapshot.captured_at.desc(), OddsSnapshot.id.desc())
            ).all()
        )

    def interval_for_priority(self, priority_level: str) -> timedelta:
        if priority_level == SCAN_PRIORITY_URGENT:
            return timedelta(seconds=self.settings.urgent_priority_scan_seconds)
        if priority_level == SCAN_PRIORITY_HIGH:
            return timedelta(seconds=self.settings.high_priority_scan_seconds)
        if priority_level == SCAN_PRIORITY_NORMAL:
            return timedelta(minutes=self.settings.normal_priority_scan_minutes)
        return timedelta(minutes=self.settings.low_priority_scan_minutes)

    def is_configured_sport(self, sport_key: str) -> bool:
        configured_sports = self.configured_sport_keys()
        if not configured_sports:
            return True
        return canonical_sport_key(sport_key) in configured_sports

    def configured_sport_keys(self) -> set[str]:
        return {canonical_sport_key(sport_key) for sport_key in self.settings.sport_key_list}


def group_latest_market_snapshots(
    snapshots: list[OddsSnapshot],
) -> dict[tuple[str, Decimal | None], list[OddsSnapshot]]:
    latest_by_quote: dict[tuple[str, Decimal | None, int, str], OddsSnapshot] = {}
    for snapshot in snapshots:
        key = (
            snapshot.market_type,
            snapshot.line,
            snapshot.bookmaker_id,
            snapshot.outcome_name,
        )
        if key not in latest_by_quote:
            latest_by_quote[key] = snapshot

    grouped: dict[tuple[str, Decimal | None], list[OddsSnapshot]] = defaultdict(list)
    for snapshot in latest_by_quote.values():
        grouped[(snapshot.market_type, snapshot.line)].append(snapshot)
    return dict(grouped)


def best_market_implied_probability(snapshots: list[OddsSnapshot]) -> Decimal | None:
    best_by_outcome: dict[str, Decimal] = {}
    for snapshot in snapshots:
        decimal_odds = Decimal(str(snapshot.decimal_odds))
        if decimal_odds <= Decimal("1"):
            continue

        current = best_by_outcome.get(snapshot.outcome_name)
        if current is None or decimal_odds > current:
            best_by_outcome[snapshot.outcome_name] = decimal_odds

    if len(best_by_outcome) not in SUPPORTED_OUTCOME_COUNTS:
        return None

    return sum((Decimal("1") / odds for odds in best_by_outcome.values()), Decimal("0"))


def is_lower_priority(priority_level: str, minimum_priority: str) -> bool:
    return PRIORITY_RANK[priority_level] < PRIORITY_RANK[minimum_priority]


def format_percent(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
