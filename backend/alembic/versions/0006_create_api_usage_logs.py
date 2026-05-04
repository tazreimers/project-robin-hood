"""create api usage logs

Revision ID: 0006_api_usage_logs
Revises: 0005_action_tracking
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_api_usage_logs"
down_revision: Union[str, None] = "0005_action_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_usage_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("sport_key", sa.String(length=64), nullable=True),
        sa.Column("regions", sa.String(length=128), server_default="", nullable=False),
        sa.Column("markets", sa.String(length=255), server_default="", nullable=False),
        sa.Column("requests_remaining", sa.Integer(), nullable=True),
        sa.Column("requests_used", sa.Integer(), nullable=True),
        sa.Column("requests_last", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Integer(), server_default="0", nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_usage_logs_captured_at", "api_usage_logs", ["captured_at"], unique=False)
    op.create_index("ix_api_usage_logs_provider", "api_usage_logs", ["provider"], unique=False)
    op.create_index("ix_api_usage_logs_sport_key", "api_usage_logs", ["sport_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_usage_logs_sport_key", table_name="api_usage_logs")
    op.drop_index("ix_api_usage_logs_provider", table_name="api_usage_logs")
    op.drop_index("ix_api_usage_logs_captured_at", table_name="api_usage_logs")
    op.drop_table("api_usage_logs")
