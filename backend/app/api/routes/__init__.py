from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.core.constants import (
    MONEY_PRECISION,
    PROBABILITY_PRECISION,
    SUPPORTED_OPPORTUNITY_ACTION_TYPES,
)
from app.core.logging import redact_secrets
from app.jobs.celery_app import celery_app
from app.jobs.adaptive_scan import adaptive_scan as adaptive_scan_job
from app.jobs.detect_arbitrage import detect_arbitrage as detect_arbitrage_job
from app.jobs.fetch_odds import fetch_odds as fetch_odds_job
from app.jobs.scan_now import scan_now as scan_now_job
from app.models import (
    ArbitrageLeg,
    ArbitrageOpportunity,
    BetRecord,
    Bookmaker,
    Event,
    EventScanPriority,
    MarketAlias,
    OddsSnapshot,
    OpportunityAction,
    ScanRun,
    Sport,
    TeamAlias,
)
from app.schemas.api_usage import ApiUsageRead
from app.schemas.health import HealthResponse
from app.schemas.jobs import JobStatusRead
from app.schemas.odds import (
    ActiveArbitrageLegRead,
    ActiveArbitrageOpportunityRead,
    ArbitrageOpportunityRead,
    BetRecordCreate,
    BetRecordPatch,
    BetRecordRead,
    BookmakerRead,
    EventRead,
    MarketAliasCreate,
    MarketAliasRead,
    OpportunityInstructionLegRead,
    OpportunityInstructionsRead,
    OpportunityActionCreate,
    OpportunityActionRead,
    SportRead,
    TeamAliasCreate,
    TeamAliasRead,
)
from app.schemas.scan_priority import EventScanPriorityRead
from app.schemas.dashboard import BookmakerPairMetricRead, DashboardMetricsRead, RecentActivityRead
from app.schemas.scanner import ScanRunRead
from app.services.health import get_health
from app.services.normalization import canonical_sport_key, cleanup_key
from app.services.opportunity_validator import (
    FRESH,
    RISKY,
    STALE,
    OpportunityValidationResult,
    OpportunityValidator,
    ensure_aware,
)
from app.services.scanner import ScannerService
from app.services.quota_guard import QuotaGuard
from app.services.scan_scheduler import ScanScheduler

router = APIRouter()

REQUIRED_BET_RECORD_FIELDS = {
    "bookmaker_id",
    "outcome_name",
    "odds_taken",
    "recommended_stake",
    "actual_stake",
    "result_status",
}


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return get_health()


@router.post("/scan", response_model=ScanRunRead, status_code=202)
def run_scan_now(db: Session = Depends(get_db)) -> ScanRun:
    scanner = ScannerService(db)
    quota_decision = QuotaGuard(db).check_scan_allowed()
    if not quota_decision.allowed:
        scan_run = scanner.create_blocked_scan_run(quota_decision.reason or "Scan blocked by quota guard")
        db.commit()
        db.refresh(scan_run)
        return scan_run

    scan_run = scanner.create_scan_run()
    db.commit()
    db.refresh(scan_run)
    scan_now_job.delay(scan_run.id)
    return scan_run


@router.get("/scan-runs", response_model=list[ScanRunRead])
def list_scan_runs(db: Session = Depends(get_db)) -> list[ScanRun]:
    return list(db.scalars(select(ScanRun).order_by(ScanRun.started_at.desc())).all())


@router.get("/scan-runs/{scan_run_id}", response_model=ScanRunRead)
def get_scan_run(scan_run_id: int, db: Session = Depends(get_db)) -> ScanRun:
    scan_run = db.get(ScanRun, scan_run_id)
    if scan_run is None:
        raise HTTPException(status_code=404, detail="Scan run not found")
    return scan_run


@router.get("/api-usage", response_model=ApiUsageRead)
def get_api_usage(db: Session = Depends(get_db)) -> dict[str, object]:
    return QuotaGuard(db).build_usage_report()


