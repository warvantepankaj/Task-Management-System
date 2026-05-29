# Feature: Pagination + Filtering + Sorting

## Why

The app currently has partial support and a real bug:

- `GET /tasks/admin` (`controllers/task_controller.py:31-36`) and `GET /tasks/user/me` (`controllers/task_controller.py:39-44`) return **every row**. `pages/Tasks.jsx` then filters and sorts client-side, which won't scale beyond a few dozen tasks.
- `GET /tasks/filtered` (`controllers/task_controller.py:72-91`) supports `page`/`size`/`status` but has a **bug**: the controller passes `user_id` to `services.task_service.get_tasks_paginated_filtered` (`services/task_service.py:76`) which does not accept that argument — a non-admin user gets a `TypeError`.
- Sort order is hardcoded `ORDER BY created_at DESC` in every list query.
- `schemas/common.py:6` defines `PaginatedResponse[T]` but no endpoint uses it; each endpoint invents its own shape (`/tasks/filtered` uses `data`, `/user/paginated` uses `users`).
- The frontend `components/tasks/TaskFilters.jsx` exposes a sort dropdown but the sort runs in-memory in `Tasks.jsx:applyFilters`, never reaching the server.

## Scope

**In scope**
- Server-side pagination, filtering, and sorting for tasks (`GET /tasks/filtered`) and users (`GET /user/paginated`).
- Unified `PaginatedResponse[T]` shape across both endpoints.
- Fix the broken `user_id` plumbing so non-admins see only their own tasks.
- Whitelist sort columns to prevent SQL injection (queries are built as raw strings).
- Frontend refactor: drop client-side filtering, push state into URL query params, add pagination controls.

**Out of scope**
- Cursor-based pagination (offset/limit is fine for current scale).
- Saved filter presets / "my views".
- Replacing the duplicate axios instances (`config/api.js` vs `services/api.js`) — flagged in `refresh-token.md`.

## API Contract

### `GET /tasks/filtered`

**Query parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `page` | int ≥ 1 | 1 | |
| `size` | int 1–100 | 10 | |
| `status` | `PENDING\|IN_PROGRESS\|COMPLETED` | — | optional |
| `assigned_to` | int | — | admin-only; ignored for non-admin (forced to current user) |
| `due_date_from` | ISO date | — | inclusive |
| `due_date_to` | ISO date | — | inclusive |
| `search` | string | — | matches `title` or `description` (ILIKE) |
| `sort_by` | `created_at\|due_date\|title\|status` | `created_at` | whitelisted |
| `sort_order` | `asc\|desc` | `desc` | |

**Response 200** — `PaginatedResponse[TaskResponse]`

```json
{
  "page": 2,
  "page_size": 10,
  "total": 47,
  "total_pages": 5,
  "data": [ { /* TaskResponse */ } ]
}
```

**Errors**
- `400` invalid `sort_by` / `sort_order` (rejected by Pydantic `Literal` type)
- `401` missing/invalid token
- `422` invalid query types

### `GET /user/paginated`

**Query parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `page` | int ≥ 1 | 1 | |
| `page_size` | int 1–100 | 10 | |
| `role` | `admin\|user` | — | optional |
| `is_active` | bool | — | optional |
| `search` | string | — | matches `username` or `email` (ILIKE) |
| `sort_by` | `created_at\|username\|email\|role` | `created_at` | whitelisted |
| `sort_order` | `asc\|desc` | `desc` | |

**Response 200** — `PaginatedResponse[UserOut]` (same shape as above).

Admin-only — non-admin requesters get `403`.

## Database Changes

None. Existing indexes on `tasks(status, due_date, created_at)` and `users(role, email)` already cover the new sort/filter columns.

## Files to Change

### Backend

