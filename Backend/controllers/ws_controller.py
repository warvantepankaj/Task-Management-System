"""
WebSocket controller for /ws/tasks.

Validates the JWT from the query string, registers the socket with the
ConnectionManager, and dispatches inbound drag events to it. Closes with custom
code 4401 on auth failure so the client knows to refresh + reconnect.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError

from core.config import JWT_SECRET
from core.ws_manager import ws_manager

logger = logging.getLogger(__name__)

ws_router = APIRouter()

ALGORITHM = "HS256"
WS_UNAUTHORIZED_CLOSE_CODE = 4401


def _decode_token(token: str) -> Optional[dict]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("token_type") != "access":
        return None
    user_id = payload.get("user_id")
    role = payload.get("role")
    if not user_id or not role:
        return None
    return {"user_id": int(user_id), "role": role}


@ws_router.websocket("/ws/tasks")
async def tasks_ws(websocket: WebSocket, token: str = Query(default="")):
    claims = _decode_token(token)
    if claims is None:
        await websocket.close(code=WS_UNAUTHORIZED_CLOSE_CODE)
        return

    user_id = claims["user_id"]
    role = claims["role"]
    await ws_manager.connect(websocket, user_id=user_id, role=role)

    try:
        while True:
            msg = await websocket.receive_json()
            if not isinstance(msg, dict):
                continue

            # Optional ping/pong for app-layer health checks.
            if msg.get("type") == "ping":
                try:
                    await websocket.send_json({"type": "pong"})
                except Exception:
                    break
                continue

            event = msg.get("event")
            if not isinstance(event, str):
                continue
            if event.startswith("task.drag_"):
                await ws_manager.handle_drag_event(
                    websocket,
                    user_id=user_id,
                    event=event,
                    data=msg.get("data") or {},
                )
            # Any other inbound events are ignored per the spec.
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws handler errored; closing")
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        await ws_manager.disconnect(websocket, user_id=user_id)
