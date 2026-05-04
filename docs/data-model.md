# Data Model

This document summarizes the current SQLAlchemy models and database tables.

## Core Odds Tables

- `bookmakers`: Bookmaker identity and region metadata.
- `sports`: Sports available to scan.
- `events`: Normalized sporting events with home team, away team, start time, and `normalized_event_key`.
- `markets`: Event/bookmaker market records keyed by market type, line, and live/suspended state.
- `outcomes`: Market outcomes with decimal odds.
- `odds_snapshots`: Historical captured odds used for arbitrage detection and freshness checks.

## Normalization Tables

- `team_aliases`: Maps a sport-specific alias to a canonical team name.
- `market_aliases`: Maps provider-specific market names to canonical market types.

## Arbitrage Tables

- `arbitrage_opportunities`: Detected opportunities with margin, stake totals, guaranteed return/profit, status, reliability score, validation status, validation reasons, and validation timestamp.
- `arbitrage_legs`: Required bookmaker/outcome/stake legs for an opportunity.

## Tracking Tables

- `opportunity_actions`: Manual user action log for opportunities. Supported actions are `VIEWED`, `ACTIONED`, `SKIPPED`, `EXPIRED`, `ODDS_CHANGED`, `BET_REJECTED`, `WON`, and `LOST`.
- `bet_records`: Manual bet record entries for odds taken, recommended stake, actual stake, settlement status, payout, and profit/loss.

## Operational Tables

- `scan_runs`: Tracks background scan execution, counts processed by the scan, completion timestamp, and any error message.
- `api_usage_logs`: Tracks provider API quota headers, estimated request cost, endpoint, sport key, regions, markets, and capture timestamp.

## Migrations

Alembic migrations live in `backend/alembic/versions/` and should be updated whenever model shape changes.
