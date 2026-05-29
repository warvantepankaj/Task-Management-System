# Feature: WebSockets (Real-Time Task Updates)

## Why

- `pages/Tasks.jsx` only refreshes its list when the user manually navigates or after a mutation; if admin A creates a task assigned to user B, user B sees nothing until they refresh.
- No WebSocket route, no broadcaster, no client. The backend is pure REST today.
- The app already has a notion of "rooms" implicitly (admins see all tasks, users see their own), which maps cleanly onto WebSocket broadcast rules.

This spec adds a single channel `/ws/tasks` that emits task lifecycle events. **Scope is intentionally narrow** to task events only; comments and presence are not included.

## Scope

**In scope**
- `WS /ws/tasks?token=<access_jwt>` endpoint.
- In-process `ConnectionManager` keyed by `user_id` with role bucketing (`admin` vs `user`).
- Broadcast on `create_task`, `admin_update_task`, `user_update_task_status`, `delete_task`.
- **Live drag relay** for the Kanban board: `task.drag_start`, `task.drag_move`, `task.drag_end`, `task.drag_rejected` events relayed without DB writes.
- Drag lock semantics: first `drag_start` wins; conflicts get `drag_rejected`; auto-release after 5 s of silence.
- Frontend hook `useTaskSocket` that merges incoming events into the Tasks/Kanban state.
- Auto-reconnect with exponential backoff; reconnect with refreshed access token if 4401-closed.

