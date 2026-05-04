#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

printf "Running backend tests...\n"
docker compose run --rm api python -m unittest discover -s app/tests

if npm --prefix frontend run | grep -q " test"; then
  printf "Running frontend tests...\n"
  docker compose run --rm frontend sh -c "npm ci && npm test"
else
  printf "No frontend test script configured; skipping frontend tests.\n"
fi

printf "Tests completed successfully.\n"
