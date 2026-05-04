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
  if command -v npm >/dev/null 2>&1 && [ -d frontend/node_modules ]; then
    npm --prefix frontend run lint
  elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    docker compose run --rm frontend sh -c "npm ci && npm run lint"
  else
    printf "Frontend dependencies are not installed. Run ./scripts/bootstrap.sh or npm --prefix frontend install.\n"
    exit 1
  fi
fi

printf "Lint completed.\n"
