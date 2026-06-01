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

## Configure Odds Markets

Live scans are controlled from `.env`.

Featured markets use The Odds API `/odds` endpoint:

```bash
ODDS_MARKETS=h2h
```

Valid featured market keys include `h2h`, `spreads`, `totals`, and `outrights`. Multiple values are comma-separated:

```bash
ODDS_MARKETS=h2h,totals
```

Player props and other non-featured markets use the event-odds endpoint, one event at a time:

```bash
ODDS_EVENT_MARKETS=player_disposals_over,player_goal_scorer_anytime
ODDS_EVENT_MARKET_MAX_EVENTS=8
```

Set `ODDS_EVENT_MARKET_MAX_EVENTS=0` to disable event-level market calls without deleting the market list.

After editing `.env`, restart the Docker Compose stack so the API and worker containers receive the new values.

For AFL props, useful market keys include `player_disposals`, `player_disposals_over`, `player_goals_scored_over`, `player_marks_over`, `player_tackles_over`, `player_kicks_over`, `player_handballs_over`, and `player_goal_scorer_anytime`.

Provider credit cost scales with sports, regions, markets, and event count. With `SPORT_KEYS=afl`, `ODDS_REGIONS=au`, `ODDS_MARKETS=h2h`, two event markets, and `ODDS_EVENT_MARKET_MAX_EVENTS=8`, the estimated cost is `1 + (8 * 2) = 17` credits per scan.

Current arbitrage detection only creates opportunities from `h2h` snapshots. Additional markets are ingested so they can be reviewed and built on, but they are not yet used to create arbitrage opportunities.

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
