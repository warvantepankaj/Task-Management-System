# Feature: Testing (Backend → Frontend → E2E)

## Why

- Zero test infrastructure exists today: no `pytest`, no `vitest`, no `tests/` or `__tests__/` directories, no fixtures, no CI hooks.
- `httpx==0.28.1` is already in `Backend/requirements.txt` (unused) — it's the recommended FastAPI test client.
- Without tests, the other four features in this batch (pagination, refresh tokens, password reset, websockets) ship as untested code — high risk for regressions, especially in the auth flow.

This spec establishes the **stack, layout, and minimum bar**. It does not enumerate every test case (those live alongside each feature's spec).

## Scope

**In scope**
- Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient` against a FastAPI app instance; isolated test DB; per-test transaction rollback.
- Frontend: `vitest` + `@testing-library/react` + `msw` (HTTP mocking).
- E2E: `playwright` at the repo root; one smoke spec per critical flow.
- Coverage tooling (`pytest-cov` + `vitest --coverage`) with a baseline target.
- Conventions: directory layout, fixture naming, "arrange/act/assert" style.

**Out of scope**
- CI pipeline configuration (GitHub Actions / etc.).
- Visual regression / Storybook.
- Load testing.
- Mutation testing.

## API Contract

N/A — this feature does not add API endpoints. The contract here is **developer-facing conventions** for writing tests.

## Database Changes

A separate database for tests: `Task_Management_System_DB_TEST`. Apply `schema.sql` to it once at session start. Each test wraps work in a transaction that rolls back at teardown — fast and isolated.

Test DB connection string is read from `TEST_DATABASE_NAME` env (defaults to `Task_Management_System_DB_TEST`). Other DB env vars (`DATABASE_USER`, `_PASSWORD`, `_HOST`, `_PORT`) are shared with dev.

## Files to Change

### Backend

- `requirements.txt` — add `pytest==8.*`, `pytest-asyncio==0.24.*`, `pytest-cov==5.*`. `httpx` already present.
- `pytest.ini` (or `pyproject.toml [tool.pytest.ini_options]`) at `Backend/`:
  ```ini
  [pytest]
  testpaths = tests
  asyncio_mode = auto
  addopts = -ra --strict-markers --cov=. --cov-report=term-missing --cov-fail-under=70
  ```
- `Backend/conftest.py` — top-level fixtures:
  - `app` (session scope) — imports the FastAPI app, overrides `get_db` to use the test DB.
  - `db_conn` (function scope) — yields a psycopg2 connection; rolls back on teardown.
  - `client` (function scope) — `httpx.AsyncClient(app=app, base_url="http://test")`.
  - `admin_user` / `regular_user` (function scope) — insert via DAO, return dict.
  - `admin_token` / `user_token` — call `/login`, return `Bearer ...` string.
  - `authed_client(client, admin_token)` — client with auth header preset.
- `Backend/tests/` layout:
  ```
  Backend/tests/
  ├── conftest.py             # shared fixtures (above)
  ├── unit/
  │   ├── test_security.py    # hash_password, verify_password
  │   ├── test_jwt.py         # token encode/decode, expiry, token_type guard
  │   └── test_dao_tasks.py   # DAO with real DB
  └── integration/
      ├── test_auth_login.py
      ├── test_auth_refresh.py
      ├── test_auth_password_reset.py
      ├── test_tasks_crud.py
      ├── test_tasks_pagination.py
      ├── test_users_pagination.py
      └── test_ws_tasks.py    # uses httpx websocket client
  ```
- Per-feature spec calls out specific cases it requires; this file just defines the harness.

### Frontend

- `package.json` — add devDependencies:
  - `vitest`, `@vitest/coverage-v8`
  - `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`
  - `jsdom`
  - `msw` (request mocking)
- `package.json` scripts:
  ```json
  {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "e2e": "playwright test"
  }
  ```
- `vite.config.js` — add:
  ```js
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    coverage: { reporter: ['text', 'html'], thresholds: { lines: 60 } }
  }
  ```
- `src/test/setup.js` — new. Imports `@testing-library/jest-dom`, sets up MSW server (`beforeAll/afterEach/afterAll`).
- `src/test/server.js` — new. MSW handlers for `/login`, `/auth/refresh`, `/tasks/filtered`, etc.
- `src/test/test-utils.jsx` — new. `renderWithProviders(ui)` that wraps in `<AuthProvider>` and `<MemoryRouter>`.
- Initial test files (skeletons; per-feature specs add real assertions):
  - `src/pages/__tests__/Login.test.jsx`
  - `src/pages/__tests__/Tasks.test.jsx`
  - `src/components/tasks/__tests__/TaskFilters.test.jsx`
  - `src/context/__tests__/AuthContext.test.jsx`
  - `src/services/__tests__/api.test.js` (interceptor behavior)
  - `src/hooks/__tests__/useTaskSocket.test.js` (uses MSW WebSocket support)

### E2E

- Repo-root `playwright.config.ts`:
  - `testDir: './e2e'`
  - `webServer: [{ command: 'pnpm --filter ./Frontend dev', url: 'http://localhost:3000', reuseExistingServer: !process.env.CI }, { command: 'uvicorn main:app --port 8000', cwd: './Backend', url: 'http://localhost:8000/docs' }]`
  - Projects: chromium only initially.
- `e2e/` directory:
  - `auth.spec.ts` — login happy path, login failure.
  - `tasks.spec.ts` — admin creates task, user sees it (relies on WebSocket feature).
  - `password-reset.spec.ts` — request reset, follow the captured link (dev-mode logged URL), set new password, log in.

## Acceptance Criteria

- [ ] `cd Backend && pytest` runs and reports pass with coverage ≥ 70% on services/, ≥ 60% on dao/.
- [ ] `cd Frontend && pnpm test:run` runs and reports pass with coverage ≥ 60% on changed files.
- [ ] `pnpm e2e` from repo root passes the auth smoke spec end-to-end against locally-running backend + frontend.
- [ ] Test DB is fully isolated: running tests does **not** touch `Task_Management_System_DB`. Verified by intentionally pointing dev DB at a no-op user and confirming tests still pass.
- [ ] Test runtime: backend suite under 30s on a clean run; frontend suite under 15s.
- [ ] At least one test exists for each of: login success, login failure, refresh-token rotation, password-reset happy path, paginated task list, WebSocket task.created event.
- [ ] `--strict-markers` is on; tests don't accidentally use unregistered markers.
- [ ] CI-ready: `pytest`, `pnpm test:run`, and `pnpm e2e` all exit 0 on a clean main branch.

## Notes / Open Questions

- **Per-test transaction rollback**: with psycopg2 + raw SQL, this is straightforward — open a transaction in the `db_conn` fixture, monkeypatch `get_db` to yield the same connection without committing, then `ROLLBACK` on teardown. Works because the app uses one connection per request via `Depends(get_db)`.
- **WebSocket testing**: `httpx` does not have WS support; use FastAPI's `TestClient.websocket_connect` (sync) for those tests. Mark them with `@pytest.mark.ws`.
- **Coverage targets are starting points**: services 80% / DAOs 70% / frontend 60% are aspirational floors, not contracts. Adjust after first three weeks of real numbers.
- **Test data**: prefer fixtures that create their own data over a "seed dump" SQL file — explicit and self-contained.
- **Snapshots**: avoid for now. Snapshot tests on JSON shapes get out of sync with API evolution and add review noise.
- **E2E flakiness**: use `await expect(locator).toBeVisible()` style (auto-retrying), never `page.waitForTimeout`. If a flake appears, the spec must be tagged `@flaky` and an issue opened; don't disable silently.
