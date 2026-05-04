"""create market quality checks

Revision ID: 0008_quality_checks
Revises: 0007_scan_priorities
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_quality_checks"
down_revision: Union[str, None] = "0007_scan_priorities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_quality_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("market_type", sa.String(length=64), nullable=False),
        sa.Column("line", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("reasons", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_quality_checks_checked_at", "market_quality_checks", ["checked_at"], unique=False)
    op.create_index("ix_market_quality_checks_event_id", "market_quality_checks", ["event_id"], unique=False)
    op.create_index("ix_market_quality_checks_market_type", "market_quality_checks", ["market_type"], unique=False)
    op.create_index("ix_market_quality_checks_status", "market_quality_checks", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_market_quality_checks_status", table_name="market_quality_checks")
    op.drop_index("ix_market_quality_checks_market_type", table_name="market_quality_checks")
    op.drop_index("ix_market_quality_checks_event_id", table_name="market_quality_checks")
    op.drop_index("ix_market_quality_checks_checked_at", table_name="market_quality_checks")
    op.drop_table("market_quality_checks")
