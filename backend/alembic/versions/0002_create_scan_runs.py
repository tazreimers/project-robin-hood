"""create scan runs

Revision ID: 0002_create_scan_runs
Revises: 0001_create_scanner_tables
Create Date: 2026-05-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_create_scan_runs"
down_revision: Union[str, None] = "0001_create_scanner_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("sports_scanned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("events_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("markets_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("snapshots_saved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("opportunities_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_runs_started_at", "scan_runs", ["started_at"], unique=False)
    op.create_index("ix_scan_runs_status", "scan_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scan_runs_status", table_name="scan_runs")
    op.drop_index("ix_scan_runs_started_at", table_name="scan_runs")
    op.drop_table("scan_runs")
