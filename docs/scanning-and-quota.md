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

Estimated cost includes configured featured markets and event-level markets:

```text
featured cost = sports * regions * ODDS_MARKETS
event market cost = sports * ODDS_EVENT_MARKET_MAX_EVENTS * regions * ODDS_EVENT_MARKETS
```

The Odds API reports actual usage in `x-requests-last`; the app stores that value when present.

## Provider Headers

The Odds API response headers are captured into `api_usage_logs`:

- `x-requests-remaining`
- `x-requests-used`
- `x-requests-last`

## Why Polling Is Expensive

Real-time odds polling can burn provider credits quickly because cost scales by sports, regions, markets, and for player props the number of events queried. A scan across two sports, two regions, and three featured markets may cost far more than a single focused request. Event-level player prop scans are usually more expensive because each event is queried separately.

Examples:

- `SPORT_KEYS=afl`, `ODDS_REGIONS=au`, `ODDS_MARKETS=h2h`: `1` credit per scan when data is returned.
- `SPORT_KEYS=afl`, `ODDS_REGIONS=au`, `ODDS_MARKETS=h2h,totals`: `2` credits per scan when data is returned.
- `SPORT_KEYS=afl`, `ODDS_REGIONS=au`, `ODDS_MARKETS=h2h`, `ODDS_EVENT_MARKETS=player_disposals_over,player_goal_scorer_anytime`, `ODDS_EVENT_MARKET_MAX_EVENTS=8`: estimated `17` credits per scan when all event markets are returned.

## Recommended Strategy

- Use demo data for UI development.
- Keep manual scans sparse during development.
- Start with one sport and one or two event-level markets when testing props.
- Prefer adaptive scans over fixed high-frequency polling.
- Lower priority for events more than 24 hours away.
- Use urgent polling only for near-start or near-arbitrage events.
