# Task Management System

A full-stack task management app with **role-based access control**, **real-time collaboration**, and a **drag-and-drop Kanban board**. FastAPI backend (PostgreSQL + JWT) and React 19 / Vite / Tailwind frontend.

## Features

- **Auth**
  - Registration + login with JWT.
  - 15-minute access tokens + 14-day rotating refresh tokens with server-side revocation (`refresh_tokens` table).
  - `POST /auth/refresh` rotates the pair; `POST /auth/logout` revokes the supplied refresh token.
  - Single-flight axios interceptor: concurrent 401s share one `/auth/refresh` call.
- **Password reset**
  - `POST /auth/forgot-password` (always 202 — no email-exists leak).
  - `POST /auth/reset-password` with a one-hour, single-use, SHA-256-hashed token.
  - SMTP via `fastapi-mail`; if no SMTP env is set, the reset link is logged to stdout for local dev.
  - Successful reset revokes every refresh token for that user (logs them out everywhere).
- **Server-side pagination, filtering, sorting** on `GET /tasks/filtered` and `GET /user/paginated`.
  - Task filters: `status`, `assigned_to` (admin), `due_date_from`, `due_date_to`, `search`, `sort_by`, `sort_order`.
  - User filters: `role`, `is_active`, `search`, `sort_by`, `sort_order`.
  - Sort columns whitelisted in the DAO; non-admins are forced to their own rows.
  - Unified `PaginatedResponse[T]` shape (`page`, `page_size`, `total`, `total_pages`, `data`).
  - Frontend persists filter / sort / page in the URL query (`useSearchParams`).
- **Real-time WebSocket channel** at `WS /ws/tasks?token=<jwt>`
  - Lifecycle events: `task.created`, `task.updated`, `task.status_changed`, `task.deleted`.
  - Live drag relay: `task.drag_start`, `task.drag_move` (60–120 Hz), `task.drag_end`, `task.drag_rejected`.
  - Per-task drag lock with a 5-second stale-lock reaper.
  - Auto-reconnect with exponential back-off; on close code `4401` the client refreshes the access token and reconnects.
- **Kanban board** at `/tasks?view=board`
  - Three columns keyed to `TaskStatus`. Drag-and-drop via `@dnd-kit/core` + `@dnd-kit/sortable`.
  - Optimistic UI: card snaps into the new column on drop, reconciles with the server response.
  - **Live multi-user drag preview**: when another user picks up a card, every other viewer sees a near-opaque ghost card following that user's cursor in real time. Implemented via framer-motion `MotionValue`s so cursor frames write straight to the DOM (no React re-render in the hot path).
  - Toggle between **List** and **Board** views in the `/tasks` header.

## Tech Stack

**Backend**

- FastAPI · Uvicorn (with `websockets`) · psycopg2 + raw SQL · python-jose (JWT, HS256) · passlib/bcrypt · fastapi-mail · PostgreSQL 14+.

**Frontend**

- React 19 · Vite 7 · Tailwind CSS 4 · React Router 7 · Axios · React Hook Form + Zod · framer-motion · `@dnd-kit/*` · lucide-react · react-hot-toast.

## Project Structure

```
Task_Management_System/
├── Backend/
│   ├── controllers/      # auth_controller, task_controller, user_controller, ws_controller
│   ├── services/         # auth_service, task_service, user_service, email_service
│   ├── dao/              # task_dao, user_dao, refresh_token_dao, password_reset_dao
│   ├── queries/          # raw SQL strings
│   ├── schemas/          # Pydantic models (incl. PaginatedResponse[T])
│   ├── core/             # config, jwt, ws_manager, gemini
│   ├── database/         # PostgreSQL session
│   ├── utils/            # security, dependencies
│   ├── services/email_templates/   # password reset HTML + TXT
│   └── main.py
├── Frontend/
│   └── src/
│       ├── pages/        # Login, Signup, ForgotPassword, ResetPassword, Dashboard, Tasks, KanbanBoard
│       ├── components/
│       │   ├── common/   # Button, Input, Modal, Navbar, Pagination, LoadingSpinner
│       │   ├── tasks/    # TaskCard, TaskFilters, TaskList, StatusBadge, TaskForm
│       │   └── kanban/   # KanbanColumn, KanbanCard, DragGhost, ViewToggle
│       ├── hooks/        # useAuth, useTaskSocket, useDragBroadcast
│       ├── services/     # api.js (single axios instance + refresh interceptor)
│       └── utils/        # constants, helpers
├── schema.sql            # users, tasks, task_comments, refresh_tokens, password_reset_tokens
└── README.md
```

## Setup

### 1. PostgreSQL

