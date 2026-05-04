# Scanning And Quota

## Manual Scan

`POST /scan` creates a `ScanRun` and queues the full workflow:

1. Quota guard check.
2. Fetch odds from configured providers.
3. Ingest and normalize odds.
4. Run arbitrage detection.
5. Update scan counts and status.

## Adaptive Scan

`POST /jobs/adaptive-scan` refreshes event priorities and scans only due sports/events. Priorities are based on event start time, near-arbitrage signals, recent arbitrage, odds movement, and sport configuration.

## Quota Guard

The quota guard blocks scans when:

- Estimated cost would exceed `DAILY_QUOTA_BUDGET`.
- Latest remaining quota is below estimated cost plus `MIN_REQUESTS_REMAINING_BUFFER`.
- More than `MAX_SCANS_PER_HOUR` scans started in the rolling hour.

## Provider Headers

The Odds API response headers are captured into `api_usage_logs`:

- `x-requests-remaining`
- `x-requests-used`
- `x-requests-last`

## Why Polling Is Expensive

Real-time odds polling can burn provider credits quickly because cost scales by sports, regions, and markets. A scan across two sports, two regions, and three markets may cost far more than a single focused request.

## Recommended Strategy

- Use demo data for UI development.
- Keep manual scans sparse during development.
- Prefer adaptive scans over fixed high-frequency polling.
- Lower priority for events more than 24 hours away.
- Use urgent polling only for near-start or near-arbitrage events.
