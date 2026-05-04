# Frontend Guide

## Folder Structure

- `frontend/app/`: Next.js routes and page composition.
- `frontend/components/layout/`: Application shell, sidebar, top bar, and page headers.
- `frontend/components/common/`: Reusable UI states and generic widgets.
- `frontend/components/help/`: Help callouts and tooltips.
- `frontend/features/`: Feature-specific components as the UI grows.
- `frontend/hooks/`: Shared React hooks.
- `frontend/lib/api.ts`: API client functions.
- `frontend/lib/formatting.ts`: Formatting helpers.
- `frontend/types/`: Shared API and domain types.
- `frontend/theme/`: MUI theme and palette.

## Add A Page

1. Create `frontend/app/<route>/page.tsx`.
2. Fetch data through `frontend/lib/api.ts`.
3. Reuse `PageHeader`, `LoadingState`, `ErrorState`, and `EmptyState`.
4. Add shared response types in `frontend/types/api.ts`.
5. Add a sidebar item in `components/layout/AppSidebar.tsx` if it is a top-level page.

## Add A Reusable Component

Place generic UI in `frontend/components/common/`. Use `frontend/features/<feature>/` for components that only make sense in one workflow.

## State Management

Use React state, hooks, and small helper hooks. Do not introduce Redux without a clear need.

## API Client

All browser API calls should go through `frontend/lib/api.ts`. That keeps error behavior, base URL handling, and response types consistent.

## Linting And Formatting

Frontend linting and formatting are aligned with the sibling `anvil/UI` project.

- ESLint config: `frontend/eslint.config.mjs`
- Prettier config: `frontend/.prettierrc.cjs`
- Prettier ignores: `frontend/.prettierignore`

Run:

```bash
cd frontend
npm run lint
npm run lint:fix
npm run format
npm run format:check
```

The ESLint setup uses flat config, typed TypeScript rules, React/React Hooks rules, Next.js core web vitals, and portable equivalents for Anvil rules that depend on Anvil-only local plugins.
