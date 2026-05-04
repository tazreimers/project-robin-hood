# API Contracts

Base URL in local development: `http://localhost:8000`.

## Health

- `GET /health`: Returns service health, service name, and environment.

## Scan Runs and Jobs

- `POST /scan`: Checks the quota guard, then creates a scan run and queues the full scan workflow. If blocked, returns a scan run with `status: "blocked"` and the reason in `error_message`.
- `GET /scan-runs`: Lists scan runs newest first.
- `GET /scan-runs/{scan_run_id}`: Returns one scan run.
- `GET /api-usage`: Returns latest remaining quota, used quota, last request cost, estimated scans remaining, and recent usage logs.
- `POST /jobs/fetch-odds`: Queues odds fetching.
- `POST /jobs/detect-arbitrage`: Queues arbitrage detection.
- `GET /jobs/{task_id}`: Returns Celery job state and result/error details.

## Reference Data

- `GET /bookmakers`: Lists bookmakers.
- `GET /sports`: Lists sports.
- `GET /events`: Lists events by start time.

## Alias Administration

- `GET /aliases/teams`: Lists team aliases.
- `POST /aliases/teams`: Creates a team alias.
- `GET /aliases/markets`: Lists market aliases.
- `POST /aliases/markets`: Creates a market alias.

## Opportunities

- `GET /opportunities`: Lists all opportunities.
- `GET /opportunities/active`: Lists active `FRESH` and `RISKY` opportunities by default.
- `GET /opportunities/active?include_stale=true`: Includes `STALE` opportunities in the active list.
- `GET /opportunities/{opportunity_id}`: Returns one opportunity.
- `GET /opportunities/{opportunity_id}/instructions`: Returns manual bet instructions for an opportunity.
- `POST /opportunities/{opportunity_id}/mark-actioned`: Marks an opportunity as manually actioned.

## Manual Action Tracking

- `POST /opportunities/{opportunity_id}/actions`: Creates a manual action log entry.

Supported action types:

- `VIEWED`
- `ACTIONED`
- `SKIPPED`
- `EXPIRED`
- `ODDS_CHANGED`
- `BET_REJECTED`
- `WON`
- `LOST`

## Manual Bet Records

- `POST /opportunities/{opportunity_id}/bet-records`: Creates a manual bet record.
- `PATCH /bet-records/{bet_record_id}`: Updates a manual bet record.

## Dashboard

- `GET /dashboard/metrics`: Returns dashboard metrics, bookmaker pair metrics, and recent manual activity.
