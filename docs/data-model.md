# Data Model

This document summarizes the main SQLAlchemy models and relationships.

## Reference And Normalisation

- `sports`: Sports available to scan.
- `bookmakers`: Bookmaker identity, region, provider key, and active flag.
- `team_aliases`: Sport-specific aliases for team normalisation.
- `market_aliases`: Provider-specific market names mapped to canonical market types.

## Events And Odds

- `events`: Normalized events with sport, teams, start time, and `normalized_event_key`.
- `markets`: Current event/bookmaker market records with market type, line, live/suspended state, and last seen time.
- `outcomes`: Current market outcomes with decimal odds.
- `odds_snapshots`: Historical captured odds used for arbitrage detection and freshness checks.

## Scanning

- `scan_runs`: Tracks scan status, processed counts, timestamps, and error messages.
- `api_usage_logs`: Stores provider quota headers: remaining, used, last request cost, estimated cost, endpoint, sport key, regions, markets, and capture time.
- `event_scan_priorities`: Stores adaptive polling priority, next scan time, last scan time, and reason.

## Arbitrage

- `arbitrage_opportunities`: Detected opportunities with event, market, line, implied probability total, margin, stake total, guaranteed return/profit, reliability score, validation status, reasons, and expiry.
- `arbitrage_legs`: Required bookmaker/outcome legs with decimal odds, recommended stake, and expected return.
- `market_quality_checks`: Per-market quality result with status, confidence, reasons JSON, line, and checked time.

## Manual Tracking

- `opportunity_actions`: Manual user activity log such as `VIEWED`, `ACTIONED`, `SKIPPED`, `EXPIRED`, and `ODDS_CHANGED`.
- `opportunity_executions`: Manual execution plan for an opportunity with status, planned/actual stake totals, expected profit, actual profit estimate, and notes.
- `execution_legs`: Per-bookmaker manual execution leg with recommended odds/stake, user-entered actual odds/stake, status, and notes.
- `bet_records`: Optional manual settlement records for odds taken, actual stake, payout, and profit/loss.

## Key Relationships

- `Sport` has many `Event` rows.
- `Event` has many markets, snapshots, opportunities, quality checks, and at most one scan priority.
- `ArbitrageOpportunity` has many legs, actions, bet records, and executions.
- `OpportunityExecution` has many execution legs.
- `Bookmaker` has markets, snapshots, arbitrage legs, and execution legs.

## Migrations

Every model shape change needs an Alembic migration under `backend/alembic/versions/`.