- `schemas/common.py:6` — extend `PaginatedResponse[T]` to include `total_pages: int`.
- `schemas/task.py` — add `TaskListQuery` Pydantic model (or use FastAPI `Query` parameters) with `sort_by: Literal[...]`, `sort_order: Literal["asc","desc"]`, optional filter fields.
- `schemas/user.py` — add `UserListQuery` similarly. Also clean up `UserResponse` (currently has stray `status`, `complete_by` fields that belong to tasks).
- `queries/task_queries.py` — add a parameterized base query `GET_TASKS_FILTERED_BASE` with placeholders for dynamic WHERE clauses and a `{order_clause}` token (filled from a whitelist, not user input).
- `queries/user_queries.py` — same pattern for users.
- `dao/task_dao.py:74-109` — rewrite `get_tasks_paginated_filtered` to:
  - Accept `user_id: int | None`, `is_admin: bool`, and all new filters + sort args.
  - Build WHERE clause incrementally with parameter binding (`%s`); never interpolate user input into SQL.
  - Map `sort_by` through `ALLOWED_TASK_SORT = {"created_at", "due_date", "title", "status"}` — reject anything else.
  - Return `(rows, total_count)`.
- `dao/user_dao.py:42-60` — same treatment for `get_all_users_paginated`.
- `services/task_service.py:76-96` — update `get_tasks_paginated_filtered` signature to accept the new args; for non-admin callers, force `user_id = current_user.id` and ignore any `assigned_to` from the client.
- `services/user_service.py:17-20` — update `fetch_all_users_paginated` similarly.
- `controllers/task_controller.py:72-91` — declare all new `Query(...)` params; fix the bug by passing `user_id`/`is_admin` through to the service.
- `controllers/user_controller.py:79-98` — declare all new `Query(...)` params; require admin.
- Both controllers now return `PaginatedResponse[...]` directly (the service already builds the dict; just declare `response_model=PaginatedResponse[TaskResponse]` etc.).

### Frontend

- `src/services/api.js` (`taskAPI`, `userAPI`) — add `getTasks(params)` that calls `GET /tasks/filtered` with the full filter object; deprecate `getAllTasks`/`getMyTasks` callers in favor of this.
- `src/pages/Tasks.jsx` — remove the client-side `applyFilters` block; instead drive a `filters` + `page` state and refetch on change. Sync state to URL query params (`useSearchParams`) so refreshing keeps the view.
- `src/components/tasks/TaskFilters.jsx` — same UI; just hand the values back to `Tasks.jsx` unchanged (no in-memory filtering).
- `src/components/tasks/TaskList.jsx` — add a pagination footer (page number + total + Prev / Next). Skeleton loader keyed to `page_size`.
- `src/components/common/Pagination.jsx` — new small component (page selector with first/prev/next/last, current/total).
- `src/utils/constants.js` — add `TASK_SORT_OPTIONS`, `USER_SORT_OPTIONS`.

## Acceptance Criteria

- [ ] `GET /tasks/filtered?page=2&size=10&status=PENDING&sort_by=due_date&sort_order=asc&search=foo` returns a `PaginatedResponse` with the documented keys.
- [ ] Non-admin caller of `GET /tasks/filtered` only ever sees rows where `assigned_to = current_user.id`, regardless of any `assigned_to` query they send.
- [ ] Non-admin caller no longer crashes (`TypeError` from current bug is fixed).
- [ ] Invalid `sort_by=password_hash` is rejected with 422 (Literal validation) and the DAO additionally rejects unknown columns as a defense-in-depth.
- [ ] `/user/paginated` returns the same `PaginatedResponse` shape.
- [ ] Frontend `Tasks` page never holds more than `page_size` rows in state.
- [ ] Filter / sort / page state survives a hard refresh via URL query params.
- [ ] Empty state ("No tasks found") still works for an empty page result.

## Notes / Open Questions

- Should `due_date_from`/`due_date_to` be inclusive of the entire end day? Spec says inclusive — implementation must add 23:59:59 to `due_date_to` (or cast to `date`).
- Total-count cost: today's volume doesn't warrant a separate cached count; add `EXPLAIN ANALYZE` if `tasks` grows past ~100k rows.
- The deprecated `GET /tasks/admin` and `GET /tasks/user/me` should be **kept** for one release with a `Deprecation` header pointing to `/tasks/filtered`, then removed.