```bash
psql -U postgres -d Task_Management_System_DB -f schema.sql
```

Tables created: `users`, `tasks`, `task_comments`, `refresh_tokens`, `password_reset_tokens`.

### 2. Backend

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Create `Backend/.env` (see `Backend/.env.example` for the full list):

```env
DATABASE_NAME=Task_Management_System_DB
DATABASE_USER=postgres
DATABASE_PASSWORD=...
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Required. Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_SECRET=<random 64-byte URL-safe string>
ACCESS_TOKEN_TTL_MIN=15
REFRESH_TOKEN_TTL_DAYS=14

# Optional. If unset, password-reset links are logged to stdout instead of sent.
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
MAIL_FROM=
FRONTEND_URL=http://localhost:3000
RESET_TOKEN_TTL_MIN=60
```

Start the API (must use the venv's uvicorn so the `websockets` library is loaded):

```powershell
.\.venv\Scripts\uvicorn.exe main:app --reload --port 8000
```

OpenAPI docs at `http://localhost:8000/docs`.

### 3. Frontend

```powershell
cd Frontend
pnpm install
pnpm dev          # http://localhost:3000
```

Vite proxies `/api` → `http://localhost:8000` (see `vite.config.js`).

## API Overview

### Auth

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/register` | Create a new account. |
| `POST` | `/login` | Returns `{ access_token, refresh_token, user, expires_in }`. |
| `POST` | `/auth/refresh` | Rotate the refresh token; returns a new pair. |
| `POST` | `/auth/logout` | Revoke the supplied refresh token. |
| `POST` | `/auth/forgot-password` | Always 202. Dispatches (or logs) a reset link. |
| `POST` | `/auth/reset-password` | Consume a one-hour token, set new password, revoke all refresh tokens for that user. |

### Tasks

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/tasks/create_task` | Admin only. |
| `GET` | `/tasks/filtered` | Paginated + filtered + sorted list. Non-admins are scoped to their own tasks. |
| `PUT` | `/tasks/{task_id}/admin` | Admin updates any field on a task. |
| `PATCH` | `/tasks/{task_id}/status` | Admin can change any task; user can change their own. Triggers `task.status_changed` over WS. |
| `DELETE` | `/tasks/{task_id}/delete` | Admin only. |

### Users

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/user/paginated` | Paginated + filtered + sorted user list (admin). |
| `GET` | `/user/id/{id}` · `/user/email/{email}` | Lookup. |
| `POST` | `/user/create_user` | Admin only. |

### WebSocket

| Path | Purpose |
|---|---|
| `WS /ws/tasks?token=<jwt>` | Auth via access JWT; closes with code `4401` if invalid/expired. Receives lifecycle + drag events; clients can send `task.drag_start` / `task.drag_move` / `task.drag_end`. |

## Authentication Model

- Access tokens are short-lived (15 min) JWTs (`HS256`) with a `token_type: "access"` claim — refresh tokens cannot be used as access tokens.
- Refresh tokens are opaque, URL-safe 32-byte strings stored hashed (`token_hash = sha256(token)`) in `refresh_tokens` with `expires_at`, `revoked_at`, `user_agent`, `ip`.
- Token rotation on every `/auth/refresh`: the old refresh token row is marked `revoked_at = NOW()` and a new pair is issued. A replayed refresh token returns 401.
- The frontend stores both tokens in `localStorage` under `access_token` / `refresh_token`. An axios interceptor performs single-flight refresh on 401 — concurrent failing requests share one in-flight `/auth/refresh` call.

## Real-time Architecture (single-process)

- `ConnectionManager` (`Backend/core/ws_manager.py`) keeps a per-user-id map of active sockets and a per-task-id drag-lock map with a 5-second stale-lock reaper.
- Mutation services (`create_task`, `admin_update_task`, `user_update_task_status`, `delete_task`) are `async` and broadcast a lifecycle event after the DB commit.
- Drag events are relayed by the server — they never hit the database — and the originating socket is skipped to avoid echoing the actor's own cursor into the actor's own tab.
- Scaling beyond one uvicorn worker would require Redis pub/sub on the manager; not included.

## Security Notes

- `JWT_SECRET` must be set in the environment; the app refuses to start if it is missing or still equal to the placeholder `"TOP_SECRET"`.
- Passwords are bcrypt-hashed via `passlib`.
- SQL is built with parameterized queries (`%s`). Sort-column inputs are whitelisted in the DAO so even a Pydantic-validation bypass can't reach raw SQL.
- `POST /auth/forgot-password` always returns 202 to avoid leaking which emails are registered.
- Refresh tokens are stored as SHA-256 hashes — a database dump does not yield usable refresh tokens.