@router.get("/scan-priorities", response_model=list[EventScanPriorityRead])
def list_scan_priorities(db: Session = Depends(get_db)) -> list[EventScanPriority]:
    scheduler = ScanScheduler(db)
    scheduler.refresh_priorities()
    db.commit()
    return scheduler.list_priorities()


@router.get("/bookmakers", response_model=list[BookmakerRead])
def list_bookmakers(db: Session = Depends(get_db)) -> list[Bookmaker]:
    return list(db.scalars(select(Bookmaker).order_by(Bookmaker.name)).all())


@router.get("/sports", response_model=list[SportRead])
def list_sports(db: Session = Depends(get_db)) -> list[Sport]:
    return list(db.scalars(select(Sport).order_by(Sport.name)).all())


@router.get("/aliases/teams", response_model=list[TeamAliasRead])
def list_team_aliases(db: Session = Depends(get_db)) -> list[TeamAlias]:
    return list(
        db.scalars(
            select(TeamAlias).order_by(TeamAlias.sport_key, TeamAlias.canonical_name, TeamAlias.alias)
        ).all()
    )


@router.post("/aliases/teams", response_model=TeamAliasRead, status_code=201)
def create_team_alias(payload: TeamAliasCreate, db: Session = Depends(get_db)) -> TeamAlias:
    team_alias = TeamAlias(
        sport_key=canonical_sport_key(payload.sport_key),
        canonical_name=payload.canonical_name.strip(),
        alias=payload.alias.strip(),
    )
    db.add(team_alias)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Team alias already exists") from exc

    db.refresh(team_alias)
    return team_alias


@router.get("/aliases/markets", response_model=list[MarketAliasRead])
def list_market_aliases(db: Session = Depends(get_db)) -> list[MarketAlias]:
    return list(
        db.scalars(
            select(MarketAlias).order_by(
                MarketAlias.provider,
                MarketAlias.canonical_market_type,
                MarketAlias.source_market_name,
            )
        ).all()
    )


@router.post("/aliases/markets", response_model=MarketAliasRead, status_code=201)
def create_market_alias(payload: MarketAliasCreate, db: Session = Depends(get_db)) -> MarketAlias:
    market_alias = MarketAlias(
        provider=cleanup_key(payload.provider),
        source_market_name=payload.source_market_name.strip(),
        canonical_market_type=payload.canonical_market_type.strip(),
    )
    db.add(market_alias)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Market alias already exists") from exc

    db.refresh(market_alias)
    return market_alias


@router.get("/events", response_model=list[EventRead])
def list_events(db: Session = Depends(get_db)) -> list[Event]:
    return list(db.scalars(select(Event).order_by(Event.start_time)).all())


@router.get("/dashboard/metrics", response_model=DashboardMetricsRead)
def get_dashboard_metrics(db: Session = Depends(get_db)) -> DashboardMetricsRead:
    return build_dashboard_metrics(db)


@router.get("/opportunities", response_model=list[ArbitrageOpportunityRead])
def list_opportunities(db: Session = Depends(get_db)) -> list[ArbitrageOpportunity]:
    query = (
        select(ArbitrageOpportunity)
        .options(selectinload(ArbitrageOpportunity.legs))
        .order_by(ArbitrageOpportunity.detected_at.desc())
    )
    return list(db.scalars(query).all())


@router.get("/opportunities/active", response_model=list[ActiveArbitrageOpportunityRead])
def list_active_opportunities(
    include_stale: bool = False,
    db: Session = Depends(get_db),
) -> list[ActiveArbitrageOpportunityRead]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    query = (
        select(ArbitrageOpportunity)
        .options(
            selectinload(ArbitrageOpportunity.event),
            selectinload(ArbitrageOpportunity.legs).selectinload(ArbitrageLeg.bookmaker),
        )
        .where(ArbitrageOpportunity.status == "open")
        .order_by(ArbitrageOpportunity.detected_at.desc())
    )

    allowed_statuses = {FRESH, RISKY}
    if include_stale:
        allowed_statuses.add(STALE)

    validator = OpportunityValidator(db, settings=settings)
    responses: list[ActiveArbitrageOpportunityRead] = []
    for opportunity in db.scalars(query).all():
        validation = validator.validate_and_apply(opportunity, now=now)
        if validation.recommended_status not in allowed_statuses:
            continue

        responses.append(build_active_opportunity_response(opportunity=opportunity, validation=validation))

    db.commit()
    return responses


