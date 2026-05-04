# Normalisation

Normalisation keeps provider and bookmaker data aligned before arbitrage detection.

## Why It Matters

Different feeds can use different team names, market names, start times, and sport keys. Without normalisation, the app may split the same event into multiple rows or compare mismatched markets.

## Team Aliases

`team_aliases` maps a source alias to a canonical team name for a sport. Matching order:

1. Exact alias.
2. Cleaned alias.
3. Fuzzy alias above threshold.
4. Fallback to the source name.

## Market Aliases

`market_aliases` maps provider market labels to canonical market types such as `h2h`.

## Event Matching Confidence

Events match when normalized keys match, or when team sets match and start times are within tolerance. Confidence is reduced when fuzzy team names or wider start-time deltas are involved.

## Common Failure Cases

- Team nickname differs between providers.
- Event start time moves.
- Market labels differ for the same betting market.
- Line markets have different lines.
- Provider omits one required outcome.

Add aliases when a failure is repeated and safe to normalize.
