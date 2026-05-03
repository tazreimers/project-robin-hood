# Developer and Agent Guidelines

## 1. Project Overview

Project Robin Hood is an arbitrage odds scanner.

It ingests market odds from APIs and scrapers where permitted, detects arbitrage opportunities, and displays manual bet instructions for a human user to review and execute outside the application.

This project does not automate betting, bookmaker login, captcha bypassing, KYC bypassing, geolocation bypassing, age-check bypassing, self-exclusion bypassing, or responsible gambling control bypassing.

## 2. Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Celery, Redis, Postgres
- Frontend: Next.js, React, MUI
- Local development: Docker Compose

## 3. Repository Structure

Expected structure:

```text
backend/
  app/
    api/
      routes/
      dependencies.py
    core/
      config.py
      logging.py
      constants.py
    db/
      session.py
      base.py
    models/
    schemas/
    services/
    jobs/
    providers/
    tests/
  alembic/

frontend/
  app/
  components/
  features/
  hooks/
  lib/
  theme/
  types/

docs/
  architecture.md
  data-model.md
  api-contracts.md
```

Provider integrations live under `backend/app/providers/`. Business services may consume providers, but provider adapter code should not live inside route handlers.

Backend tests live in `backend/app/tests/`.

## 4. Backend Conventions

- API route handlers should be thin.
- Business logic belongs in `backend/app/services/`.
- External data integrations belong in `backend/app/providers/`.
- Database models belong in `backend/app/models/`.
- Pydantic request and response objects belong in `backend/app/schemas/`.
- Celery tasks belong in `backend/app/jobs/`.
- Shared config belongs in `backend/app/core/config.py`.
- Shared logging helpers belong in `backend/app/core/logging.py`.
- Shared constants belong in `backend/app/core/constants.py`.
- Database session setup belongs in `backend/app/db/session.py`.
- Declarative SQLAlchemy base setup belongs in `backend/app/db/base.py`.
- Do not call external APIs directly from route handlers.
- Do not put business logic in SQLAlchemy models.

## 5. Frontend Conventions

- Use feature-based folders under `frontend/features/`.
- Shared UI components go in `frontend/components/`.
- API calls go in `frontend/lib/api.ts`.
- TypeScript types go in `frontend/types/`.
- Theme files go in `frontend/theme/`.
- Avoid duplicating API-fetch logic inside pages.
- Keep pages mostly as composition and layout components.

## 6. Naming Conventions

- Backend files: `snake_case.py`
- Backend classes: `PascalCase`
- Backend functions: `snake_case`
- Frontend components: `PascalCase.tsx`
- Frontend hooks: `useSomething.ts`
- Types and interfaces: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

## 7. Testing Expectations

- Add backend tests for services and API routes.
- Add frontend tests for key UI components where practical.
- Arbitrage math must always have unit tests.
- Normalisation logic must always have unit tests.
- Provider adapters should be tested with mocked responses.

## 8. Safety and Compliance Boundaries

- Do not implement bookmaker login automation.
- Do not implement automatic bet placement.
- Do not bypass anti-bot systems.
- Do not bypass captcha.
- Do not bypass KYC, geolocation, age checks, self-exclusion, or responsible gambling controls.
- Do not scrape sites in violation of their terms.
- Prefer official APIs and permitted data feeds.

The application may track manual user actions, record manually entered bet records, and display manual instructions. It must not control bookmaker accounts or place bets.

## 9. Definition of Done

A change is done when:

- It follows the folder structure.
- Linting passes.
- Relevant tests pass.
- README or docs are updated where needed.
- No safety or compliance boundary is violated.

## 10. Codex Instructions

- Read `AGENTS.md` first.
- Preserve the existing architecture.
- Prefer small, focused changes.
- Do not introduce new frameworks without justification.
- Add tests with meaningful changes.
- Update docs when changing architecture, data models, or API contracts.
- Do not change product behavior when the task is documentation or structure cleanup only.
