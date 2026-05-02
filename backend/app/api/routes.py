from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import get_db
from app.jobs.celery_app import celery_app
from app.jobs.detect_arbitrage import detect_arbitrage as detect_arbitrage_job
from app.jobs.fetch_odds import fetch_odds as fetch_odds_job
from app.jobs.scan_now import scan_now as scan_now_job
from app.logging_utils import redact_secrets
from app.models import (
    ArbitrageLeg,
    ArbitrageOpportunity,
    Bookmaker,
    Event,
    MarketAlias,
    OddsSnapshot,
    ScanRun,
    Sport,
    TeamAlias,
)
from app.schemas.health import HealthResponse
from app.schemas.jobs import JobStatusRead
from app.schemas.odds import (
    ActiveArbitrageLegRead,
    ActiveArbitrageOpportunityRead,
    ArbitrageOpportunityRead,
    BookmakerRead,
    EventRead,
    MarketAliasCreate,
    MarketAliasRead,
    OpportunityInstructionLegRead,
    OpportunityInstructionsRead,
    SportRead,
    TeamAliasCreate,
    TeamAliasRead,
)
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

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return get_health()


@router.post("/scan", response_model=ScanRunRead, status_code=202)
def run_scan_now(db: Session = Depends(get_db)) -> ScanRun:
    scanner = ScannerService(db)
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
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/jobs/fetch-odds", status_code=202)
def enqueue_fetch_odds() -> dict[str, str]:
    task = fetch_odds_job.delay()
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
