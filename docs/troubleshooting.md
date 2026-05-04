# Troubleshooting

## Docker Not Running

Start Docker Desktop or your Docker daemon, then rerun `./scripts/bootstrap.sh`.

## Database Connection Failed

Check Postgres health:

```bash
docker compose ps postgres
docker compose logs postgres
```

Make sure `.env` uses the Compose host `postgres` for containers.

## Migrations Failed

Run:

```bash
docker compose run --rm api alembic upgrade head
```

If local data can be discarded, use `./scripts/reset_local.sh`.

## Redis Not Reachable

Check:

```bash
docker compose ps redis
docker compose logs redis
```

Celery jobs need Redis to queue and report status.

## Frontend Cannot Reach Backend

Confirm `NEXT_PUBLIC_API_URL` points to `http://localhost:8000` and that `curl http://localhost:8000/health` works.

## API Key Missing

`ODDS_API_KEY` is optional for demo data. Live provider scans need a valid key in `.env`.

## Quota Exhausted

Check `/api-usage` or the API Usage page. Reduce scan frequency, narrow sports/markets, or wait for provider quota reset.

## No Opportunities Found

This can be normal. Try:

- Seed demo data: `./scripts/seed_local.sh`
- Include stale opportunities in the UI.
- Check scan runs for errors.
- Verify configured sports and regions.
- Confirm odds snapshots are fresh.
