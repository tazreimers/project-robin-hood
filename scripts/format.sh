#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

if command -v ruff >/dev/null 2>&1; then
  printf "Running backend ruff format...\n"
  ruff format backend
else
  printf "No backend formatter configured; skipping backend format.\n"
fi

if npm --prefix frontend run | grep -q " format"; then
  printf "Running frontend formatter...\n"
  docker compose run --rm frontend npm run format
else
  printf "No frontend format script configured; skipping frontend format.\n"
fi
