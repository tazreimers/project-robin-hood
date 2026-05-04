# Backend Guide

## Folder Structure

- `backend/app/api/routes/`: FastAPI route handlers.
- `backend/app/api/dependencies.py`: Request dependencies such as database sessions.
- `backend/app/core/`: Settings, constants, and logging helpers.
- `backend/app/db/`: SQLAlchemy base and session setup.
- `backend/app/models/`: SQLAlchemy models only.
- `backend/app/schemas/`: Pydantic request/response models.
- `backend/app/services/`: Business logic.
- `backend/app/providers/`: External provider adapters.
- `backend/app/jobs/`: Celery tasks.
- `backend/app/tests/`: Backend tests.
- `backend/alembic/`: Migrations.

## How The Layers Fit

Routes parse HTTP input and call services. Services own business decisions such as scanning, quota checks, arbitrage detection, market quality, normalisation, and manual execution calculations. Providers translate external API payloads into provider DTOs. Models represent database tables and should not contain business logic.

## Add A New Endpoint

1. Add or update a Pydantic schema in `backend/app/schemas/`.
2. Put business logic in a service under `backend/app/services/`.
3. Add a thin route in `backend/app/api/routes/`.
4. Add route or service tests in `backend/app/tests/`.
5. Update `docs/api-contracts.md`.

## Add A New Provider

1. Implement an adapter in `backend/app/providers/`.
2. Return provider DTOs from `backend/app/providers/base.py`.
3. Keep credentials in `backend/app/core/config.py`.
4. Do not call provider APIs from route handlers.
5. Test adapter parsing with mocked responses.

## Migrations

When models change:

```bash
cd backend
alembic revision -m "describe change"
alembic upgrade head
```

Keep migrations deterministic and review generated SQL.
