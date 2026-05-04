from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import (
    EXECUTION_LEG_STATUS_ODDS_CHANGED,
    EXECUTION_LEG_STATUS_PLACED,
    EXECUTION_LEG_STATUS_PLANNED,
    EXECUTION_LEG_STATUS_SKIPPED,
    EXECUTION_LEG_STATUSES,
    EXECUTION_STATUS_ACTIONED,
    EXECUTION_STATUS_ODDS_CHANGED,
    EXECUTION_STATUS_PARTIALLY_ACTIONED,
    EXECUTION_STATUS_PLANNED,
    EXECUTION_STATUS_SETTLED,
    EXECUTION_STATUS_SKIPPED,
    EXECUTION_STATUSES,
    MONEY_PRECISION,
)
from app.models import ArbitrageLeg, ArbitrageOpportunity, ExecutionLeg, OpportunityExecution
from app.schemas.execution import ExecutionLegPatch, OpportunityExecutionCreate, OpportunityExecutionPatch


class ExecutionNotFoundError(ValueError):
    pass


class ExecutionValidationError(ValueError):
    pass


class OpportunityExecutionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_execution(self, opportunity_id: int, payload: OpportunityExecutionCreate) -> OpportunityExecution:
        opportunity = self.get_opportunity_with_legs(opportunity_id)
        if opportunity is None:
            raise ExecutionNotFoundError("Opportunity not found")
        if not opportunity.legs:
            raise ExecutionValidationError("Opportunity has no execution legs")

        execution = OpportunityExecution(
            opportunity_id=opportunity.id,
            status=EXECUTION_STATUS_PLANNED,
            total_stake_planned=quantize_money(
                sum((Decimal(str(leg.stake)) for leg in opportunity.legs), Decimal("0"))
            ),
            total_stake_actual=Decimal("0.00"),
            expected_profit=quantize_money(Decimal(str(opportunity.guaranteed_profit))),
            actual_profit=None,
            notes=clean_notes(payload.notes),
        )
        execution.legs = [
            ExecutionLeg(
                bookmaker_id=leg.bookmaker_id,
                outcome_name=leg.outcome_name,
                recommended_odds=Decimal(str(leg.decimal_odds)),
                actual_odds=None,
                recommended_stake=Decimal(str(leg.stake)),
                actual_stake=None,
                status=EXECUTION_LEG_STATUS_PLANNED,
                notes=None,
            )
            for leg in sorted(opportunity.legs, key=lambda item: item.id)
        ]
        self.db.add(execution)
        self.db.flush()
        return self.get_execution(execution.id) or execution

    def list_executions(self) -> list[OpportunityExecution]:
        return list(
            self.db.scalars(
                select(OpportunityExecution)
                .options(selectinload(OpportunityExecution.legs).selectinload(ExecutionLeg.bookmaker))
                .order_by(OpportunityExecution.created_at.desc(), OpportunityExecution.id.desc())
            ).all()
        )

    def get_execution(self, execution_id: int) -> OpportunityExecution | None:
        return self.db.scalar(
            select(OpportunityExecution)
            .options(selectinload(OpportunityExecution.legs).selectinload(ExecutionLeg.bookmaker))
            .where(OpportunityExecution.id == execution_id)
        )

    def update_execution(
        self,
        execution_id: int,
        payload: OpportunityExecutionPatch,
    ) -> OpportunityExecution:
        execution = self.get_execution(execution_id)
        if execution is None:
            raise ExecutionNotFoundError("Execution not found")

        updates = payload.model_dump(exclude_unset=True)
        manual_status = updates.pop("status", None)
        if "notes" in updates:
            execution.notes = clean_notes(updates["notes"])

        self.recalculate_execution(execution)
        if manual_status is not None:
            execution.status = normalize_execution_status(manual_status)

        self.db.flush()
        return self.get_execution(execution.id) or execution

    def update_leg(
        self,
        execution_id: int,
        leg_id: int,
        payload: ExecutionLegPatch,
    ) -> OpportunityExecution:
        execution = self.get_execution(execution_id)
        if execution is None:
            raise ExecutionNotFoundError("Execution not found")

        leg = next((candidate for candidate in execution.legs if candidate.id == leg_id), None)
        if leg is None:
            raise ExecutionNotFoundError("Execution leg not found")

        updates = payload.model_dump(exclude_unset=True)
        if "status" in updates and updates["status"] is not None:
            leg.status = normalize_leg_status(updates["status"])
        if "actual_odds" in updates:
            actual_odds = updates["actual_odds"]
            leg.actual_odds = Decimal(str(actual_odds)) if actual_odds is not None else None
        if "actual_stake" in updates:
            actual_stake = updates["actual_stake"]
            leg.actual_stake = Decimal(str(actual_stake)) if actual_stake is not None else None
        if "notes" in updates:
            leg.notes = clean_notes(updates["notes"])

        self.recalculate_execution(execution)
        self.db.flush()
        return self.get_execution(execution.id) or execution

    def recalculate_execution(self, execution: OpportunityExecution) -> None:
        execution.total_stake_planned = quantize_money(
            sum((Decimal(str(leg.recommended_stake)) for leg in execution.legs), Decimal("0"))
        )

        placed_legs = [leg for leg in execution.legs if leg.status == EXECUTION_LEG_STATUS_PLACED]
        execution.total_stake_actual = quantize_money(
            sum((Decimal(str(leg.actual_stake)) for leg in placed_legs if leg.actual_stake is not None), Decimal("0"))
        )

        complete_placed_legs = [
            leg
            for leg in placed_legs
            if leg.actual_odds is not None and leg.actual_stake is not None and Decimal(str(leg.actual_stake)) > 0
        ]
        if execution.legs and len(complete_placed_legs) == len(execution.legs):
            minimum_return = min(
                Decimal(str(leg.actual_odds)) * Decimal(str(leg.actual_stake)) for leg in complete_placed_legs
            )
            execution.actual_profit = quantize_money(minimum_return - Decimal(str(execution.total_stake_actual)))
        else:
            execution.actual_profit = None

        execution.status = derive_execution_status(execution)

    def get_opportunity_with_legs(self, opportunity_id: int) -> ArbitrageOpportunity | None:
        return self.db.scalar(
            select(ArbitrageOpportunity)
            .options(selectinload(ArbitrageOpportunity.legs).selectinload(ArbitrageLeg.bookmaker))
            .where(ArbitrageOpportunity.id == opportunity_id)
        )