**Out of scope**
- Multi-process broadcasting (no Redis pub/sub). Single-worker uvicorn is assumed; spec flags this as a scale ceiling.
- Comment streaming, typing indicators, presence ("who's online").
- Native push notifications.
- socket.io. Spec uses **native WebSockets** (FastAPI's built-in `WebSocket`) — no extra deps.
- Persisting drag-move history (the events are transient and never hit the DB).

## API Contract

### `WS /ws/tasks?token=<jwt>`

**Handshake**
- Client opens `ws://host:8000/ws/tasks?token=<access_token>`.
- Server validates JWT via `core/jwt.decode_token`; checks `token_type == "access"`.
- On invalid/expired token, server closes with code **4401** (custom, "unauthorized"). Client treats 4401 as "refresh access token then reconnect".

**Server → client message envelope**

```json
{
  "event": "task.created" | "task.updated" | "task.status_changed" | "task.deleted",
  "task": { /* TaskResponse */ } | { "id": 42 },
  "actor_id": 1,
  "ts": "2026-05-28T12:34:56Z"
}
```

For `task.deleted` the `task` payload only carries `{ "id": ... }`.

**Client → server messages**
- `{"type":"ping"}` → server replies `{"type":"pong"}`. (Optional; built-in WS ping/pong frames also fine.)
- `{"event":"task.drag_start", "data": { "task_id": int, "from_status": str }}` — client signals it has picked up a card.
- `{"event":"task.drag_move", "data": { "task_id": int, "x": int, "y": int, "over_status": str | null }}` — client streams cursor position (throttled to 30 Hz). Server drops any message arriving more than once per 30 ms from the same socket.
- `{"event":"task.drag_end", "data": { "task_id": int, "cancelled": bool }}` — client signals release. If a status change was committed, the existing `PATCH /tasks/{id}/status` REST call triggers a normal `task.status_changed` broadcast.
- All other inbound messages are ignored.

**Broadcast rules**

| Event | Sent to |
|---|---|
| `task.created` | all admins **plus** `assigned_to` user |
| `task.updated` | all admins **plus** `assigned_to` user (old and new, if reassigned) |
| `task.status_changed` | all admins **plus** `assigned_to` user |
| `task.deleted` | all admins **plus** previous `assigned_to` user |
| `task.drag_start` | every connected client (admin + assignee + actor's own other tabs) — server first checks no other drag is active for this `task_id`; if one is, sends `task.drag_rejected` only to the requester instead |
| `task.drag_move` | every connected client *except* the originating socket (actor's own tabs **do** receive it so the cursor stays in sync across tabs) |
| `task.drag_end` | every connected client; server clears the per-`task_id` drag lock |
| `task.drag_rejected` | only the requesting client (1:1 reply, not broadcast) |

The actor (the user who caused the change) **also** receives lifecycle events on their other tabs — keeps multi-tab consistency. For `drag_move`, the originating socket is skipped (the client is already showing its own cursor); the actor's other tabs do receive it.

### Drag lock state

The `ConnectionManager` holds an in-memory map `active_drags: dict[task_id, { user_id, started_at }]`. A new `drag_start` for a `task_id` already in the map is rejected unless `started_at < now - 5s` (stale lock auto-released).

## Database Changes

None.

## Files to Change

### Backend

- `core/ws_manager.py` — new. `ConnectionManager` with:
  - `connections: dict[int, set[WebSocket]]` (per user_id)
  - `admin_user_ids: set[int]` (cache)
  - `active_drags: dict[int, dict]` (per task_id: `{ user_id, socket_id, started_at }`)
  - `async def connect(ws, user_id, role)`, `disconnect(ws, user_id)` — disconnect must also clear any drag locks held by that socket.
  - `async def broadcast_to_users(user_ids: set[int], payload: dict, skip_socket: WebSocket | None = None)`.
  - `async def broadcast_task_event(event: str, task: dict, actor_id: int)` — lifecycle events. Builds recipient set per the rules above.
  - `async def handle_drag_event(socket, user_id, event, data)` — drag relay: validates the lock, broadcasts to peers (skipping originating socket for `drag_move`), sends `drag_rejected` 1:1 on conflict, expires stale locks.
  - Background task that scans `active_drags` every second and emits a synthetic `drag_end` for any lock older than 5 s.
- `controllers/ws_controller.py` — new. `@router.websocket("/ws/tasks")` accepts the connection, validates token, registers with manager, then loops on `receive_json`. Inbound `task.drag_*` events route to `ws_manager.handle_drag_event`. On `WebSocketDisconnect`, removes from manager and clears any drag locks owned by this socket.
- `main.py` — `app.include_router(ws_router)`.
- `services/task_service.py` — at the end of each mutating function (`create_task`, `admin_update_task`, `user_update_task_status`, `delete_task`), call `await ws_manager.broadcast_task_event(...)`. These methods need to become `async` (currently sync) — keep the sync DAO layer; the async-ification is shallow.
  - If we don't want to convert the whole stack to async, the alternative is to schedule the broadcast via `asyncio.create_task(...)` from a small adapter. Spec recommends the conversion since FastAPI handles both.
- `controllers/task_controller.py` — update endpoints to `async def` to match the now-async services.

### Frontend

- `src/hooks/useTaskSocket.js` — new. Signature:
  ```js
  useTaskSocket({
    onCreated, onUpdated, onStatusChanged, onDeleted,
    onDragStart, onDragMove, onDragEnd, onDragRejected
  })
  ```
  Returns `{ status: "connecting" | "open" | "closed", send(event, data) }`.
  - Opens `ws://localhost:8000/ws/tasks?token=...` using the access token from storage.
  - Reconnect logic: exponential backoff 1s → 2s → 4s → 8s → 16s, capped at 30s. Resets on successful open.
  - On close code `4401`, calls the same `/auth/refresh` helper used by the axios interceptor (see `refresh-token.md`), then reconnects.
  - `send` is a no-op when the socket isn't open (drops with a `console.warn`).
- `src/hooks/useDragBroadcast.js` — new. Wraps `useTaskSocket.send` with a 30 Hz throttle for `task.drag_move` (one frame per ~33 ms). Drops frames if `ws.bufferedAmount > 64 * 1024` to prevent backlog.
- `src/pages/Tasks.jsx` — wire `useTaskSocket` with callbacks that:
  - `onCreated(task)` — `setTasks(prev => prev.some(t => t.id === task.id) ? prev : [task, ...prev])`.
  - `onUpdated(task)` — replace by id.
  - `onStatusChanged(task)` — same as updated.
  - `onDeleted({ id })` — filter out.
  - Skip the update if it conflicts with optimistic UI (compare `actor_id` to `user.id`).
- `src/components/common/Navbar.jsx` (or a small badge component) — small "Live" indicator that turns gray on disconnect; useful for debugging and reassures users that auto-updates are on.

## Acceptance Criteria

### Lifecycle events
- [ ] Two browser sessions: admin in tab 1 creates a task assigned to user B. Tab 2 (logged in as B) sees the new task card within 1 second with no manual refresh.
- [ ] When admin updates a task, both tabs reflect the change immediately.
- [ ] When a non-recipient user changes their own task's status, an unrelated user's tab does **not** receive that event.
- [ ] `task.deleted` removes the card from list immediately, and the empty state appears if it was the last task.
- [ ] Multiple tabs of the same user all stay in sync (actor's own tabs also receive the event).

### Drag relay
- [ ] User A grabs a card on the Kanban board; within 100 ms user B sees the card flagged with a "being moved by A" pill.
- [ ] As A moves the cursor, B's screen shows a ghost card following A's position; frame rate is smooth (≥ 15 fps perceived) on local network.
- [ ] If two users simultaneously grab the same card, one receives `task.drag_rejected` and the card stays under the other user's control.
- [ ] A user closes their tab mid-drag; within 5 s every other client clears the lock and the card returns to its original column.
- [ ] On A's drop into a new column, the existing `PATCH /tasks/{id}/status` runs once and B's screen shows the card snap to the new column via the `task.status_changed` event.

### Auth & resilience
- [ ] Invalid token at handshake closes with code 4401; client refreshes access token via `/auth/refresh` and successfully reconnects with the new token.
- [ ] Server-side restart causes clients to reconnect within ~30s (backoff cap) and resume receiving events.
- [ ] No memory leak: opening and closing the page 50 times does not leave 50 entries in `connections[user_id]` server-side.
- [ ] Drag-move backpressure: artificially blocking a slow client does not stall the server's broadcast loop for other clients.

## Notes / Open Questions

- **Auth via query param**: putting the JWT in the URL is acceptable (the URL never leaves the browser → server hop and isn't logged client-side), but request headers can't be set on a browser `WebSocket`. Alternative: a short-lived ticket endpoint (`POST /ws-ticket` → 30s ticket) — overkill for now, noted for future hardening.
- **Single-process limit**: in-memory `ConnectionManager` works fine for one uvicorn worker. Scaling beyond one worker requires Redis pub/sub (or NATS). Spec recommends planning that move when concurrent users cross ~500 or when running behind multiple replicas.
- **Backpressure**: if a client is slow, `ws.send_text()` may block. Wrap sends in `asyncio.wait_for(..., timeout=5s)`; on timeout, drop and force-close that connection.
- **Coordinate with `refresh-token.md`**: the `useTaskSocket` reconnect-after-4401 path depends on the refresh-token implementation landing first.
- **Coordinate with `pagination-filtering-sorting.md`**: incoming events that don't match the current filter still arrive at the client. Frontend must check filters before inserting (or, simpler: always re-fetch on event, debounced 300ms). Spec recommends the in-memory merge approach for snappy UX and the debounced refetch as a fallback.
