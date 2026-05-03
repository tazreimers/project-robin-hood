"""create normalization aliases

Revision ID: 0004_create_normalization_aliases
Revises: 0003_add_opportunity_validation
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_create_normalization_aliases"
down_revision: Union[str, None] = "0003_add_opportunity_validation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AFL_SPORT_KEY = "aussierules_afl"

AFL_TEAM_ALIASES: list[dict[str, str]] = [
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Adelaide", "alias": "Adelaide"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Adelaide", "alias": "Adelaide Crows"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Adelaide", "alias": "Crows"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Adelaide", "alias": "ADE"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Adelaide", "alias": "ADEL"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Brisbane", "alias": "Brisbane"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Brisbane", "alias": "Brisbane Lions"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Brisbane", "alias": "Lions"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Brisbane", "alias": "BRI"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Brisbane", "alias": "BRL"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Brisbane", "alias": "BL"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Carlton", "alias": "Carlton"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Carlton", "alias": "Carlton Blues"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Carlton", "alias": "Blues"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Carlton", "alias": "CAR"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Carlton", "alias": "CARL"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Collingwood", "alias": "Collingwood"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Collingwood", "alias": "Collingwood Magpies"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Collingwood", "alias": "Magpies"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Collingwood", "alias": "COL"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Collingwood", "alias": "COLL"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Essendon", "alias": "Essendon"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Essendon", "alias": "Essendon Bombers"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Essendon", "alias": "Bombers"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Essendon", "alias": "ESS"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Fremantle", "alias": "Fremantle"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Fremantle", "alias": "Fremantle Dockers"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Fremantle", "alias": "Dockers"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Fremantle", "alias": "FRE"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Geelong", "alias": "Geelong"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Geelong", "alias": "Geelong Cats"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Geelong", "alias": "Cats"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Geelong", "alias": "GEE"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Geelong", "alias": "GEEL"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Gold Coast", "alias": "Gold Coast"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Gold Coast", "alias": "Gold Coast Suns"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Gold Coast", "alias": "Gold Coast SUNS"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Gold Coast", "alias": "Suns"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Gold Coast", "alias": "GCS"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Gold Coast", "alias": "GC"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Gold Coast", "alias": "SUNS"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "GWS", "alias": "GWS"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "GWS", "alias": "GWS Giants"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "GWS", "alias": "GWS GIANTS"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "GWS", "alias": "Greater Western Sydney"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "GWS", "alias": "Greater Western Sydney Giants"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "GWS", "alias": "Giants"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Hawthorn", "alias": "Hawthorn"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Hawthorn", "alias": "Hawthorn Hawks"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Hawthorn", "alias": "Hawks"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Hawthorn", "alias": "HAW"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Melbourne", "alias": "Melbourne"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Melbourne", "alias": "Melbourne Demons"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Melbourne", "alias": "Demons"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Melbourne", "alias": "MEL"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Melbourne", "alias": "MELB"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "North Melbourne", "alias": "North Melbourne"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "North Melbourne", "alias": "North Melbourne Kangaroos"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "North Melbourne", "alias": "Kangaroos"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "North Melbourne", "alias": "NMFC"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "North Melbourne", "alias": "NM"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Port Adelaide", "alias": "Port Adelaide"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Port Adelaide", "alias": "Port Adelaide Power"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Port Adelaide", "alias": "Power"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Port Adelaide", "alias": "PORT"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Port Adelaide", "alias": "PA"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Richmond", "alias": "Richmond"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Richmond", "alias": "Richmond Tigers"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Richmond", "alias": "Tigers"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Richmond", "alias": "RICH"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "St Kilda", "alias": "St Kilda"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "St Kilda", "alias": "St Kilda Saints"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "St Kilda", "alias": "Saints"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "St Kilda", "alias": "STK"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Sydney", "alias": "Sydney"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Sydney", "alias": "Sydney Swans"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Sydney", "alias": "Swans"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Sydney", "alias": "SYD"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "West Coast", "alias": "West Coast"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "West Coast", "alias": "West Coast Eagles"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "West Coast", "alias": "Eagles"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "West Coast", "alias": "WCE"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Western Bulldogs", "alias": "Western Bulldogs"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Western Bulldogs", "alias": "Bulldogs"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Western Bulldogs", "alias": "WB"},
    {"sport_key": AFL_SPORT_KEY, "canonical_name": "Western Bulldogs", "alias": "WBD"},
]

MARKET_ALIASES: list[dict[str, str]] = [
    {"provider": "the_odds_api", "source_market_name": "h2h", "canonical_market_type": "h2h"},
    {"provider": "the_odds_api", "source_market_name": "head_to_head", "canonical_market_type": "h2h"},
    {"provider": "the_odds_api", "source_market_name": "Head to Head", "canonical_market_type": "h2h"},
    {"provider": "the_odds_api", "source_market_name": "moneyline", "canonical_market_type": "h2h"},
]


def upgrade() -> None:
    team_aliases = op.create_table(
        "team_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport_key", sa.String(length=64), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sport_key", "alias", name="uq_team_aliases_sport_alias"),
    )
    op.create_index("ix_team_aliases_sport_key", "team_aliases", ["sport_key"], unique=False)
    op.create_index("ix_team_aliases_canonical_name", "team_aliases", ["canonical_name"], unique=False)

    market_aliases = op.create_table(
        "market_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("source_market_name", sa.String(length=255), nullable=False),
        sa.Column("canonical_market_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "source_market_name", name="uq_market_aliases_provider_source"),
    )
    op.create_index("ix_market_aliases_provider", "market_aliases", ["provider"], unique=False)
    op.create_index("ix_market_aliases_canonical_market_type", "market_aliases", ["canonical_market_type"], unique=False)

    op.bulk_insert(team_aliases, AFL_TEAM_ALIASES)
    op.bulk_insert(market_aliases, MARKET_ALIASES)


def downgrade() -> None:
    op.drop_index("ix_market_aliases_canonical_market_type", table_name="market_aliases")
    op.drop_index("ix_market_aliases_provider", table_name="market_aliases")
    op.drop_table("market_aliases")
    op.drop_index("ix_team_aliases_canonical_name", table_name="team_aliases")
    op.drop_index("ix_team_aliases_sport_key", table_name="team_aliases")
    op.drop_table("team_aliases")
