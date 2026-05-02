"""add opportunity validation fields

Revision ID: 0003_add_opportunity_validation
Revises: 0002_create_scan_runs
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_add_opportunity_validation"
down_revision: Union[str, None] = "0002_create_scan_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "arbitrage_opportunities",
        sa.Column("reliability_score", sa.Numeric(precision=5, scale=2), server_default="0", nullable=False),
    )
    op.add_column(
        "arbitrage_opportunities",
        sa.Column("validation_status", sa.String(length=32), server_default="STALE", nullable=False),
    )
    op.add_column(
        "arbitrage_opportunities",
        sa.Column("validation_reasons", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column(
        "arbitrage_opportunities",
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("arbitrage_opportunities", "last_validated_at")
    op.drop_column("arbitrage_opportunities", "validation_reasons")
    op.drop_column("arbitrage_opportunities", "validation_status")
    op.drop_column("arbitrage_opportunities", "reliability_score")
