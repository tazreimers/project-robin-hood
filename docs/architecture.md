# Architecture

Project Robin Hood is a local arbitrage odds scanner with a FastAPI backend, Celery worker, Postgres database, Redis broker, and Next.js frontend.

## Runtime Services

- `api`: FastAPI application. It exposes scanner, opportunities, alias management, action logging, bet record, and dashboard endpoints.
- `worker`: Celery worker. It runs background odds-fetching and arbitrage-detection jobs.
- `postgres`: Persistent relational database for events, markets, odds snapshots, opportunities, aliases, scan runs, and tracking records.
- `redis`: Celery broker and result backend.
- `frontend`: Next.js application using React and MUI.

Docker Compose wires these services together for local development.

## Backend Layers

- `backend/app/api/routes/`: FastAPI route handlers. These should stay thin and delegate real work.
- `backend/app/api/dependencies.py`: API dependency wiring such as database sessions.
- `backend/app/core/`: Settings, logging helpers, and shared constants.
- `backend/app/db/`: SQLAlchemy declarative base and session/engine setup.
- `backend/app/models/`: SQLAlchemy table models.
- `backend/app/schemas/`: Pydantic request and response models.
- `backend/app/services/`: Business logic for scanning, odds ingestion, arbitrage detection, normalization, validation, and health checks.
- `backend/app/providers/`: External odds provider adapters and provider DTOs.
- `backend/app/jobs/`: Celery app and background tasks.
- `backend/app/tests/`: Backend unit tests.
- `backend/alembic/`: Database migrations.

## Scan Flow

1. A user clicks Run Scan in the frontend or calls `POST /scan`.
2. The API checks the quota guard for estimated cost, remaining quota buffer, daily budget, and scan frequency.
3. If allowed, the API creates a `scan_runs` row and queues `scan_now`; if blocked, the scan run is returned with `status: "blocked"`.
4. Celery fetches odds through provider adapters.
5. Provider responses log quota headers to `api_usage_logs`.
6. Odds ingestion normalizes teams, events, and markets before persisting sports, events, bookmakers, markets, outcomes, and snapshots.
7. Arbitrage detection evaluates recent odds snapshots and creates opportunity rows and legs.
8. Opportunity validation scores freshness, event start risk, market consistency, event matching confidence, and leg availability.
9. The frontend reads active opportunities and displays manual execution instructions.

## Manual Tracking Flow

Users can log manual actions against an opportunity and manually record bet details. These records power dashboard metrics such as actioned opportunities, expired opportunities, recommended profit, realized profit/loss, average margin, average odds age, and best bookmaker pairs.

The system does not automate bookmaker account access or bet placement.

## Frontend Layers

- `frontend/app/`: Next.js app routes and page composition.
- `frontend/components/`: Shared UI components, including the application shell.
- `frontend/features/`: Feature-specific components and helpers for larger UI areas.
- `frontend/hooks/`: Shared React hooks.
- `frontend/lib/api.ts`: API client functions and formatting helpers.
- `frontend/theme/`: MUI theme configuration.
- `frontend/types/`: Shared TypeScript types.
