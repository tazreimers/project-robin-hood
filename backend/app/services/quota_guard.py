from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.constants import THE_ODDS_API_DEFAULT_MARKETS
from app.models import ApiUsageLog, ScanRun
from app.providers.base import ProviderApiUsage


@dataclass(frozen=True)
class QuotaGuardDecision:
    allowed: bool
    estimated_cost: int
    reason: str | None = None


class QuotaGuard:
    provider_name = "the_odds_api"

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def check_scan_allowed(
        self,
        now: datetime | None = None,
        exclude_scan_run_id: int | None = None,
        sport_keys: list[str] | None = None,
    ) -> QuotaGuardDecision:
        """Decide whether a scan can run without exceeding local quota protections."""
        estimated_cost = self.estimate_scan_cost(sport_keys=sport_keys)
        if not self.settings.enable_quota_guard:
            return QuotaGuardDecision(allowed=True, estimated_cost=estimated_cost)

        checked_at = ensure_aware(now or datetime.now(timezone.utc))
        recent_scans = self.count_recent_scans(checked_at, exclude_scan_run_id=exclude_scan_run_id)
        if self.settings.max_scans_per_hour >= 0 and recent_scans >= self.settings.max_scans_per_hour:
            return QuotaGuardDecision(
                allowed=False,
                estimated_cost=estimated_cost,
                reason=(
                    "Scan blocked by quota guard: "
                    f"{recent_scans} scans already started in the last hour "
                    f"(limit {self.settings.max_scans_per_hour})."
                ),
            )

        usage_today = self.sum_usage_since(start_of_day_utc(checked_at))
        if self.settings.daily_quota_budget > 0 and usage_today + estimated_cost > self.settings.daily_quota_budget:
            return QuotaGuardDecision(
                allowed=False,
                estimated_cost=estimated_cost,
                reason=(
                    "Scan blocked by quota guard: estimated scan cost "
                    f"{estimated_cost} would exceed the daily quota budget "
                    f"({usage_today}/{self.settings.daily_quota_budget} already used)."
                ),
            )

        latest_log = self.latest_usage_log()
        if latest_log and latest_log.requests_remaining is not None:
            minimum_required = estimated_cost + self.settings.min_requests_remaining_buffer
            if latest_log.requests_remaining < minimum_required:
                return QuotaGuardDecision(
                    allowed=False,
                    estimated_cost=estimated_cost,
                    reason=(
                        "Scan blocked by quota guard: latest remaining quota "
                        f"{latest_log.requests_remaining} is below the required "
                        f"{minimum_required} credits (estimated scan cost {estimated_cost} "
                        f"+ buffer {self.settings.min_requests_remaining_buffer})."
                    ),
                )

        return QuotaGuardDecision(allowed=True, estimated_cost=estimated_cost)

    def estimate_scan_cost(
        self,
        sport_keys: list[str] | None = None,
        regions: str | None = None,
        markets: str | None = None,
    ) -> int:
        """Estimate provider credits for a scan before issuing API calls."""
        scan_sport_keys = sport_keys if sport_keys is not None else self.settings.sport_key_list
        request_cost = estimate_request_cost(
            regions=regions if regions is not None else self.settings.odds_regions,
            markets=markets if markets is not None else THE_ODDS_API_DEFAULT_MARKETS,
        )
        return len(scan_sport_keys) * request_cost

    def count_recent_scans(self, now: datetime, exclude_scan_run_id: int | None = None) -> int:
        one_hour_ago = now - timedelta(hours=1)
        query = select(ScanRun).where(
            ScanRun.started_at >= one_hour_ago,
            ScanRun.status.in_(("queued", "running", "completed", "failed")),
        )
        if exclude_scan_run_id is not None:
            query = query.where(ScanRun.id != exclude_scan_run_id)
        return len(list(self.db.scalars(query).all()))

    def latest_usage_log(self) -> ApiUsageLog | None:
        return self.db.scalar(
            select(ApiUsageLog)
            .where(ApiUsageLog.provider == self.provider_name)
            .order_by(ApiUsageLog.captured_at.desc(), ApiUsageLog.id.desc())
            .limit(1)
        )

    def sum_usage_since(self, since: datetime) -> int:
        logs = list(
            self.db.scalars(
                select(ApiUsageLog).where(
                    ApiUsageLog.provider == self.provider_name,
                    ApiUsageLog.captured_at >= since,
                )
            ).all()
        )
        return sum(log.requests_last if log.requests_last is not None else log.estimated_cost for log in logs)

    def log_api_response(self, usage: ProviderApiUsage) -> ApiUsageLog:
        log = ApiUsageLog(
            provider=usage.provider,
            endpoint=usage.endpoint,
            sport_key=usage.sport_key,
            regions=usage.regions,
            markets=usage.markets,
            requests_remaining=usage.requests_remaining,
            requests_used=usage.requests_used,
            requests_last=usage.requests_last,
            estimated_cost=usage.estimated_cost,
            captured_at=usage.captured_at,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def build_usage_report(self, limit: int = 50) -> dict[str, object]:
        latest_log = self.latest_usage_log()
        estimated_cost = self.estimate_scan_cost()
        estimated_scans_remaining = None
        if latest_log and latest_log.requests_remaining is not None and estimated_cost > 0:
            usable_remaining = latest_log.requests_remaining - self.settings.min_requests_remaining_buffer
            estimated_scans_remaining = max(0, usable_remaining // estimated_cost)

        usage_logs = list(
            self.db.scalars(
                select(ApiUsageLog)
                .where(ApiUsageLog.provider == self.provider_name)
                .order_by(ApiUsageLog.captured_at.desc(), ApiUsageLog.id.desc())
                .limit(limit)
            ).all()
        )

        return {
            "latest_remaining_quota": latest_log.requests_remaining if latest_log else None,
            "used_quota": latest_log.requests_used if latest_log else None,
            "last_request_cost": latest_log.requests_last if latest_log else None,
            "estimated_scans_remaining": estimated_scans_remaining,
            "usage_logs": usage_logs,
        }


def estimate_request_cost(regions: str, markets: str) -> int:
    """The Odds API charges by region x market for each sport odds request."""
    region_count = len([region.strip() for region in regions.split(",") if region.strip()])
    market_count = len([market.strip() for market in markets.split(",") if market.strip()])
    if region_count == 0 or market_count == 0:
        return 0
    return region_count * market_count


def start_of_day_utc(value: datetime) -> datetime:
    aware_value = ensure_aware(value)
    return datetime.combine(aware_value.date(), time.min, tzinfo=timezone.utc)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
