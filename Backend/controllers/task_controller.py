from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas.task import TaskStatusUpdate, TaskStatus, TaskUpdateAdmin, TaskCreate
from services.task_service import TaskService
from database.session import get_db
from utils.security import get_current_user
from utils.dependencies import admin_required, user_required

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/create_task")
async def create_task(
    task: TaskCreate,
    conn=Depends(get_db),
    admin: dict = Depends(admin_required),
):
    if not task.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="assigned_to is required for admin",
        )

    return await TaskService.create_task(conn, task, admin_id=admin["id"])


@router.get("/admin", summary="Admin - get all tasks (legacy unpaginated)")
def get_all_tasks_admin(
    admin: dict = Depends(admin_required),
    conn=Depends(get_db),
):
    return TaskService.get_all_tasks_admin(conn)


@router.get("/user/me", summary="User - get my tasks (legacy unpaginated)")
def get_my_tasks(
    user: dict = Depends(user_required),
    conn=Depends(get_db),
):
    return TaskService.get_tasks_for_user(conn, user["id"])


@router.put("/{task_id}/admin", summary="Admin updates task")
async def update_task_admin(
    task_id: int,
    payload: TaskUpdateAdmin,
    admin: dict = Depends(admin_required),
    conn=Depends(get_db),
):
    return await TaskService.admin_update_task(conn, task_id, admin["id"], payload)


@router.patch("/{task_id}/status", summary="User updates task status")
async def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    user: dict = Depends(user_required),
    conn=Depends(get_db),
):
    return await TaskService.user_update_task_status(
        conn, task_id, user["id"], payload.status
    )


@router.get("/filtered", summary="Get tasks with pagination + filters + sorting")
def get_tasks_filtered(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: TaskStatus | None = Query(None),
    assigned_to: int | None = Query(
        None, description="Admin-only; ignored for non-admins."
    ),
    due_date_from: date | None = Query(None, description="Inclusive lower bound on due_date."),
    due_date_to: date | None = Query(None, description="Inclusive upper bound on due_date."),
    search: str | None = Query(None, description="ILIKE match on title or description."),
    sort_by: Literal["created_at", "due_date", "title", "status"] = Query("created_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db),
):
    is_admin = current_user["role"] == "admin"
    user_id = None if is_admin else current_user["id"]

    return TaskService.get_tasks_paginated_filtered(
        conn=conn,
        page=page,
        size=size,
        is_admin=is_admin,
        user_id=user_id,
        status=status.value if status else None,
        assigned_to=assigned_to,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.delete("/{task_id}/delete", summary="Admin deletes a task")
async def delete_task(
    task_id: int,
    admin: dict = Depends(admin_required),
    conn=Depends(get_db),
):
    await TaskService.delete_task(conn, task_id, actor_id=admin["id"])
    return {"message": "Task deleted successfully"}
