"""
In-process WebSocket connection manager for the /ws/tasks channel.

Holds per-user-id socket sets and per-task-id drag locks. Single-uvicorn-worker
deployment is assumed; scaling beyond one worker would require Redis pub/sub.
"""
import asyncio
import datetime as _dt
import json
import logging
from typing import Iterable, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _json_default(o):
    if isinstance(o, (_dt.datetime, _dt.date)):
        return o.isoformat()
    return str(o)


class ConnectionManager:
    """Tracks live WebSocket connections and broadcasts task events.

    - `connections`: per-user-id set of sockets (user can have multiple tabs).
    - `admin_user_ids`: cache of currently-connected admin user ids (used to
      build broadcast recipient sets in O(1)).
    - `active_drags`: per-task-id lock describing who's currently dragging.
    """

    STALE_DRAG_SECONDS = 5
    REAPER_INTERVAL_SECONDS = 1
    SEND_TIMEOUT_SECONDS = 5

    def __init__(self) -> None:
        self.connections: dict[int, set[WebSocket]] = {}
        self.admin_user_ids: set[int] = set()
        # task_id -> { user_id, socket_id, started_at, last_seen }
        self.active_drags: dict[int, dict] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------ lifecycle

    async def connect(self, ws: WebSocket, user_id: int, role: str) -> None:
        await ws.accept()
        async with self._lock:
            self.connections.setdefault(user_id, set()).add(ws)
            if role == "admin":
                self.admin_user_ids.add(user_id)
        # Lazily start the stale-lock reaper.
        self._ensure_reaper_running()

    async def disconnect(self, ws: WebSocket, user_id: int) -> None:
        """Remove the socket and release any drag locks owned by it."""
        released: list[tuple[int, dict]] = []
        async with self._lock:
            bucket = self.connections.get(user_id)
            if bucket and ws in bucket:
                bucket.discard(ws)
                if not bucket:
                    self.connections.pop(user_id, None)
                    # User has no more tabs; drop admin cache entry.
                    self.admin_user_ids.discard(user_id)
            # Release any drag locks held by this socket.
            for task_id, lock in list(self.active_drags.items()):
                if lock.get("socket_id") == id(ws):
                    released.append((task_id, lock))
                    self.active_drags.pop(task_id, None)

        # Outside the lock: broadcast synthetic drag_end for released locks.
        for task_id, lock in released:
            await self._broadcast_all(
                {
                    "event": "task.drag_end",
                    "data": {"task_id": task_id, "cancelled": True},
                    "actor_id": lock.get("user_id"),
                    "ts": _now_iso(),
                },
            )

    def _ensure_reaper_running(self) -> None:
        if self._reaper_task is None or self._reaper_task.done():
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            self._reaper_task = loop.create_task(self._stale_drag_reaper())

    async def _stale_drag_reaper(self) -> None:
        """Every second, expire drag locks older than STALE_DRAG_SECONDS."""
        while True:
            try:
                await asyncio.sleep(self.REAPER_INTERVAL_SECONDS)
                now = _dt.datetime.utcnow()
                expired: list[tuple[int, dict]] = []
                async with self._lock:
                    for task_id, lock in list(self.active_drags.items()):
                        started_at = lock.get("last_seen") or lock.get("started_at")
                        if isinstance(started_at, _dt.datetime):
                            age = (now - started_at).total_seconds()
                            if age > self.STALE_DRAG_SECONDS:
                                expired.append((task_id, lock))
                                self.active_drags.pop(task_id, None)
                for task_id, lock in expired:
                    await self._broadcast_all(
                        {
                            "event": "task.drag_end",
                            "data": {"task_id": task_id, "cancelled": True},
                            "actor_id": lock.get("user_id"),
                            "ts": _now_iso(),
                        },
                    )
            except asyncio.CancelledError:
                break
            except Exception:  # pragma: no cover - defensive
                logger.exception("stale-drag reaper failed")

    # ------------------------------------------------------------------ sending

    async def _send(self, ws: WebSocket, payload: dict) -> bool:
        """Send JSON to a single socket with a timeout. Returns False on failure."""
        try:
            text = json.dumps(payload, default=_json_default)
            await asyncio.wait_for(ws.send_text(text), timeout=self.SEND_TIMEOUT_SECONDS)
            return True
        except Exception:
            logger.warning("ws send failed; closing socket", exc_info=False)
            try:
                await ws.close()
            except Exception:
                pass
            return False

    async def broadcast_to_users(
        self,
        user_ids: Iterable[int],
        payload: dict,
        skip_socket: Optional[WebSocket] = None,
    ) -> None:
        """Fan out a payload to every socket of every user in `user_ids`."""
        async with self._lock:
            targets: list[WebSocket] = []
            for uid in set(user_ids):
                for ws in self.connections.get(uid, set()):
                    if ws is skip_socket:
                        continue
                    targets.append(ws)
        # Send outside the lock to avoid blocking new connects/disconnects on slow peers.
        if not targets:
            return
        await asyncio.gather(*(self._send(t, payload) for t in targets), return_exceptions=True)

    async def _broadcast_all(
        self, payload: dict, skip_socket: Optional[WebSocket] = None,
    ) -> None:
        async with self._lock:
            user_ids = list(self.connections.keys())
        await self.broadcast_to_users(user_ids, payload, skip_socket=skip_socket)

    # ------------------------------------------------------------------ task lifecycle

    async def broadcast_task_event(self, event: str, task: dict, actor_id: int) -> None:
        """Broadcast a lifecycle event (created/updated/status_changed/deleted)."""
        # Recipient set: all admins + the assigned_to user (if any). Actor's
        # own tabs DO receive the event (multi-tab consistency).
        recipients: set[int] = set(self.admin_user_ids)
        assigned_to = task.get("assigned_to") if isinstance(task, dict) else None
        if assigned_to:
            recipients.add(int(assigned_to))
        # Always include the actor so their other tabs stay in sync.
        recipients.add(int(actor_id))

        payload = {
            "event": event,
            "task": task,
            "actor_id": actor_id,
            "ts": _now_iso(),
        }
        await self.broadcast_to_users(recipients, payload)

    # ------------------------------------------------------------------ drag relay

    async def handle_drag_event(
        self,
        socket: WebSocket,
        user_id: int,
        event: str,
        data: dict,
    ) -> None:
        """Relay task.drag_start / drag_move / drag_end across all peers."""
        if not isinstance(data, dict):
            return
        task_id = data.get("task_id")
        if not isinstance(task_id, int):
            return

        now = _dt.datetime.utcnow()
        ts = _now_iso()

        if event == "task.drag_start":
            async with self._lock:
                existing = self.active_drags.get(task_id)
                stale = False
                if existing:
                    started = existing.get("last_seen") or existing.get("started_at")
                    if isinstance(started, _dt.datetime):
                        stale = (now - started).total_seconds() > self.STALE_DRAG_SECONDS
                if existing and not stale and existing.get("socket_id") != id(socket):
                    # Conflict — reply 1:1 with drag_rejected.
                    reject_payload = {
                        "event": "task.drag_rejected",
                        "data": {"task_id": task_id, "reason": "locked_by_other_user"},
                        "actor_id": existing.get("user_id"),
                        "ts": ts,
                    }
                    # Send outside the lock.
                else:
                    self.active_drags[task_id] = {
                        "user_id": user_id,
                        "socket_id": id(socket),
                        "started_at": now,
                        "last_seen": now,
                    }
                    reject_payload = None

            if reject_payload is not None:
                await self._send(socket, reject_payload)
                return

            await self._broadcast_all(
                {
                    "event": "task.drag_start",
                    "data": data,
                    "actor_id": user_id,
                    "ts": ts,
                }
            )
            return

        if event == "task.drag_move":
            async with self._lock:
                lock = self.active_drags.get(task_id)
                if not lock or lock.get("socket_id") != id(socket):
                    # Either no lock or someone else owns it: ignore.
                    return
                lock["last_seen"] = now

            await self._broadcast_all(
                {
                    "event": "task.drag_move",
                    "data": data,
                    "actor_id": user_id,
                    "ts": ts,
                },
                skip_socket=socket,
            )
            return

        if event == "task.drag_end":
            async with self._lock:
                lock = self.active_drags.get(task_id)
                if lock and lock.get("socket_id") == id(socket):
                    self.active_drags.pop(task_id, None)

            await self._broadcast_all(
                {
                    "event": "task.drag_end",
                    "data": data,
                    "actor_id": user_id,
                    "ts": ts,
                }
            )
            return

        # Unknown drag event — ignore.


# Module-level singleton used everywhere.
ws_manager = ConnectionManager()
