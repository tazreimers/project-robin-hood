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

The frontend currently has linting, formatting checks, and TypeScript checks through `next build`, but no test runner. When adding one, wire it into `frontend/package.json` as `npm test` so `scripts/test.sh` can run it automatically.

Frontend linting and formatting follow the sibling `anvil/UI` standards. Run:

```bash
cd frontend
npm run lint
npm run lint:fix
npm run format
npm run format:check
npm run build
```

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
npm run format:check
npm run build
./node_modules/.bin/tsc --noEmit --incremental false
```
