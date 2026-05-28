import datetime
from psycopg2.extensions import connection
from fastapi import HTTPException, status
from dao.task_dao import TaskDAO
from constants.task_constants import VALID_STATUSES
from schemas.task import TaskCreate, TaskUpdateAdmin, TaskStatusUpdate
from core.ws_manager import ws_manager


def _serialize_task(task) -> dict | None:
    """Coerce a DAO row into a JSON-friendly dict for WS broadcasts.

    DAO methods return either a dict (RealDictCursor / get_task_by_id) or a raw
    psycopg2 tuple. We normalize both so callers don't have to care.
    """
    if task is None:
        return None
    if isinstance(task, dict):
        out = dict(task)
    else:
        try:
            out = {
                "id": task[0],
                "title": task[1],
                "description": task[2],
                "status": task[3],
                "due_date": task[4],
                "assigned_to": task[5],
                "assigned_by": task[6],
                "created_at": task[7] if len(task) > 7 else None,
            }
        except Exception:
            return None
    for key in ("due_date", "created_at"):
        val = out.get(key)
        if isinstance(val, (datetime.date, datetime.datetime)):
            out[key] = val.isoformat()
    return out


class TaskService:

    @staticmethod
    async def create_task(conn, task: TaskCreate, admin_id: int):
        task_data = (
            task.title,
            task.description,
            task.status.value,
            task.due_date,
            task.assigned_to,
            admin_id
        )

        try:
            task_id = TaskDAO.create_task(conn, task_data)
            created_task = TaskDAO.get_task_by_id(conn, task_id)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

        await ws_manager.broadcast_task_event(
            "task.created", _serialize_task(created_task) or {}, actor_id=admin_id
        )
        return created_task

    @staticmethod
    def get_all_tasks_admin(conn):
        return TaskDAO.get_all_tasks_admin(conn)

    @staticmethod
    def get_tasks_for_user(conn, user_id: int):
        return TaskDAO.get_tasks_for_user(conn, user_id)

    @staticmethod
    async def admin_update_task(conn, task_id: int, admin_id: int, payload):
        updates = payload.dict(exclude_unset=True)

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )

        task = TaskDAO.update_task_by_admin(conn, task_id, updates)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        conn.commit()

        serialized = _serialize_task(task)
        if serialized:
            await ws_manager.broadcast_task_event(
                "task.updated", serialized, actor_id=admin_id
            )
        return task

    @staticmethod
    async def user_update_task_status(conn, task_id: int, user_id: int, status: str):

        updated_task = TaskDAO.update_task_status(conn, task_id, user_id, status)

        if not updated_task:
            raise HTTPException(
                status_code=404,
                detail="Task not found or not assigned to user"
            )

        full = TaskDAO.get_task_by_id(conn, task_id)
        serialized = _serialize_task(full) or {"id": task_id, "assigned_to": user_id, "status": status}
        await ws_manager.broadcast_task_event(
            "task.status_changed", serialized, actor_id=user_id
        )
        return updated_task

    @staticmethod
    def get_tasks_paginated_filtered(
        conn,
        *,
        page: int,
        size: int,
        is_admin: bool,
        user_id: int | None,
        status: str | None = None,
        assigned_to: int | None = None,
        due_date_from=None,
        due_date_to=None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ):
        """Build a PaginatedResponse-shaped dict.

        Non-admin callers are pinned to their own `user_id`; any `assigned_to`
        they pass on the query string is dropped — defense in depth on top of
        the controller forcing the same.
        """
        if page < 1 or size < 1:
            raise ValueError("page and size must be >= 1")

        if not is_admin:
            assigned_to = None
            scoped_user_id = user_id
        else:
            scoped_user_id = None

        offset = (page - 1) * size

        tasks, total = TaskDAO.get_tasks_paginated_filtered(
            conn=conn,
            limit=size,
            offset=offset,
            user_id=scoped_user_id,
            status=status,
            assigned_to=assigned_to,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total + size - 1) // size if size else 0
        return {
            "page": page,
            "page_size": size,
            "total": int(total),
            "total_pages": int(total_pages),
            "data": tasks,
        }

    @staticmethod
    async def delete_task(conn, task_id: int, actor_id: int | None = None):
        existing = TaskDAO.get_task_by_id(conn, task_id)
        TaskDAO.delete_task(conn, task_id)
        conn.commit()

        payload = {"id": task_id}
        if existing and existing.get("assigned_to") is not None:
            payload["assigned_to"] = existing["assigned_to"]
        await ws_manager.broadcast_task_event(
            "task.deleted", payload, actor_id=actor_id if actor_id is not None else 0
        )
