# Project Robin Hood

Project Robin Hood is a local arbitrage odds scanner. It ingests permitted odds feeds, detects potential arbitrage opportunities, and shows manual execution instructions for a human user to review outside the app.

It does not place bets, log in to bookmaker accounts, solve captchas, bypass KYC/geolocation checks, or control bookmaker accounts.

## UI

The MVP frontend is a trading-dashboard style Next.js app with:

- Dashboard metrics, scan controls, quota status, and recent activity.
- Opportunities board with freshness and quality indicators.
- Manual opportunity execution form for actual odds/stake notes.
- Scan history, adaptive scan priority, API usage, executions, and help pages.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Worker: Celery
- Queue/cache: Redis
- Database: Postgres
- Frontend: Next.js, React, MUI
- Local development: Docker Compose

## Quick Start

```bash
./scripts/bootstrap.sh
./scripts/dev.sh
```

Open:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

To try the UI without a live API key:

```bash
./scripts/seed_local.sh
```

## Common Commands

```bash
make bootstrap  # check tools and create .env if missing
make dev        # start the Docker Compose stack
make test       # run backend tests and frontend tests if configured
make lint       # run configured linters
make format     # run configured formatters
make reset      # reset local Docker volumes/database
make seed       # seed local demo data
make docs       # print key docs
```

Frontend code quality commands:

```bash
cd frontend
npm run lint
npm run lint:fix
npm run format
npm run format:check
```

The frontend ESLint and Prettier rules are aligned with the sibling `anvil/UI` project. ESLint uses `frontend/eslint.config.mjs`; Prettier uses `frontend/.prettierrc.cjs` and `frontend/.prettierignore`.

## Folder Structure

```text
backend/   FastAPI app, SQLAlchemy models, services, providers, Celery jobs, tests
frontend/  Next.js app routes, shared components, feature folders, hooks, API client
docs/      Developer onboarding and architecture documentation
scripts/   Local bootstrap, dev, test, lint, reset, and seed helpers
```

## Documentation

- [Getting started](docs/getting-started.md)
- [Architecture](docs/architecture.md)
- [Backend guide](docs/backend.md)
- [Frontend guide](docs/frontend.md)
- [Data model](docs/data-model.md)
- [API contracts](docs/api-contracts.md)
- [Scanning and quota](docs/scanning-and-quota.md)
- [Arbitrage logic](docs/arbitrage-logic.md)
- [Normalisation](docs/normalisation.md)
- [Testing](docs/testing.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Safety and compliance](docs/safety-and-compliance.md)
- [Contributing](docs/contributing.md)

## Safety Boundaries

This application provides analytics and manual instructions only. Do not add automatic bet placement, bookmaker login automation, captcha bypassing, KYC bypassing, geolocation bypassing, self-exclusion bypassing, responsible gambling control bypassing, or anti-bot bypassing.

Prefer official APIs and permitted data feeds. Check legal requirements and bookmaker/provider terms before adding integrations.

## MVP Limitations

- The current provider integration targets The Odds API head-to-head markets.
- No frontend test runner is configured yet.
- Local seed data is synthetic and should not be used as market truth.
- Manual execution records are user-entered notes and estimates, not bookmaker account records.

## Roadmap

- Broader permitted market coverage.
- Richer opportunity review and execution history.
- More provider adapters with mocked tests.
- Frontend component tests.
- More granular settings/admin UI.
