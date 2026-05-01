"""create scanner tables

Revision ID: 0001_create_scanner_tables
Revises:
Create Date: 2026-05-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_create_scanner_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("sport_key", sa.String(length=64), nullable=False),
        sa.Column("home_team", sa.String(length=255), nullable=False),
        sa.Column("away_team", sa.String(length=255), nullable=False),
        sa.Column("commence_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_events_sport_key", "events", ["sport_key"], unique=False)
    op.create_index("ix_events_commence_time", "events", ["commence_time"], unique=False)

    op.create_table(
        "bookmakers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_table(
        "arbitrage_opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("market_key", sa.String(length=64), nullable=False),
        sa.Column("stake_currency", sa.String(length=3), nullable=False),
        sa.Column("total_implied_probability", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("profit_margin", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("legs", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arbitrage_opportunities_event_id", "arbitrage_opportunities", ["event_id"], unique=False)
    op.create_index("ix_arbitrage_opportunities_detected_at", "arbitrage_opportunities", ["detected_at"], unique=False)

    op.create_table(
        "odds_quotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("market_key", sa.String(length=64), nullable=False),
        sa.Column("outcome_name", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("last_update", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["bookmaker_id"], ["bookmakers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_odds_quotes_event_id", "odds_quotes", ["event_id"], unique=False)
    op.create_index("ix_odds_quotes_market_key", "odds_quotes", ["market_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_odds_quotes_market_key", table_name="odds_quotes")
    op.drop_index("ix_odds_quotes_event_id", table_name="odds_quotes")
    op.drop_table("odds_quotes")
    op.drop_index("ix_arbitrage_opportunities_detected_at", table_name="arbitrage_opportunities")
    op.drop_index("ix_arbitrage_opportunities_event_id", table_name="arbitrage_opportunities")
    op.drop_table("arbitrage_opportunities")
    op.drop_table("bookmakers")
    op.drop_index("ix_events_commence_time", table_name="events")
    op.drop_index("ix_events_sport_key", table_name="events")
    op.drop_table("events")
