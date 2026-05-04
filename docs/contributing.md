# Contributing

## Branch Naming

Use short descriptive names:

```text
feature/quota-dashboard
fix/stale-odds-validation
docs/onboarding
```

## Commit Style

Use concise imperative messages:

```text
Add demo seed data
Fix quota guard scan estimate
Document manual execution workflow
```

## Pull Request Checklist

- The change stays inside the safety boundaries.
- Routes are thin and business logic is in services.
- Provider code lives under `backend/app/providers/`.
- Shared frontend API calls live in `frontend/lib/api.ts`.
- Shared types live in `frontend/types/`.
- Tests were added or updated where behavior changed.
- Docs were updated for setup, API, data model, or behavior changes.
- Lint/tests/build were run and results are noted.

## Testing Expectations

Run:

```bash
./scripts/test.sh
./scripts/lint.sh
```

For frontend structure changes, also run:

```bash
cd frontend
npm run build
```

## Safety Checklist

Confirm the change does not automate betting, bookmaker login, captcha handling, KYC, geolocation, responsible gambling controls, or anti-bot bypassing.
