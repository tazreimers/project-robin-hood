"""create opportunity executions

Revision ID: 0009_executions
Revises: 0008_quality_checks
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_executions"
down_revision: Union[str, None] = "0008_quality_checks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PLANNED", nullable=False),
        sa.Column("total_stake_planned", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_stake_actual", sa.Numeric(precision=12, scale=2), server_default="0", nullable=False),
        sa.Column("expected_profit", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("actual_profit", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["arbitrage_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunity_executions_opportunity_id", "opportunity_executions", ["opportunity_id"], unique=False)
    op.create_index("ix_opportunity_executions_status", "opportunity_executions", ["status"], unique=False)

    op.create_table(
        "execution_legs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execution_id", sa.Integer(), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("outcome_name", sa.String(length=255), nullable=False),
        sa.Column("recommended_odds", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("actual_odds", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("recommended_stake", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("actual_stake", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="PLANNED", nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["bookmaker_id"], ["bookmakers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["execution_id"], ["opportunity_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_legs_bookmaker_id", "execution_legs", ["bookmaker_id"], unique=False)
    op.create_index("ix_execution_legs_execution_id", "execution_legs", ["execution_id"], unique=False)
    op.create_index("ix_execution_legs_status", "execution_legs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_execution_legs_status", table_name="execution_legs")
    op.drop_index("ix_execution_legs_execution_id", table_name="execution_legs")
    op.drop_index("ix_execution_legs_bookmaker_id", table_name="execution_legs")
    op.drop_table("execution_legs")
    op.drop_index("ix_opportunity_executions_status", table_name="opportunity_executions")
    op.drop_index("ix_opportunity_executions_opportunity_id", table_name="opportunity_executions")
    op.drop_table("opportunity_executions")
