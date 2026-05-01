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
        "bookmakers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=False),
        sa.Column("api_key_name", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key_name", name="uq_bookmakers_api_key_name"),
    )
    op.create_index("ix_bookmakers_region", "bookmakers", ["region"], unique=False)

    op.create_table(
        "sports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("sport_id", sa.Integer(), nullable=False),
        sa.Column("home_team", sa.String(length=255), nullable=False),
        sa.Column("away_team", sa.String(length=255), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("normalized_event_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sport_id"], ["sports.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_events_normalized_event_key", "events", ["normalized_event_key"], unique=False)
    op.create_index("ix_events_start_time", "events", ["start_time"], unique=False)

    op.create_table(
        "markets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("market_type", sa.String(length=64), nullable=False),
        sa.Column("line", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("is_live", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_suspended", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["bookmaker_id"], ["bookmakers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "bookmaker_id",
            "market_type",
            "line",
            "is_live",
            name="uq_markets_event_bookmaker_type_line_live",
        ),
    )
    op.create_index("ix_markets_bookmaker_id", "markets", ["bookmaker_id"], unique=False)
    op.create_index("ix_markets_last_seen_at", "markets", ["last_seen_at"], unique=False)
    op.create_index("ix_markets_market_type", "markets", ["market_type"], unique=False)

    op.create_table(
        "odds_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("market_type", sa.String(length=64), nullable=False),
        sa.Column("line", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("outcome_name", sa.String(length=255), nullable=False),
        sa.Column("decimal_odds", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["bookmaker_id"], ["bookmakers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_odds_snapshots_bookmaker_id", "odds_snapshots", ["bookmaker_id"], unique=False)
    op.create_index("ix_odds_snapshots_captured_at", "odds_snapshots", ["captured_at"], unique=False)
    op.create_index("ix_odds_snapshots_market_type", "odds_snapshots", ["market_type"], unique=False)

    op.create_table(
        "arbitrage_opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("market_type", sa.String(length=64), nullable=False),
        sa.Column("line", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("implied_probability_total", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("margin", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("total_stake", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("guaranteed_return", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("guaranteed_profit", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arbitrage_opportunities_detected_at", "arbitrage_opportunities", ["detected_at"], unique=False)
    op.create_index("ix_arbitrage_opportunities_market_type", "arbitrage_opportunities", ["market_type"], unique=False)

    op.create_table(
        "outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("market_id", sa.Integer(), nullable=False),
        sa.Column("outcome_name", sa.String(length=255), nullable=False),
        sa.Column("decimal_odds", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("market_id", "outcome_name", name="uq_outcomes_market_outcome_name"),
    )

    op.create_table(
        "arbitrage_legs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("bookmaker_id", sa.Integer(), nullable=False),
        sa.Column("outcome_name", sa.String(length=255), nullable=False),
        sa.Column("decimal_odds", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("stake", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("expected_return", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["bookmaker_id"], ["bookmakers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["arbitrage_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arbitrage_legs_bookmaker_id", "arbitrage_legs", ["bookmaker_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_arbitrage_legs_bookmaker_id", table_name="arbitrage_legs")
    op.drop_table("arbitrage_legs")
    op.drop_table("outcomes")
    op.drop_index("ix_arbitrage_opportunities_market_type", table_name="arbitrage_opportunities")
    op.drop_index("ix_arbitrage_opportunities_detected_at", table_name="arbitrage_opportunities")
    op.drop_table("arbitrage_opportunities")
    op.drop_index("ix_odds_snapshots_market_type", table_name="odds_snapshots")
    op.drop_index("ix_odds_snapshots_captured_at", table_name="odds_snapshots")
    op.drop_index("ix_odds_snapshots_bookmaker_id", table_name="odds_snapshots")
    op.drop_table("odds_snapshots")
    op.drop_index("ix_markets_market_type", table_name="markets")
    op.drop_index("ix_markets_last_seen_at", table_name="markets")
    op.drop_index("ix_markets_bookmaker_id", table_name="markets")
    op.drop_table("markets")
    op.drop_index("ix_events_start_time", table_name="events")
    op.drop_index("ix_events_normalized_event_key", table_name="events")
    op.drop_table("events")
    op.drop_table("sports")
    op.drop_index("ix_bookmakers_region", table_name="bookmakers")
    op.drop_table("bookmakers")