def derive_execution_status(execution: OpportunityExecution) -> str:
    if execution.status == EXECUTION_STATUS_SETTLED:
        return EXECUTION_STATUS_SETTLED

    leg_statuses = [leg.status for leg in execution.legs]
    if not leg_statuses or all(status == EXECUTION_LEG_STATUS_PLANNED for status in leg_statuses):
        return EXECUTION_STATUS_PLANNED
    if all(status == EXECUTION_LEG_STATUS_SKIPPED for status in leg_statuses):
        return EXECUTION_STATUS_SKIPPED
    if any(status == EXECUTION_LEG_STATUS_ODDS_CHANGED for status in leg_statuses):
        return EXECUTION_STATUS_ODDS_CHANGED
    if all(status == EXECUTION_LEG_STATUS_PLACED for status in leg_statuses):
        return EXECUTION_STATUS_ACTIONED
    if any(status in {EXECUTION_LEG_STATUS_PLACED, EXECUTION_LEG_STATUS_SKIPPED} for status in leg_statuses):
        return EXECUTION_STATUS_PARTIALLY_ACTIONED
    return EXECUTION_STATUS_PLANNED


def normalize_execution_status(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in EXECUTION_STATUSES:
        raise ExecutionValidationError("Unsupported execution status")
    return normalized


def normalize_leg_status(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in EXECUTION_LEG_STATUSES:
        raise ExecutionValidationError("Unsupported execution leg status")
    return normalized


def clean_notes(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def quantize_money(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)
