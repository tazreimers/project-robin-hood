"""create event scan priorities

Revision ID: 0007_create_event_scan_priorities
Revises: 0006_create_api_usage_logs
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_create_event_scan_priorities"
down_revision: Union[str, None] = "0006_create_api_usage_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_scan_priorities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("sport_key", sa.String(length=64), nullable=False),
        sa.Column("priority_level", sa.String(length=16), nullable=False),
        sa.Column("next_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_event_scan_priorities_event_id"),
    )
    op.create_index("ix_event_scan_priorities_event_id", "event_scan_priorities", ["event_id"], unique=False)
    op.create_index("ix_event_scan_priorities_next_scan_at", "event_scan_priorities", ["next_scan_at"], unique=False)
    op.create_index("ix_event_scan_priorities_priority_level", "event_scan_priorities", ["priority_level"], unique=False)
    op.create_index("ix_event_scan_priorities_sport_key", "event_scan_priorities", ["sport_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_event_scan_priorities_sport_key", table_name="event_scan_priorities")
    op.drop_index("ix_event_scan_priorities_priority_level", table_name="event_scan_priorities")
    op.drop_index("ix_event_scan_priorities_next_scan_at", table_name="event_scan_priorities")
    op.drop_index("ix_event_scan_priorities_event_id", table_name="event_scan_priorities")
    op.drop_table("event_scan_priorities")
