# API Contracts

Base URL in local development: `http://localhost:8000`.

## Health

- `GET /health`: Service health.

Example:

```json
{ "status": "ok", "service": "Project Robin Hood API", "environment": "development" }
```

## Scans And Jobs

- `POST /scan`: Checks quota guard, creates a scan run, and queues the full scan. If blocked, returns `status: "blocked"` and `error_message`.
- `GET /scan-runs`: Lists scan runs newest first.
- `GET /scan-runs/{scan_run_id}`: Returns one scan run.
- `POST /jobs/fetch-odds`: Queues provider odds fetching.
- `POST /jobs/adaptive-scan`: Queues adaptive due-event scanning.
- `POST /jobs/detect-arbitrage`: Queues arbitrage detection.
- `GET /jobs/{task_id}`: Returns Celery job state and result/error details.

## Quota And Quality

- `GET /api-usage`: Latest remaining quota, used quota, last request cost, estimated scans remaining, and usage logs.
- `GET /scan-priorities`: Adaptive event scan priorities with event, start time, priority, next scan time, and reason.
- `GET /quality-checks`: Market quality checks newest first.

## Reference Data

- `GET /bookmakers`: Active and inactive bookmaker records.
- `GET /sports`: Sports known to the system.
- `GET /events`: Events ordered by start time.

## Alias Administration

- `GET /aliases/teams`: Team aliases.
- `POST /aliases/teams`: Create a team alias.
- `GET /aliases/markets`: Market aliases.
- `POST /aliases/markets`: Create a market alias.

## Opportunities

- `GET /opportunities`: All opportunities with legs.
- `GET /opportunities/active`: Open `FRESH` and `RISKY` opportunities.
- `GET /opportunities/active?include_stale=true`: Includes stale opportunities.
- `GET /opportunities/active?include_inactive=true`: Includes historical inactive opportunities for review.
- `GET /opportunities/{opportunity_id}`: One opportunity.
- `GET /opportunities/{opportunity_id}/instructions`: Manual instructions, quality check, and per-leg freshness.
- `POST /opportunities/{opportunity_id}/mark-actioned`: Marks an opportunity manually actioned.

Instruction leg shape:

```json
{
  "bookmaker": { "id": 1, "name": "DemoBet" },
  "outcome_name": "Home",
  "decimal_odds": "2.2000",
  "stake": "505.62",
  "expected_return": "1112.36",
  "freshness_status": "VERIFIED"
}
```

## Manual Actions And Executions

- `POST /opportunities/{opportunity_id}/actions`: Creates a manual action log entry.
- `POST /opportunities/{opportunity_id}/executions`: Creates a manual execution plan from opportunity legs.
- `GET /executions`: Lists execution plans newest first.
- `GET /executions/{execution_id}`: Returns one execution with legs.
- `PATCH /executions/{execution_id}`: Updates execution status or notes.
- `PATCH /executions/{execution_id}/legs/{leg_id}`: Updates actual odds, actual stake, leg status, or notes.

Execution statuses: `PLANNED`, `ACTIONED`, `PARTIALLY_ACTIONED`, `ODDS_CHANGED`, `SKIPPED`, `SETTLED`.

Leg statuses: `PLANNED`, `PLACED`, `SKIPPED`, `ODDS_CHANGED`.

## Manual Bet Records

- `POST /opportunities/{opportunity_id}/bet-records`: Creates a manual bet record.
- `PATCH /bet-records/{bet_record_id}`: Updates a manual bet record.

## Dashboard

- `GET /dashboard/metrics`: Opportunity totals, execution metrics, settled profit/loss, bookmaker pair metrics, and recent manual activity.
