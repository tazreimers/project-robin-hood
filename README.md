# Project Robin Hood

A local MVP for an arbitrage betting scanner.

## Stack

- Backend: FastAPI
- Database: Postgres
- ORM: SQLAlchemy
- Migrations: Alembic
- Job runner: Celery
- Cache/queue: Redis
- Frontend: Next.js
- Local orchestration: Docker Compose

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
```

`ODDS_API_KEY` is optional for bootstrapping. The scan job currently returns a skipped result when it is not configured.

## Run Locally

Start the full stack:

```bash
docker compose up --build
```

Open the frontend:

```text
http://localhost:3000
```

Check the API directly:

```bash
curl http://localhost:8000/health
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
