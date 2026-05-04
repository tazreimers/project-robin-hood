# Testing

## Backend

Backend tests live in `backend/app/tests/` and use `unittest`. Most service tests use in-memory SQLite.

Run:

```bash
cd backend
python -m unittest discover -s app/tests
```

Or through Docker:

```bash
./scripts/test.sh
```

## Frontend

The frontend currently has linting and TypeScript checks but no test runner. When adding one, wire it into `frontend/package.json` as `npm test` so `scripts/test.sh` can run it automatically.

## Always Test

- Arbitrage math and stake allocation.
- Normalisation and alias matching.
- Provider adapters with mocked responses.
- Quota guard decisions.
- Market quality checks.
- Manual execution calculations.
- API routes for new workflows.

## Useful Checks

```bash
cd frontend
npm run lint
npm run build
./node_modules/.bin/tsc --noEmit --incremental false
```
