from typing import Optional
from queries.task_queries import  CREATE_TASK_QUERY,GET_ALL_TASKS_ADMIN_QUERY, GET_TASKS_BASE, GET_TASKS_FOR_USER_QUERY, UPDATE_TASK_QUERY, UPDATE_TASK_STATUS_QUERY, GET_TASKS_PAGINATED, COUNT_TASKS, DELETE_TASK_QUERY
from psycopg2.extensions import connection, cursor
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException, status

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
    def get_tasks_paginated_filtered(conn, limit: int, offset: int, status: str | None = None):
        params = []
        where_clause = ""

        # Add status filter if provided
        if status:
            where_clause = " WHERE status = %s"
            params.append(status)

        # Data query
        data_query = f"""
            SELECT *
            FROM tasks
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """

        # Count query
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM tasks
            {where_clause}
        """

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Fetch paginated tasks
            cur.execute(data_query, params + [limit, offset])
            tasks = cur.fetchall()

            # Fetch total count
            cur.execute(count_query, params)
            row = cur.fetchone()
            total = int(row["total"]) if row else 0

        return tasks,total
    
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

