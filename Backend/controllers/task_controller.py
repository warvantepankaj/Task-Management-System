from fastapi import APIRouter, Depends, Query, HTTPException, status
from schemas.task import  TaskStatusUpdate, TaskStatus, TaskUpdateAdmin,TaskCreate
from services.task_service import TaskService
from database.session import get_db
from utils.security import get_current_user
from utils.dependencies import admin_required,user_required

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/create_task")
def create_task(
    task: TaskCreate,
    conn=Depends(get_db),
    admin: dict = Depends(admin_required),  
):
    if not task.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="assigned_to is required for admin"
        )

    return TaskService.create_task(
        conn,
        task,
        admin_id=admin["id"]  
    )



@router.get("/admin", summary="Admin - get all tasks")
def get_all_tasks_admin(
    admin: dict = Depends(admin_required),
    conn=Depends(get_db)
):
    return TaskService.get_all_tasks_admin(conn)


@router.get("/user/me", summary="User - get my tasks")
def get_my_tasks(
    user: dict = Depends(user_required),
    conn=Depends(get_db)
):
    return TaskService.get_tasks_for_user(conn, user["id"])


@router.put("/{task_id}/admin", summary="Admin updates task")
def update_task_admin(
    task_id: int,
    payload: TaskUpdateAdmin,
    admin: dict = Depends(admin_required),
    conn=Depends(get_db)
):
    return TaskService.admin_update_task(
        conn, task_id, admin["id"], payload
    )


@router.patch("/{task_id}/status", summary="User updates task status")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    user: dict = Depends(user_required),
    conn=Depends(get_db)
):
    return TaskService.user_update_task_status(
        conn, task_id, user["id"], payload.status
    )



@router.get("/filtered", summary="Get tasks with pagination & filters")
def get_tasks_filtered(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: TaskStatus | None = Query(None),
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_db)
):
    
    user_id = None
    if current_user["role"] == "user":
        user_id = current_user["id"]

    return TaskService.get_tasks_paginated_filtered(
        conn=conn,
        page=page,
        size=size,
        status=status.value if status else None,
        user_id=user_id
    )


@router.delete("/{task_id}/delete", summary="Admin deletes a task")
def delete_task(
    task_id: int,
    admin: dict = Depends(admin_required),
    conn=Depends(get_db)
):
    TaskService.delete_task(conn, task_id)
    return {"message": "Task deleted successfully"}