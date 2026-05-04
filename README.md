# Project Robin Hood

A local MVP for an arbitrage betting scanner.

## Developer Guidelines

Read [AGENTS.md](AGENTS.md) before making repository changes. It defines the project architecture, safety boundaries, folder conventions, testing expectations, and Codex instructions.

Architecture reference docs:

- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [API contracts](docs/api-contracts.md)

## Stack

- Backend: FastAPI
- Database: Postgres
- ORM: SQLAlchemy
- Migrations: Alembic
- Job runner: Celery
- Cache/queue: Redis
- Frontend: Next.js
- Local orchestration: Docker Compose

## Project Structure

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
```

## Services

- `api`: FastAPI application on `http://localhost:8000`
- `worker`: Celery worker for background odds scans
- `postgres`: Postgres database on `localhost:5432`
- `redis`: Redis broker/cache on `localhost:6379`
- `frontend`: Next.js app on `http://localhost:3000`

## Environment

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Available variables:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/arbitrage
REDIS_URL=redis://redis:6379/0
ODDS_API_KEY=
SPORT_KEYS=afl,nrl
ODDS_REGIONS=au
DEFAULT_TOTAL_STAKE=1000
MIN_ARBITRAGE_MARGIN=0.01
MAX_ODDS_AGE_SECONDS=60
MIN_MARKET_CONFIDENCE=0.85
MAX_EVENT_START_TIME_DIFF_MINUTES=5
DAILY_QUOTA_BUDGET=500
MIN_REQUESTS_REMAINING_BUFFER=20
MAX_SCANS_PER_HOUR=12
ENABLE_QUOTA_GUARD=true
LOW_PRIORITY_SCAN_MINUTES=30
NORMAL_PRIORITY_SCAN_MINUTES=5
HIGH_PRIORITY_SCAN_SECONDS=60
URGENT_PRIORITY_SCAN_SECONDS=30
NEAR_ARB_THRESHOLD=0.03
```

`ODDS_API_KEY` is optional for bootstrapping. Odds ingestion returns a skipped result when it is not configured.

The current provider is The Odds API v4: `https://the-odds-api.com/liveapi/guides/v4/`. `SPORT_KEYS` accepts The Odds API sport keys. For convenience, the MVP maps `afl` to `aussierules_afl` and `nrl` to `rugbyleague_nrl`.

## Run Locally

Start the full stack:

```bash
docker compose up --build -d
```

Open the frontend:

```text
http://localhost:3000
```

The dashboard can trigger a full scan, display the latest scan run, and show active opportunities.

## Common Development Commands

Full stack:

```bash
docker compose up --build
docker compose down
docker compose config
```

Backend:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
python -m unittest discover app/tests
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run build
```

## Frontend UX

The frontend uses a trading-dashboard layout with a fixed collapsible sidebar, sticky AppBar, and warm Robin Hood-inspired theme accents.

Theme switching:

- Use the sun/moon switch in the AppBar to toggle light and dark mode.
- The selected theme is stored in browser `localStorage`.
- Light mode uses a parchment background with forest green and gold accents.
- Dark mode uses charcoal surfaces with bright green and muted gold accents.

UX features:

- AppBar scan controls with loading state and snackbar feedback.
- Dashboard metric cards for scan health, opportunity performance, realized profit/loss, and recent activity.
- Opportunities board powered by MUI DataGrid with sorting, filtering, column resizing, and pagination.
- Auto-refresh controls with a 30-second countdown and row flash for newly detected opportunities.
- Execution-focused opportunity detail screen with large odds, stake cards, copyable instructions, and a manual checklist.

Check the API directly:

```bash
curl http://localhost:8000/health
```

Core read endpoints:

```text
GET /bookmakers
GET /sports
GET /events
GET /dashboard/metrics
GET /aliases/teams
POST /aliases/teams
GET /aliases/markets
POST /aliases/markets
POST /scan
GET /scan-runs
GET /scan-runs/{id}
GET /api-usage
GET /scan-priorities
GET /quality-checks
GET /opportunities
GET /opportunities/active
GET /opportunities/active?include_stale=true
GET /opportunities/{id}
GET /opportunities/{id}/instructions
POST /opportunities/{id}/mark-actioned
POST /opportunities/{id}/actions
POST /opportunities/{id}/bet-records
PATCH /bet-records/{id}
POST /jobs/fetch-odds
POST /jobs/adaptive-scan
POST /jobs/detect-arbitrage
GET /jobs/{task_id}
```

## Odds Ingestion

Set your odds API key in `.env`:

```bash
ODDS_API_KEY=your_api_key_here
SPORT_KEYS=afl,nrl
ODDS_REGIONS=au
```

Start the stack:

```bash
docker compose up --build
```

Trigger a manual scrape:

```bash
curl -X POST http://localhost:8000/jobs/fetch-odds
```

Run the complete scan workflow, which fetches odds and then detects arbitrage:

```bash
curl -X POST http://localhost:8000/scan
```

Inspect recent scan runs:

```bash
curl http://localhost:8000/scan-runs
curl http://localhost:8000/scan-runs/{id}
```

Check the queued job:

```bash
curl http://localhost:8000/jobs/{task_id}
```

Inspect stored events through the API:

```bash
curl http://localhost:8000/events
```

Detect arbitrage from recent odds snapshots:

```bash
curl -X POST http://localhost:8000/jobs/detect-arbitrage
```

Inspect active opportunities with event details, bookmaker legs, stake sizing, and freshness status:

```bash
curl http://localhost:8000/opportunities/active
```

Open manual bet instructions for an opportunity:

```bash
curl http://localhost:8000/opportunities/{id}/instructions
```

Mark an opportunity as actioned after manual handling:

```bash
curl -X POST http://localhost:8000/opportunities/{id}/mark-actioned
```

Inspect stored markets, outcomes, and snapshots in Postgres:

```bash
docker compose exec postgres psql -U postgres -d arbitrage -c "select e.start_time, e.home_team, e.away_team, m.market_type, b.name as bookmaker, o.outcome_name, o.decimal_odds from events e join markets m on m.event_id = e.id join bookmakers b on b.id = m.bookmaker_id join outcomes o on o.market_id = m.id order by e.start_time, b.name;"
docker compose exec postgres psql -U postgres -d arbitrage -c "select captured_at, market_type, outcome_name, decimal_odds from odds_snapshots order by captured_at desc limit 20;"
```

## Database Migrations

The API service runs migrations on container startup. To run them manually:

```bash
docker compose run --rm api alembic upgrade head
```

Create a new migration after model changes:

```bash
docker compose run --rm api alembic revision --autogenerate -m "describe change"
```

## Background Jobs

The Celery worker starts with Docker Compose. The initial odds scan task is registered as:

```text
app.jobs.scan_odds.scan_odds
```

You can trigger it from an API shell or add an endpoint later:

```python
from app.jobs.scan_odds import scan_odds

scan_odds.delay()
```

## Local Development Without Docker

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

If you run the backend on the host machine instead of inside Docker, use host-based service URLs:

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/arbitrage"
$env:REDIS_URL="redis://localhost:6379/0"
```

On macOS or Linux, activate the virtual environment with:

```bash
. .venv/bin/activate
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The frontend uses Material UI. If you are adding dependencies from a fresh checkout, install the MUI packages with:

```bash
cd frontend
npm install @mui/material @mui/icons-material @emotion/react @emotion/styled
```

The local frontend runs at:

```text
http://localhost:3000
```
