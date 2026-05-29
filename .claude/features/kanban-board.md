# Feature: Kanban Board with Live Multi-User Drag

## Why

- The app today shows tasks only as a card grid (`src/pages/Tasks.jsx`) with client-side filtering. Users coming from modern PM tools expect a board view.
- The WebSocket spec (`websockets.md`) is being added at the same time — pairing it with a board makes "real-time collaboration" tangible: when one user moves a card, every other user watching the board sees the card move under their finger as it happens.
- No drag-and-drop library is installed and no `KanbanColumn` / `KanbanCard` component exists. There is no existing DnD code anywhere in the frontend (grep confirms zero `onDragStart` / `onDrop` handlers).
- The design system across `Dashboard.jsx`, `Tasks.jsx`, `Login.jsx`, `Signup.jsx` is consistent (DM Sans, indigo/purple gradients, `rounded-xl shadow-md` cards, `bg-gradient-to-br from-gray-50 to-gray-100` page bg). The new board must visually belong to the same family.

## Scope

**In scope**
- List ↔ Board view toggle on `/tasks` (single route, `?view=list|board` query param).
- Three columns mapped to `TaskStatus` enum (`PENDING`, `IN_PROGRESS`, `COMPLETED`).
- Drag-and-drop via `@dnd-kit/core` + `@dnd-kit/sortable` + `@dnd-kit/utilities`.
- Drop-across-columns persists status via existing `PATCH /tasks/{task_id}/status` (`controllers/task_controller.py:59-68`).
- **Live ghost preview** of in-progress drags across all connected clients (depends on `websockets.md` `task.drag_*` events).
- Optimistic UI on drop with server reconciliation.
- Keyboard a11y (`@dnd-kit` defaults).
- Mobile: columns stack vertically; touch drag works via `@dnd-kit` `TouchSensor`.
- **UI Consistency Contract** (see §6) — all colors, typography, spacing, shapes, motion match existing modules.

**Out of scope**
- Column reordering, custom columns, swimlanes, WIP limits, labels, priorities.
- Persisted card ordering within a column (would need `tasks.order_index INT`). Cards within a column render in the same order returned by the API (currently `ORDER BY created_at DESC`).
- Dedicated `/board` route. (User chose toggle-on-`/tasks`.)
- Replacing the list view. List view stays as the default.
- Native mobile gestures beyond what `@dnd-kit` provides out of the box.

## API Contract

**No new REST endpoints.**

- Status persistence reuses `PATCH /tasks/{task_id}/status` body `{ "status": "PENDING|IN_PROGRESS|COMPLETED" }` — already wired in `controllers/task_controller.py:59-68` and `services/task_service.py:62-73`.
- Initial fetch reuses `GET /tasks/filtered` (per `pagination-filtering-sorting.md`) with `size=200&view=board` (board view does not paginate visually; it fetches up to 200 tasks and surfaces a "showing N of M" note if there are more).
- Live drag broadcasting rides the WebSocket channel defined in `websockets.md`. Events used by the board:
  - **Outbound**: `task.drag_start`, `task.drag_move` (throttled 30 Hz), `task.drag_end`.
  - **Inbound**: all of the above from other actors, plus `task.drag_rejected` (lock conflict), and the regular lifecycle events `task.created` / `task.updated` / `task.status_changed` / `task.deleted`.

## Database Changes

None.

