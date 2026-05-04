#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"

printf "Starting Project Robin Hood local stack...\n"
printf "Frontend: http://localhost:3000\n"
printf "Backend:  http://localhost:8000\n"
printf "API docs: http://localhost:8000/docs\n\n"

docker compose up --build
