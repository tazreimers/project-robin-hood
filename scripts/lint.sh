#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

if command -v ruff >/dev/null 2>&1; then
  printf "Running backend ruff lint...\n"
  ruff check backend
else
  printf "No backend linter configured; skipping backend lint.\n"
fi

if [ -f frontend/package.json ]; then
  printf "Running frontend lint...\n"
  docker compose run --rm frontend sh -c "npm ci && npm run lint"
fi

printf "Lint completed.\n"
