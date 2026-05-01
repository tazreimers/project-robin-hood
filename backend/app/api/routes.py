from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db import get_db
from app.jobs.celery_app import celery_app
from app.jobs.detect_arbitrage import detect_arbitrage as detect_arbitrage_job
from app.jobs.fetch_odds import fetch_odds as fetch_odds_job
from app.logging_utils import redact_secrets
from app.models import ArbitrageLeg, ArbitrageOpportunity, Bookmaker, Event, OddsSnapshot, Sport
from app.schemas.health import HealthResponse
from app.schemas.jobs import JobStatusRead
from app.schemas.odds import (
    ActiveArbitrageLegRead,
    ActiveArbitrageOpportunityRead,
    ArbitrageOpportunityRead,
    BookmakerRead,
    EventRead,
    SportRead,
)
from app.services.arbitrage import ensure_aware
from app.services.health import get_health

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return get_health()


@router.get("/bookmakers", response_model=list[BookmakerRead])
def list_bookmakers(db: Session = Depends(get_db)) -> list[Bookmaker]:
    return list(db.scalars(select(Bookmaker).order_by(Bookmaker.name)).all())


@router.get("/sports", response_model=list[SportRead])
def list_sports(db: Session = Depends(get_db)) -> list[Sport]:
    return list(db.scalars(select(Sport).order_by(Sport.name)).all())


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
def list_active_opportunities(db: Session = Depends(get_db)) -> list[ActiveArbitrageOpportunityRead]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    query = (
        select(ArbitrageOpportunity)
        .options(
            selectinload(ArbitrageOpportunity.event),
            selectinload(ArbitrageOpportunity.legs).selectinload(ArbitrageLeg.bookmaker),
        )
        .where(ArbitrageOpportunity.status == "open")
        .where(or_(ArbitrageOpportunity.expires_at.is_(None), ArbitrageOpportunity.expires_at > now))
        .order_by(ArbitrageOpportunity.detected_at.desc())
    )

    return [
        build_active_opportunity_response(
            opportunity=opportunity,
            db=db,
            now=now,
            max_odds_age_seconds=settings.max_odds_age_seconds,
        )
        for opportunity in db.scalars(query).all()
    ]


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
    db: Session,
    now: datetime,
    max_odds_age_seconds: int,
) -> ActiveArbitrageOpportunityRead:
    latest_snapshot_at = get_latest_snapshot_at(db, opportunity)
    odds_age_seconds: int | None = None
    freshness_status = "stale"

    if latest_snapshot_at is not None:
        latest_snapshot_at = ensure_aware(latest_snapshot_at)
        odds_age_seconds = max(0, int((now - latest_snapshot_at).total_seconds()))
        if odds_age_seconds <= max_odds_age_seconds:
            freshness_status = "fresh"

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
        latest_snapshot_at=latest_snapshot_at,
        odds_age_seconds=odds_age_seconds,
        freshness_status=freshness_status,
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


def get_latest_snapshot_at(db: Session, opportunity: ArbitrageOpportunity) -> datetime | None:
    query = select(func.max(OddsSnapshot.captured_at)).where(
        OddsSnapshot.event_id == opportunity.event_id,
        OddsSnapshot.market_type == opportunity.market_type,
    )
    query = query.where(OddsSnapshot.line.is_(None)) if opportunity.line is None else query.where(
        OddsSnapshot.line == opportunity.line
    )
    return db.scalar(query)
