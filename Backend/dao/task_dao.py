from datetime import date, datetime, time, timezone
from typing import Optional

from psycopg2.extensions import connection, cursor
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException, status

from queries.task_queries import (
    CREATE_TASK_QUERY,
    GET_ALL_TASKS_ADMIN_QUERY,
    GET_TASKS_BASE,
    GET_TASKS_FOR_USER_QUERY,
    UPDATE_TASK_QUERY,
    UPDATE_TASK_STATUS_QUERY,
    GET_TASKS_PAGINATED,
    COUNT_TASKS,
    DELETE_TASK_QUERY,
    GET_TASKS_FILTERED_BASE,
    COUNT_TASKS_FILTERED_BASE,
)

# Defense-in-depth: even though the Pydantic Literal on the controller side
# already rejects unknown sort_by values, the DAO refuses to interpolate any
# column name that isn't on this list.
ALLOWED_TASK_SORT = {"created_at", "due_date", "title", "status"}
ALLOWED_SORT_ORDER = {"asc", "desc"}

class TaskDAO:

    @staticmethod
    def create_task(conn: connection, data: tuple):
        try:
            with conn.cursor() as cur:
                cur.execute(CREATE_TASK_QUERY, data)
                result = cur.fetchone()
                if result:
                    return result[0]
                raise Exception("Task creation failed - no ID returned")
        except Exception as e:
            conn.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )

    @staticmethod
    def get_all_tasks_admin(conn: connection):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(GET_ALL_TASKS_ADMIN_QUERY)
            return cur.fetchall()

    @staticmethod
    def get_tasks_for_user(conn: connection, user_id: int):
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(GET_TASKS_FOR_USER_QUERY, (user_id,))
            return cur.fetchall()
        
    @staticmethod
    def update_task_by_admin(conn, task_id: int, updates: dict):
        if not updates:
            return None

        ALLOWED_FIELDS = {
            "title",
            "description",
            "status",
            "due_date",
            "assigned_to"
        }

        updates = {k: v for k, v in updates.items() if k in ALLOWED_FIELDS}

        if not updates:
            return None

        set_clause = ", ".join(f"{key} = %s" for key in updates.keys())
        values = list(updates.values()) + [task_id]

        query = UPDATE_TASK_QUERY.format(set_clause=set_clause)

        with conn.cursor() as cur:
            cur.execute(query, values)
            return cur.fetchone()


    @staticmethod
    def update_task_status(conn, task_id: int, user_id: int, status: str):
        query = UPDATE_TASK_STATUS_QUERY
        with conn.cursor() as cur:
            cur.execute(query, (status, task_id, user_id))
            conn.commit()
            return cur.fetchone()
        
    @staticmethod
    def get_tasks_paginated_filtered(
        conn,
        limit: int,
        offset: int,
        *,
        user_id: int | None = None,
        status: str | None = None,
        assigned_to: int | None = None,
        due_date_from: date | None = None,
        due_date_to: date | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ):
        """
        Build the WHERE clause incrementally with parameter binding (%s) so
        nothing from the request ever lands directly in the SQL string. The
        sort column / direction are mapped through whitelists.
        """
        if sort_by not in ALLOWED_TASK_SORT:
            raise HTTPException(status_code=400, detail="invalid_sort_by")
        if sort_order not in ALLOWED_SORT_ORDER:
            raise HTTPException(status_code=400, detail="invalid_sort_order")

        conditions: list[str] = []
        params: list = []

        if user_id is not None:
            conditions.append("assigned_to = %s")
            params.append(user_id)
        elif assigned_to is not None:
            # Admin-only filter; service forces user_id for non-admins so this
            # branch is unreachable for them.
            conditions.append("assigned_to = %s")
            params.append(assigned_to)

        if status:
            conditions.append("status = %s")
            params.append(status)

        if due_date_from is not None:
            conditions.append("due_date >= %s")
            params.append(due_date_from)

        if due_date_to is not None:
            # Inclusive of the entire end day. due_date is a DATE column, so
            # using "<=" on the date is already inclusive of the whole day.
            conditions.append("due_date <= %s")
            params.append(due_date_to)

        if search:
            conditions.append("(title ILIKE %s OR description ILIKE %s)")
            pattern = f"%{search}%"
            params.append(pattern)
            params.append(pattern)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        order_clause = f"{sort_by} {sort_order.upper()}"

        data_query = GET_TASKS_FILTERED_BASE.format(
            where_clause=where_clause, order_clause=order_clause
        )
        count_query = COUNT_TASKS_FILTERED_BASE.format(where_clause=where_clause)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(data_query, params + [limit, offset])
            tasks = cur.fetchall()

            cur.execute(count_query, params)
            row = cur.fetchone()
            total = int(row["total"]) if row else 0

        return tasks, total
    
    @staticmethod
    def delete_task(conn, task_id: int):
        with conn.cursor() as cur:
            cur.execute(DELETE_TASK_QUERY, (task_id,))


    @staticmethod
    def get_task_by_id(conn, task_id: int):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, description, status, due_date, assigned_to, assigned_by, created_at
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "status": row[3],
                    "due_date": row[4],
                    "assigned_to": row[5],
                    "assigned_by": row[6],
                    "created_at": row[7]
                }
            return None

