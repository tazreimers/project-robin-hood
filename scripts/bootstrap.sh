#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

status=0

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    printf "ok: %s found\n" "$1"
  else
    printf "missing: %s\n" "$1"
    status=1
  fi
}

check_command docker

if docker compose version >/dev/null 2>&1; then
  printf "ok: docker compose found\n"
else
  printf "missing: docker compose plugin\n"
  status=1
fi

if [ -f frontend/package.json ]; then
  check_command node
fi

check_command python3

if [ ! -f .env ]; then
  cp .env.example .env
  printf "created .env from .env.example\n"
else
  printf "ok: .env already exists; not overwriting\n"
fi

if [ "$status" -ne 0 ]; then
  printf "\nBootstrap checks failed. Install the missing tools above and rerun ./scripts/bootstrap.sh.\n"
  exit "$status"
fi

printf "\nNext steps:\n"
printf "  1. Review .env and set ODDS_API_KEY if you want live odds.\n"
printf "  2. Run ./scripts/dev.sh to start the stack.\n"
printf "  3. Run ./scripts/seed_local.sh for demo data without an API key.\n"
printf "  4. Open http://localhost:3000 and http://localhost:8000/docs.\n"
