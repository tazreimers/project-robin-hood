# Getting Started

## Prerequisites

- Git
- Docker
- Docker Compose plugin
- Node.js for local frontend tooling
- Python 3.12 for local backend tooling

## Clone

```bash
git clone <repo-url> project-robin-hood
cd project-robin-hood
```

## Bootstrap

```bash
./scripts/bootstrap.sh
```

This checks local tools, creates `.env` from `.env.example` if missing, and prints next steps. It will not overwrite an existing `.env`.

## Run The App

```bash
./scripts/dev.sh
```

Open:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Seed Demo Data

```bash
./scripts/seed_local.sh
```

Use this when you do not have an odds API key. It creates fake AFL events, bookmakers, odds snapshots, opportunities, and quality examples.

## Run Tests

```bash
./scripts/test.sh
```

Backend tests run with `unittest`. Frontend tests are skipped until a frontend test script is configured.

## Common First Tasks

- Add a backend endpoint: update schemas, service logic, route, and tests.
- Add a provider: create an adapter in `backend/app/providers/`, keep credentials in settings, and test with mocked responses.
- Add a frontend page: create a route under `frontend/app/`, add API helpers in `frontend/lib/api.ts`, and shared types in `frontend/types/`.
- Update docs whenever behavior, setup, data model, or API contracts change.
