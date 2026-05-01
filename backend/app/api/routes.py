from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.jobs.celery_app import celery_app
from app.jobs.fetch_odds import fetch_odds as fetch_odds_job
from app.logging_utils import redact_secrets
from app.models import ArbitrageOpportunity, Bookmaker, Event, Sport
from app.schemas.health import HealthResponse
from app.schemas.jobs import JobStatusRead
from app.schemas.odds import ArbitrageOpportunityRead, BookmakerRead, EventRead, SportRead
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
