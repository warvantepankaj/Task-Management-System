from queries.user_queries import FETCH_USER_BY_EMAIL_QUERY, FETCH_USER_BY_ID_QUERY, INSERT_USER_QUERY, SELECT_ALL_USERS_QUERY, SELECT_ALL_USERS_PAGINATED_QUERY,COUNT_USERS_QUERY
from psycopg2.extras import RealDictCursor

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
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(FETCH_USER_BY_EMAIL_QUERY, (email,))
            return cur.fetchone()
    except Exception as e:
        raise e

def get_user_by_id(conn, id):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(FETCH_USER_BY_ID_QUERY, (id,))
            return cur.fetchone()
    except Exception as e:
        raise e

def get_all_users(conn):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(SELECT_ALL_USERS_QUERY)
            return cur.fetchall()
    except Exception as e:
        raise e
    

# Optional: Get users with pagination

def get_all_users_paginated(conn, page: int, page_size: int):
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be >= 1")

    offset = (page - 1) * page_size
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Fetch paginated data
            cur.execute(SELECT_ALL_USERS_PAGINATED_QUERY, (page_size, offset))
            users = cur.fetchall()

                # Fetch total count
            cur.execute(COUNT_USERS_QUERY)
            total = cur.fetchone()["total"]

        return users, total

    except Exception as e:
        raise RuntimeError(f"Failed to fetch users: {str(e)}")
