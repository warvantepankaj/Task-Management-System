import datetime
from psycopg2.extensions import connection
from fastapi import HTTPException,status
from dao.task_dao import TaskDAO
from constants.task_constants import VALID_STATUSES
from schemas.task import TaskCreate, TaskUpdateAdmin, TaskStatusUpdate

class TaskService:

    @staticmethod
    def create_task(conn, task: TaskCreate, admin_id: int):
        task_data = (
            task.title,
            task.description,
            task.status.value,  # convert enum to string
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
        
        return created_task

    
    
    @staticmethod
    def get_all_tasks_admin(conn):
        return TaskDAO.get_all_tasks_admin(conn)

    @staticmethod
    def get_tasks_for_user(conn, user_id: int):
        return TaskDAO.get_tasks_for_user(conn, user_id)
    
    @staticmethod
    def admin_update_task(conn, task_id: int, admin_id: int, payload):
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
        return task


    @staticmethod
    def user_update_task_status(conn, task_id: int, user_id: int, status: str):

        updated_task = TaskDAO.update_task_status(conn, task_id, user_id, status)

        if not updated_task:
            raise HTTPException(
                status_code=404,
                detail="Task not found or not assigned to user"
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
        """
        Build a PaginatedResponse-shaped dict.

        Non-admin callers are pinned to their own `user_id`; any `assigned_to`
        they pass on the query string is dropped — defense in depth on top of
        the controller forcing the same.
        """
        if page < 1 or size < 1:
            raise ValueError("page and size must be >= 1")

        # For non-admins, force scoping to their own tasks.
        if not is_admin:
            assigned_to = None  # ignored anyway, but make the intent obvious
            scoped_user_id = user_id
        else:
            scoped_user_id = None  # admins can filter by `assigned_to` or none

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
    def delete_task(conn, task_id: int):
        TaskDAO.delete_task(conn, task_id)
        conn.commit()