(For reference: persisted card ordering — out of scope — would require a `tasks.order_index INT` column and a `PATCH /tasks/reorder` endpoint. The board's component contract leaves room for this without rewrites.)

## Files to Change

### Frontend — new files

- `src/pages/KanbanBoard.jsx` — top-level board page.
  - Reads filters / view from URL via `useSearchParams`.
  - Fetches via `taskAPI.getTasks({ ...filters, size: 200, view: 'board' })`.
  - Renders header (`<TaskFilters>` + `<ViewToggle>` + create button) and three `<KanbanColumn>`s inside a single `<DndContext>` (`@dnd-kit/core`).
  - Maintains local state `{ tasks: Task[], remoteDrags: Record<task_id, { user, cursor, over_status }> }`.
  - Subscribes to `useTaskSocket` callbacks; on `onStatusChanged`, replaces the task by id (also resolves any optimistic state). On `onDragStart/Move/End`, updates `remoteDrags`. On `onDragRejected`, snaps the locally-held drag back and toasts.
  - `onDragEnd` (local): optimistic status update + `taskAPI.updateTaskStatus(id, newStatus)` + `socket.send('task.drag_end', { task_id, cancelled: false })`. On API failure, revert and toast.

- `src/components/kanban/KanbanColumn.jsx` — single status column.
  - Props: `status`, `label`, `tasks`, `remoteDrags`.
  - Header: status label (color from `TASK_STATUS_COLORS`), count pill (`bg-{color}-100 text-{color}-800`).
  - Body: `<SortableContext strategy={verticalListSortingStrategy}>` wrapping `<KanbanCard>`s.
  - Empty state: same `Inbox` icon pattern as `TaskList.jsx:19-39`, message tailored per column ("No tasks to start" / "Nothing in progress" / "No completed tasks yet").

- `src/components/kanban/KanbanCard.jsx` — draggable card.
  - Uses `useSortable({ id: task.id.toString() })`.
  - Inner layout reuses `TaskCard.jsx`'s body (title, description, assignee, due date, status badge) — wraps, does not fork.
  - Drag handle: `<GripVertical>` icon top-right, `cursor-grab` / `cursor-grabbing` on active.
  - Local drag state: `transform` from `dnd-kit` + `whileDrag={{ scale: 1.04, rotate: 1 }}` framer-motion.
  - **Remote drag overlay** (when `remoteDrags[task.id]` exists and the actor isn't the current user):
    - `opacity-50 pointer-events-none ring-2 ring-indigo-400 ring-dashed`.
    - Top-right pill: 6×6 gradient avatar (`from-indigo-500 to-purple-600`) with `getInitials(user.username)` + "moving" label.
  - On pickup: emits `socket.send('task.drag_start', { task_id, from_status })`. On drag move (via `useDragBroadcast`): emits `drag_move`. On drop: emits `drag_end`.

- `src/components/kanban/DragGhost.jsx` — floating ghost card for remote drags.
  - One ghost per active remote drag, positioned absolutely from `remoteDrags[id].cursor.{x,y}`.
  - Styled like `KanbanCard` but `opacity-40`, non-interactive, and animated with `transition={{ duration: 0.08, ease: 'linear' }}` to smooth jitter.

- `src/components/kanban/ViewToggle.jsx` — segmented control "List | Board" for the `/tasks` header.
  - Rounded-pill toggle; active state uses Navbar's active-link style (`bg-indigo-50 text-indigo-600 font-medium`).
  - Icons: `<List>` and `<LayoutGrid>` from lucide-react.

- `src/hooks/useDragBroadcast.js` — throttle helper described in `websockets.md`.

### Frontend — changed files

- `src/pages/Tasks.jsx`:
  - Read `view = searchParams.get('view') ?? 'list'`.
  - Add `<ViewToggle>` next to the existing "Create Task" button in the header (`Tasks.jsx:123-140`).
  - Render `<TaskList>` when `view === 'list'` (current behavior), `<KanbanBoard>` when `view === 'board'`.
  - Filters/page state are shared and synced to URL.

- `src/utils/constants.js`:
  - Add `KANBAN_COLUMN_ORDER = [TASK_STATUS.PENDING, TASK_STATUS.IN_PROGRESS, TASK_STATUS.COMPLETED]`.
  - Add `KANBAN_COLUMN_LABEL = { [TASK_STATUS.PENDING]: 'To Do', [TASK_STATUS.IN_PROGRESS]: 'In Progress', [TASK_STATUS.COMPLETED]: 'Done' }`.

- `package.json` — add `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` to dependencies.

### Backend — changed files

- None directly — the heavy WS work lives in `websockets.md`. This spec only consumes that channel. The Kanban work cannot land until `websockets.md` is implemented.

## UI Consistency Contract

Every choice below was verified against the existing exploration of `Dashboard.jsx`, `Tasks.jsx`, `Login.jsx`, `Navbar.jsx`, `TaskCard.jsx`, `StatsCard.jsx`, and `index.css`. Deviating from these tokens means the board will look like it belongs to a different app — don't.

### Color tokens

- **Primary action**: `bg-primary-600 hover:bg-primary-700` (defined in `src/index.css` `@theme`). Used on the "Create Task" button.
- **Brand gradients**: `from-indigo-500 to-purple-600` for logos, avatars, primary stats cards, and the remote-drag user pill on cards.
- **Status colors** (mirror `TASK_STATUS_COLORS` in `src/utils/constants.js`; reuse exactly, do not redefine):

  | Status | Column header bg | Header text | Count pill | Card border accent (subtle) |
  |---|---|---|---|---|
  | `PENDING` | `bg-amber-50` | `text-amber-700` | `bg-amber-100 text-amber-800` | `border-l-4 border-amber-400` |
  | `IN_PROGRESS` | `bg-blue-50` | `text-blue-700` | `bg-blue-100 text-blue-800` | `border-l-4 border-blue-400` |
  | `COMPLETED` | `bg-emerald-50` | `text-emerald-700` | `bg-emerald-100 text-emerald-800` | `border-l-4 border-emerald-400` |

### Page chrome (identical to existing pages)

- Wrapper: `<Navbar />` then
  ```jsx
  <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  ```
- Page heading (matches `Tasks.jsx:124-127` and `Dashboard.jsx`):
  ```jsx
  <h1 className="text-3xl font-bold text-gray-900 mb-2">All Tasks</h1>
  <p className="text-gray-600">Drag cards between columns to update status</p>
  ```
- Filters panel: reuse `<TaskFilters>` unchanged above the board.

### Typography

- Font: `'DM Sans', system-ui, -apple-system, sans-serif` (already set in `index.css`).
- Page title: `text-3xl font-bold text-gray-900`.
- Column header label: `text-lg font-semibold` in the status color.
- Card title: `text-lg font-semibold text-gray-900` (matches `TaskCard.jsx`).
- Card description: `text-gray-600 text-sm line-clamp-2`.
- Metadata: `text-sm text-gray-600`.
- Error/status text: `text-sm text-red-600` (matches `Input.jsx`).

### Spacing & shape

- Outer board grid: `grid grid-cols-1 md:grid-cols-3 gap-6`.
- Column container: `bg-white/70 backdrop-blur-sm rounded-xl p-4 min-h-[60vh] space-y-3`.
  - Glass effect echoes Navbar's `bg-white/80 backdrop-blur-lg`.
- Cards: `bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-all duration-200` — i.e., the existing `.card` utility from `index.css`. Do not invent a new shadow scale.
- Inter-card vertical gap inside a column: `space-y-3`.
- Section spacing between header / filters / board: `mb-6` / `mb-8` (matches `Tasks.jsx`).

### Animation (framer-motion — no new motion patterns)

- Card entry: `initial={{ opacity: 0, y: 20 }}` → `animate={{ opacity: 1, y: 0 }}` with `transition={{ delay: index * 0.05 }}` — staggered, same pattern as `TaskList.jsx:38-44` but tighter for the denser column layout.
- Card hover lift: `whileHover={{ y: -4 }}` (existing `TaskCard` behavior).
- Drag pickup feedback: `whileDrag={{ scale: 1.04, rotate: 1 }}` — subtle, matches the existing tap/hover scale vocabulary in `Button.jsx`.
- Remote drag ghost: `transition={{ duration: 0.08, ease: 'linear' }}` — fast enough to feel live, slow enough to dampen WS jitter.
- Column drop highlight: `bg-{color}-50 ring-2 ring-{color}-300` while a card is being dragged over the column.

### Icons (lucide-react — already a dependency)

- Drag handle: `<GripVertical>` (new usage).
- Empty column: `<Inbox>` (reused from `TaskList.jsx:24`).
- View toggle: `<LayoutGrid>` for Board, `<List>` for List.
- Card metadata: `<User>`, `<Calendar>` (already used in `TaskCard.jsx`).

### Avatars

- "Being dragged by X" pill: 6×6 (`w-6 h-6`) rounded-md, gradient `from-indigo-500 to-purple-600`, `text-white text-xs font-semibold`, two-letter initials from `getInitials(username)` (existing helper in `src/utils/helpers.js`).

### Loading & empty states

- Initial board load: full-grid skeleton — 3 columns each with 3 `bg-gray-200 rounded-xl h-32 animate-pulse` placeholders. Echoes `TaskList.jsx:9-17`.
- Empty column: large gray `Inbox` icon (`w-12 h-12 text-gray-300`) + `text-sm text-gray-500` helper message. Mirrors the "No tasks found" block.
- Error: red toast via `react-hot-toast` (already configured globally in `App.jsx`).

### Toggle visual

`<ViewToggle>` styled as a pill container with two buttons. Active button: `bg-indigo-50 text-indigo-600 font-medium` (Navbar active-link style). Inactive: `text-gray-600 hover:bg-gray-50`. Wrapper: `inline-flex items-center bg-white border border-gray-200 rounded-lg p-1`.

## Acceptance Criteria

### Functional
- [ ] Visiting `/tasks` shows the list view by default.
- [ ] Clicking the "Board" toggle navigates to `/tasks?view=board` and renders three columns with correct counts and data.
- [ ] Filters from `<TaskFilters>` apply to the board — only matching cards appear in each column.
- [ ] Dragging a card from `PENDING` to `IN_PROGRESS` calls `PATCH /tasks/{id}/status` exactly once.
- [ ] On API failure, the card snaps back to its original column and an error toast appears.
- [ ] Cards inside a column can be reordered visually (server order is not persisted; reverts on next refresh — this is intentional and documented).
- [ ] Empty columns render the empty state per status.
- [ ] Mobile width (<768 px): columns stack vertically; touch drag works.
- [ ] Keyboard a11y: Tab to a card, Space to pick up, Arrow keys to move, Space to drop.

### Real-time
- [ ] User A drags a card; within 100 ms user B in another browser sees the card flagged with a "being moved by A" pill.
- [ ] As A moves the cursor, B sees a ghost following A's position at ≥ 15 fps perceived rate.
- [ ] If two users simultaneously grab the same card, the loser receives `task.drag_rejected` and the card stays under the winner's control.
- [ ] A user closes their tab mid-drag; within 5 s every other client clears the lock.
- [ ] On A's drop into `IN_PROGRESS`, B sees the card snap to the `IN_PROGRESS` column via `task.status_changed` and the "being moved" overlay disappears.

### UI consistency (manual visual review)
- [ ] Page wrapper, max width, padding, and background gradient match `Dashboard.jsx` and `Tasks.jsx`.
- [ ] Font family, heading sizes, weights match existing pages.
- [ ] Card shadow, radius, hover lift indistinguishable from a `TaskCard` in list view.
- [ ] Status colors match `TASK_STATUS_COLORS` exactly — no new amber/blue/emerald shades.
- [ ] Toggle pill uses the same active-state style as the Navbar links.
- [ ] No new font weights, color hex codes, or shadow scales introduced.

## Notes / Open Questions

- **Persisted card order**: deferred. If/when added, a `tasks.order_index INT` column plus `PATCH /tasks/reorder` will be needed. `KanbanColumn` already iterates a `tasks` prop in array order, so swapping to a sorted list is a one-line change.
- **`size=200` fetch ceiling**: on boards with >200 tasks, the view shows a "Showing 200 of N" note. Real fix is virtualization (e.g., `react-virtual`) — deferred until a real user hits the wall.
- **Drag lock race conditions**: handled by server-side `active_drags` map in `websockets.md`. Spec there owns the rules; this spec just relies on them.
- **Multi-tab actor**: the actor's own other tabs receive `drag_move` events (so a user with two tabs open sees their cursor mirror in tab 2). This is deliberate; do not filter it out client-side.
- **Coordination**: this feature hard-depends on `websockets.md` (lifecycle + `drag_*` events) and benefits from `pagination-filtering-sorting.md` (the new `/tasks/filtered` endpoint with `size=200`). Implement in the order: websockets → pagination → kanban.
- **Accessibility caveat**: the live ghost preview is purely visual. Screen-reader users get `aria-live` announcements for status changes ("Task 'X' moved to In Progress") on commit, not during drag. That's a reasonable compromise; flag if users report otherwise.
- **Visual regression**: a Playwright screenshot test against `/tasks?view=board` should land alongside this feature (see `testing.md`). Without it, the "UI Consistency Contract" criteria are manual-review only.
