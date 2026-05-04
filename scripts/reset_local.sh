#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

printf "This will stop the local stack and delete Docker volumes, including the local Postgres database.\n"
printf "Type 'reset local' to continue: "
read -r confirmation

if [ "$confirmation" != "reset local" ]; then
  printf "Reset cancelled.\n"
  exit 0
fi

docker compose down -v
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head

printf "Local database reset and migrations applied.\n"
printf "Seed demo data now? [y/N] "
read -r seed_answer
case "$seed_answer" in
  y|Y|yes|YES)
    ./scripts/seed_local.sh
    ;;
  *)
    printf "Skipping seed data.\n"
    ;;
esac
