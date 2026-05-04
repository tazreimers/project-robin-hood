# Architecture

Project Robin Hood is a local arbitrage odds scanner with a FastAPI backend, Celery worker, Postgres database, Redis broker, and Next.js frontend.

## System Overview

- `api`: FastAPI service exposing scanner, opportunities, quota, execution, alias, and dashboard endpoints.
- `worker`: Celery worker for odds fetching, adaptive scans, and arbitrage detection.
- `postgres`: Durable storage for events, odds snapshots, opportunities, logs, and manual tracking records.
- `redis`: Celery broker and result backend.
- `frontend`: Next.js app for dashboards, opportunity review, manual execution, and help.
- External providers: Official/permitted odds APIs under `backend/app/providers/`.

## Data Flow

1. A user starts a scan from the frontend or `POST /scan`.
2. The quota guard estimates scan cost and checks daily budget, remaining request buffer, and scan frequency.
3. The API creates a `ScanRun` and queues Celery work.
4. Provider adapters fetch odds and capture quota headers.
5. Odds ingestion normalises sport, event, team, market, bookmaker, and outcome data.
6. Snapshots are stored in `odds_snapshots`.
7. Market quality checks reject stale, incomplete, mismatched, suspended, or invalid markets.
8. Arbitrage detection evaluates fresh quality-approved snapshots and saves opportunities and legs.
9. Opportunity validation scores freshness and leg availability for the UI.
10. The frontend displays opportunities and manual execution forms.

## Backend/API

Routes live in `backend/app/api/routes/`. Route handlers should stay thin and delegate provider calls, quota checks, scan scheduling, market quality checks, and arbitrage logic to services.

## Worker

Celery tasks live in `backend/app/jobs/`. Jobs open their own database session, call services, commit successful work, and mark failures on the relevant run or task summary.

## Redis

Redis is used as the Celery broker/result backend. The app should not depend on Redis for durable business state.

## Postgres

Postgres stores normalized source data, snapshots, opportunities, quota logs, scan priorities, quality checks, and manual tracking records. Alembic migrations live in `backend/alembic/versions/`.

## Frontend

The frontend is a Next.js app with MUI. Pages compose shared components from `frontend/components`, feature-specific code belongs under `frontend/features`, API calls live in `frontend/lib/api.ts`, and shared types live in `frontend/types`.

## Safety Boundary

The system stops at analytics, instructions, and manually entered records. It must not control bookmaker accounts or place bets.