@router.get("/opportunities/{opportunity_id}", response_model=ArbitrageOpportunityRead)
def get_opportunity(opportunity_id: int, db: Session = Depends(get_db)) -> ArbitrageOpportunity:
    query = (
        select(ArbitrageOpportunity)
        .options(selectinload(ArbitrageOpportunity.legs))
        .where(ArbitrageOpportunity.id == opportunity_id)
    )
    opportunity = db.scalar(query)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    return opportunity


@router.get("/opportunities/{opportunity_id}/instructions", response_model=OpportunityInstructionsRead)
def get_opportunity_instructions(
    opportunity_id: int,
    db: Session = Depends(get_db),
) -> OpportunityInstructionsRead:
    opportunity = get_opportunity_with_details(opportunity_id, db)
    return build_opportunity_instructions(opportunity=opportunity, db=db, now=datetime.now(timezone.utc))


@router.post("/opportunities/{opportunity_id}/mark-actioned", response_model=ArbitrageOpportunityRead)
def mark_opportunity_actioned(opportunity_id: int, db: Session = Depends(get_db)) -> ArbitrageOpportunity:
    opportunity = get_opportunity_with_details(opportunity_id, db)
    opportunity.status = "ACTIONED"
    add_opportunity_action(db, opportunity_id=opportunity.id, action_type="ACTIONED", notes="Marked as actioned")
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/opportunities/{opportunity_id}/actions", response_model=OpportunityActionRead, status_code=201)
def create_opportunity_action(
    opportunity_id: int,
    payload: OpportunityActionCreate,
    db: Session = Depends(get_db),
) -> OpportunityAction:
    get_existing_opportunity(opportunity_id, db)
    action = add_opportunity_action(
        db,
        opportunity_id=opportunity_id,
        action_type=payload.action_type,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(action)
    return action


@router.post("/opportunities/{opportunity_id}/bet-records", response_model=BetRecordRead, status_code=201)
def create_bet_record(
    opportunity_id: int,
    payload: BetRecordCreate,
    db: Session = Depends(get_db),
) -> BetRecord:
    get_existing_opportunity(opportunity_id, db)
    get_existing_bookmaker(payload.bookmaker_id, db)
    outcome_name = payload.outcome_name.strip()
    if not outcome_name:
        raise HTTPException(status_code=400, detail="Outcome name is required")

    bet_record = BetRecord(
        opportunity_id=opportunity_id,
        bookmaker_id=payload.bookmaker_id,
        outcome_name=outcome_name,
        odds_taken=payload.odds_taken,
        recommended_stake=payload.recommended_stake,
        actual_stake=payload.actual_stake,
        result_status=payload.result_status.strip().upper(),
        payout=payload.payout,
        profit_loss=payload.profit_loss,
        settled_at=payload.settled_at,
    )
    db.add(bet_record)
    db.commit()
    db.refresh(bet_record)
    return bet_record


@router.patch("/bet-records/{bet_record_id}", response_model=BetRecordRead)
def update_bet_record(
    bet_record_id: int,
    payload: BetRecordPatch,
    db: Session = Depends(get_db),
) -> BetRecord:
    bet_record = db.get(BetRecord, bet_record_id)
    if bet_record is None:
        raise HTTPException(status_code=404, detail="Bet record not found")

    updates = payload.model_dump(exclude_unset=True)
    if "bookmaker_id" in updates and updates["bookmaker_id"] is not None:
        get_existing_bookmaker(updates["bookmaker_id"], db)

    for field, value in updates.items():
        if field in REQUIRED_BET_RECORD_FIELDS and value is None:
            raise HTTPException(status_code=400, detail=f"{field} cannot be null")
        if field in {"outcome_name", "result_status"} and isinstance(value, str):
            value = value.strip()
            if not value:
                raise HTTPException(status_code=400, detail=f"{field} is required")
            if field == "result_status":
                value = value.upper()
        setattr(bet_record, field, value)

    db.commit()
    db.refresh(bet_record)
    return bet_record


@router.post("/jobs/fetch-odds", status_code=202)
def enqueue_fetch_odds() -> dict[str, str]:
    task = fetch_odds_job.delay()
    return {"status": "queued", "task_id": task.id}


@router.post("/jobs/adaptive-scan", status_code=202)
def enqueue_adaptive_scan() -> dict[str, str]:
    task = adaptive_scan_job.delay()
    return {"status": "queued", "task_id": task.id}


@router.post("/jobs/detect-arbitrage", status_code=202)
def enqueue_detect_arbitrage() -> dict[str, str]:
    task = detect_arbitrage_job.delay()
    return {"status": "queued", "task_id": task.id}


@router.get("/jobs/{task_id}", response_model=JobStatusRead)
def get_job_status(task_id: str) -> JobStatusRead:
    task = celery_app.AsyncResult(task_id)
    result = task.result if task.ready() else None

    if task.successful() and isinstance(result, dict):
        return JobStatusRead(
            task_id=task_id,
            state=task.state,
            ready=True,
            successful=True,
            result=result,
        )

    return JobStatusRead(
        task_id=task_id,
        state=task.state,
        ready=task.ready(),
        successful=task.successful(),
        error=redact_secrets(result) if task.failed() and result is not None else None,
    )


def add_opportunity_action(
    db: Session,
    opportunity_id: int,
    action_type: str,
    notes: str | None = None,
) -> OpportunityAction:
    normalized_action_type = action_type.strip().upper()
    if normalized_action_type not in SUPPORTED_OPPORTUNITY_ACTION_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported action type")

    opportunity = get_existing_opportunity(opportunity_id, db)
    if normalized_action_type == "ACTIONED":
        opportunity.status = "ACTIONED"
    elif normalized_action_type == "EXPIRED":
        opportunity.status = "expired"

    action = OpportunityAction(
        opportunity_id=opportunity_id,
        action_type=normalized_action_type,
        notes=notes.strip() if notes else None,
    )
    db.add(action)
    db.flush()
    return action


def get_existing_opportunity(opportunity_id: int, db: Session) -> ArbitrageOpportunity:
    opportunity = db.get(ArbitrageOpportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity


def get_existing_bookmaker(bookmaker_id: int, db: Session) -> Bookmaker:
    bookmaker = db.get(Bookmaker, bookmaker_id)
    if bookmaker is None:
        raise HTTPException(status_code=404, detail="Bookmaker not found")
    return bookmaker


def build_dashboard_metrics(db: Session) -> DashboardMetricsRead:
    opportunities = list(
        db.scalars(
            select(ArbitrageOpportunity).options(
                selectinload(ArbitrageOpportunity.legs).selectinload(ArbitrageLeg.bookmaker)
            )
        ).all()
    )
    actions = list(db.scalars(select(OpportunityAction)).all())
    bet_records = list(db.scalars(select(BetRecord)).all())
    recent_actions = list(
        db.scalars(select(OpportunityAction).order_by(OpportunityAction.created_at.desc()).limit(10)).all()
    )

    actioned_opportunity_ids = {
        action.opportunity_id for action in actions if action.action_type == "ACTIONED"
    } | {opportunity.id for opportunity in opportunities if opportunity.status == "ACTIONED"}
    expired_opportunity_ids = {
        action.opportunity_id for action in actions if action.action_type == "EXPIRED"
    } | {
        opportunity.id
        for opportunity in opportunities
        if opportunity.status == "expired" or opportunity.validation_status == "EXPIRED"
    }

    margins = [Decimal(str(opportunity.margin)) for opportunity in opportunities]
    odds_ages = [
        Decimal(str(odds_age))
        for opportunity in opportunities
        for odds_age in [extract_odds_age(opportunity)]
        if odds_age is not None
    ]

    return DashboardMetricsRead(
        total_opportunities_found=len(opportunities),
        opportunities_actioned=len(actioned_opportunity_ids),
        expired_before_action=len(expired_opportunity_ids - actioned_opportunity_ids),
        total_recommended_profit=quantize_money(
            sum((Decimal(str(opportunity.guaranteed_profit)) for opportunity in opportunities), Decimal("0"))
        ),
        actual_profit_loss=quantize_money(
            sum(
                (Decimal(str(record.profit_loss)) for record in bet_records if record.profit_loss is not None),
                Decimal("0"),
            )
        ),
        average_margin=average_decimal(margins, PROBABILITY_PRECISION),
        average_odds_age=average_decimal(odds_ages, Decimal("0.01")),
        best_bookmaker_pairs=build_bookmaker_pair_metrics(opportunities),
        recent_activity=[
            RecentActivityRead(
                id=action.id,
                opportunity_id=action.opportunity_id,
                action_type=action.action_type,
                notes=action.notes,
                created_at=action.created_at,
            )
            for action in recent_actions
        ],
    )


def build_bookmaker_pair_metrics(
    opportunities: list[ArbitrageOpportunity],
) -> list[BookmakerPairMetricRead]:
    pair_metrics: dict[tuple[str, ...], dict[str, Decimal | int]] = defaultdict(
        lambda: {"opportunities": 0, "total_recommended_profit": Decimal("0"), "margin_total": Decimal("0")}
    )

    for opportunity in opportunities:
        bookmaker_names = tuple(
            sorted({leg.bookmaker.name for leg in opportunity.legs if leg.bookmaker is not None})
        )
        if len(bookmaker_names) < 2:
            continue

        pair_metrics[bookmaker_names]["opportunities"] += 1
        pair_metrics[bookmaker_names]["total_recommended_profit"] += Decimal(str(opportunity.guaranteed_profit))
        pair_metrics[bookmaker_names]["margin_total"] += Decimal(str(opportunity.margin))

    metrics = [
        BookmakerPairMetricRead(
            bookmaker_pair=list(bookmaker_pair),
            opportunities=int(values["opportunities"]),
            total_recommended_profit=quantize_money(Decimal(str(values["total_recommended_profit"]))),
            average_margin=(Decimal(str(values["margin_total"])) / Decimal(str(values["opportunities"]))).quantize(
                PROBABILITY_PRECISION,
                rounding=ROUND_HALF_UP,
            ),
        )
        for bookmaker_pair, values in pair_metrics.items()
    ]
    return sorted(
        metrics,
        key=lambda metric: (metric.opportunities, metric.total_recommended_profit),
        reverse=True,
    )[:5]


def extract_odds_age(opportunity: ArbitrageOpportunity) -> int | float | str | None:
    validation_reasons = opportunity.validation_reasons or {}
    if not isinstance(validation_reasons, dict):
        return None
    odds_age = validation_reasons.get("odds_age_seconds")
    if odds_age in ("", None):
        return None
    return odds_age if isinstance(odds_age, (int, float, str)) else None


def average_decimal(values: list[Decimal], precision: Decimal) -> Decimal | None:
    if not values:
        return None
    return (sum(values, Decimal("0")) / Decimal(str(len(values)))).quantize(precision, rounding=ROUND_HALF_UP)


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


def build_active_opportunity_response(
    opportunity: ArbitrageOpportunity,
    validation: OpportunityValidationResult,
) -> ActiveArbitrageOpportunityRead:
    return ActiveArbitrageOpportunityRead(
        id=opportunity.id,
        event=EventRead.model_validate(opportunity.event),
        market_type=opportunity.market_type,
        line=opportunity.line,
        implied_probability_total=opportunity.implied_probability_total,
        margin=opportunity.margin,
        total_stake=opportunity.total_stake,
        guaranteed_profit=opportunity.guaranteed_profit,
        guaranteed_return=opportunity.guaranteed_return,
        detected_at=opportunity.detected_at,
        latest_snapshot_at=validation.latest_snapshot_at,
        odds_age_seconds=validation.odds_age_seconds,
        freshness_status=validation.recommended_status.lower(),
        reliability_score=opportunity.reliability_score,
        validation_status=opportunity.validation_status,
        validation_reasons=opportunity.validation_reasons,
        last_validated_at=opportunity.last_validated_at,
        legs=[
            ActiveArbitrageLegRead(
                id=leg.id,
                bookmaker=BookmakerRead.model_validate(leg.bookmaker),
                outcome_name=leg.outcome_name,
                decimal_odds=leg.decimal_odds,
                stake=leg.stake,
                expected_return=leg.expected_return,
            )
            for leg in opportunity.legs
        ],
    )


def get_opportunity_with_details(opportunity_id: int, db: Session) -> ArbitrageOpportunity:
    query = (
        select(ArbitrageOpportunity)
        .options(
            selectinload(ArbitrageOpportunity.event),
            selectinload(ArbitrageOpportunity.legs).selectinload(ArbitrageLeg.bookmaker),
        )
        .where(ArbitrageOpportunity.id == opportunity_id)
    )
    opportunity = db.scalar(query)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity


def build_opportunity_instructions(
    opportunity: ArbitrageOpportunity,
    db: Session,
    now: datetime,
) -> OpportunityInstructionsRead:
    instruction_legs: list[OpportunityInstructionLegRead] = []

    for leg in opportunity.legs:
        source_last_seen_at = get_leg_source_last_seen_at(db, opportunity, leg)
        odds_age_seconds: int | None = None
        if source_last_seen_at is not None:
            source_last_seen_at = ensure_aware(source_last_seen_at)
            odds_age_seconds = max(0, int((now - source_last_seen_at).total_seconds()))

        instruction = (
            f"Bet AUD {leg.stake} on {leg.outcome_name} at {leg.bookmaker.name} "
            f"only if decimal odds are still {leg.decimal_odds} or better."
        )
        instruction_legs.append(
            OpportunityInstructionLegRead(
                id=leg.id,
                bookmaker=BookmakerRead.model_validate(leg.bookmaker),
                outcome_name=leg.outcome_name,
                decimal_odds=leg.decimal_odds,
                stake=leg.stake,
                expected_return=leg.expected_return,
                source_last_seen_at=source_last_seen_at,
                odds_age_seconds=odds_age_seconds,
                instruction=instruction,
            )
        )

    return OpportunityInstructionsRead(
        id=opportunity.id,
        event=EventRead.model_validate(opportunity.event),
        market=opportunity.market_type,
        line=opportunity.line,
        total_stake=opportunity.total_stake,
        guaranteed_profit=opportunity.guaranteed_profit,
        guaranteed_return=opportunity.guaranteed_return,
        margin=opportunity.margin,
        legs=instruction_legs,
        instructions=[
            "Open each bookmaker manually before placing any bet.",
            "Confirm the event, market, outcome, and decimal odds for every leg.",
            "Place all listed stakes only if every quoted price is still available or better.",
            "Do not place any leg unless you can place every leg in the opportunity.",
        ],
        warning="Re-check odds manually before placing any bet. Do not place a bet if the odds have changed.",
    )


def get_leg_source_last_seen_at(
    db: Session,
    opportunity: ArbitrageOpportunity,
    leg: ArbitrageLeg,
) -> datetime | None:
    query = (
        select(func.max(OddsSnapshot.captured_at))
        .where(OddsSnapshot.event_id == opportunity.event_id)
        .where(OddsSnapshot.market_type == opportunity.market_type)
        .where(OddsSnapshot.bookmaker_id == leg.bookmaker_id)
        .where(OddsSnapshot.outcome_name == leg.outcome_name)
        .where(OddsSnapshot.decimal_odds == leg.decimal_odds)
    )
    query = query.where(OddsSnapshot.line.is_(None)) if opportunity.line is None else query.where(
        OddsSnapshot.line == opportunity.line
    )
    return db.scalar(query)
