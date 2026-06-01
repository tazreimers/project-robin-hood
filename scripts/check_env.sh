#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
else
  printf "No .env file found. Run ./scripts/bootstrap.sh to create one from .env.example.\n"
fi

required_vars="DATABASE_URL REDIS_URL"
defaulted_vars="SPORT_KEYS ODDS_MARKETS ODDS_EVENT_MARKET_MAX_EVENTS DEFAULT_TOTAL_STAKE MIN_ARBITRAGE_MARGIN MAX_ODDS_AGE_SECONDS DAILY_QUOTA_BUDGET MIN_REQUESTS_REMAINING_BUFFER MAX_SCANS_PER_HOUR ENABLE_QUOTA_GUARD LOW_PRIORITY_SCAN_MINUTES NORMAL_PRIORITY_SCAN_MINUTES HIGH_PRIORITY_SCAN_SECONDS URGENT_PRIORITY_SCAN_SECONDS NEAR_ARB_THRESHOLD MIN_MARKET_CONFIDENCE MAX_EVENT_START_TIME_DIFF_MINUTES"
optional_vars="ODDS_API_KEY ODDS_REGIONS ODDS_EVENT_MARKETS"
missing=0

for name in $required_vars; do
  eval "value=\${$name:-}"
  if [ -z "$value" ]; then
    printf "missing required: %s\n" "$name"
    missing=1
  else
    printf "ok required: %s\n" "$name"
  fi
done

for name in $defaulted_vars; do
  eval "value=\${$name:-}"
  if [ -z "$value" ]; then
    printf "using app default: %s (add to .env to override)\n" "$name"
  else
    printf "ok configured: %s\n" "$name"
  fi
done

for name in $optional_vars; do
  eval "value=\${$name:-}"
  if [ -z "$value" ]; then
    printf "optional unset: %s\n" "$name"
  else
    printf "ok optional: %s\n" "$name"
  fi
done

if [ "$missing" -ne 0 ]; then
  printf "\nEnvironment check failed. See .env.example for safe local defaults.\n"
  exit 1
fi

printf "\nEnvironment check passed. ODDS_API_KEY is optional when using demo seed data.\n"
