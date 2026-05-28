from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from queries.user_queries import (
    FETCH_USER_BY_EMAIL_QUERY,
    FETCH_USER_BY_ID_QUERY,
    INSERT_USER_QUERY,
    SELECT_ALL_USERS_QUERY,
    SELECT_ALL_USERS_PAGINATED_QUERY,
    COUNT_USERS_QUERY,
    GET_USERS_FILTERED_BASE,
    COUNT_USERS_FILTERED_BASE,
)

ALLOWED_USER_SORT = {"created_at", "username", "email", "role"}
ALLOWED_SORT_ORDER = {"asc", "desc"}


def create_user(conn, username, email, password_hash, role):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(INSERT_USER_QUERY, (username, email, password_hash, role))
            user = cur.fetchone()
            conn.commit()
            return user
    except Exception as e:
        conn.rollback()
        raise e


def get_user_by_email(conn, email):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(FETCH_USER_BY_EMAIL_QUERY, (email,))
        return cur.fetchone()


def get_user_by_id(conn, id):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(FETCH_USER_BY_ID_QUERY, (id,))
        return cur.fetchone()


def get_all_users(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SELECT_ALL_USERS_QUERY)
        return cur.fetchall()


def get_all_users_paginated(
    conn,
    page: int,
    page_size: int,
    *,
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    """
    Filtered + sorted + paginated user listing. Same defense-in-depth as
    tasks: whitelist sort_by / sort_order, build WHERE with %s placeholders.
    """
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be >= 1")
    if sort_by not in ALLOWED_USER_SORT:
        raise HTTPException(status_code=400, detail="invalid_sort_by")
    if sort_order not in ALLOWED_SORT_ORDER:
        raise HTTPException(status_code=400, detail="invalid_sort_order")

    offset = (page - 1) * page_size
    conditions: list[str] = []
    params: list = []

    if role is not None:
        conditions.append("role = %s")
        params.append(role)

    if is_active is not None:
        conditions.append("is_active = %s")
        params.append(is_active)

    if search:
        conditions.append("(username ILIKE %s OR email ILIKE %s)")
        pattern = f"%{search}%"
        params.append(pattern)
        params.append(pattern)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order_clause = f"{sort_by} {sort_order.upper()}"

    data_query = GET_USERS_FILTERED_BASE.format(
        where_clause=where_clause, order_clause=order_clause
    )
    count_query = COUNT_USERS_FILTERED_BASE.format(where_clause=where_clause)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(data_query, params + [page_size, offset])
            users = cur.fetchall()

            cur.execute(count_query, params)
            row = cur.fetchone()
            total = int(row["total"]) if row else 0
    except HTTPException:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to fetch users: {str(e)}")

    return users, total
