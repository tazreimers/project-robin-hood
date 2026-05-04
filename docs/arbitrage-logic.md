# Arbitrage Logic

## Implied Probability

For decimal odds:

```text
implied_probability = 1 / decimal_odds
```

## Two-Way Arbitrage

For outcomes A and B:

```text
total = (1 / odds_a) + (1 / odds_b)
margin = 1 - total
```

If `total < 1`, the prices imply less than 100% probability and may form an arbitrage.

Example:

```text
Home @ 2.20 => 0.4545
Away @ 2.25 => 0.4444
total = 0.8989
margin = 0.1011
```

## Three-Way Arbitrage

For home/draw/away markets:

```text
total = (1 / home_odds) + (1 / draw_odds) + (1 / away_odds)
margin = 1 - total
```

The same `total < 1` rule applies.

## Stake Allocation

Stakes are allocated in proportion to each leg's implied probability:

```text
stake_for_leg = total_stake * (leg_implied_probability / implied_probability_total)
expected_return = stake_for_leg * decimal_odds
```

Rounding is adjusted so the final stake total matches `DEFAULT_TOTAL_STAKE`.

## Filters

- Odds must be decimal odds above `1.01`.
- Snapshots older than `MAX_ODDS_AGE_SECONDS` are ignored.
- Candidate markets must pass market quality checks.
- Margin must be at least `MIN_ARBITRAGE_MARGIN`.

## Important Caveat

An opportunity is only actionable if every leg is still available at the displayed odds or better when manually checked.
