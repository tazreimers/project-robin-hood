"""create action tracking

Revision ID: 0005_action_tracking
Revises: 0004_normalization_aliases
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_action_tracking"
down_revision: Union[str, None] = "0004_normalization_aliases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["arbitrage_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunity_actions_action_type", "opportunity_actions", ["action_type"], unique=False)
    op.create_index("ix_opportunity_actions_opportunity_id", "opportunity_actions", ["opportunity_id"], unique=False)

    op.create_table(
        "bet_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("outcome_name", sa.String(length=255), nullable=False),
        sa.Column("odds_taken", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("recommended_stake", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("actual_stake", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("result_status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("payout", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("profit_loss", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["bookmaker_id"], ["bookmakers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["arbitrage_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bet_records_bookmaker_id", "bet_records", ["bookmaker_id"], unique=False)
    op.create_index("ix_bet_records_opportunity_id", "bet_records", ["opportunity_id"], unique=False)
    op.create_index("ix_bet_records_result_status", "bet_records", ["result_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bet_records_result_status", table_name="bet_records")
    op.drop_index("ix_bet_records_opportunity_id", table_name="bet_records")
    op.drop_index("ix_bet_records_bookmaker_id", table_name="bet_records")
    op.drop_table("bet_records")
    op.drop_index("ix_opportunity_actions_opportunity_id", table_name="opportunity_actions")
    op.drop_index("ix_opportunity_actions_action_type", table_name="opportunity_actions")
    op.drop_table("opportunity_actions")
