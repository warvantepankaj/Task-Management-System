from datetime import datetime

from psycopg2.extras import RealDictCursor

from queries.password_reset_queries import (
    INSERT_RESET_TOKEN,
    GET_RESET_TOKEN_BY_HASH,
    MARK_RESET_TOKEN_USED,
    INVALIDATE_USER_RESET_TOKENS,
    UPDATE_USER_PASSWORD,
)


def create(conn, user_id: int, token_hash: str, expires_at: datetime):
    """Insert a new reset-token row. Caller commits."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(INSERT_RESET_TOKEN, (user_id, token_hash, expires_at))
        return cur.fetchone()


def get_by_hash(conn, token_hash: str):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(GET_RESET_TOKEN_BY_HASH, (token_hash,))
        return cur.fetchone()


def mark_used(conn, token_hash: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(MARK_RESET_TOKEN_USED, (token_hash,))
        return cur.fetchone() is not None


def invalidate_user_tokens(conn, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(INVALIDATE_USER_RESET_TOKENS, (user_id,))


def update_user_password(conn, user_id: int, new_password_hash: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(UPDATE_USER_PASSWORD, (new_password_hash, user_id))
        return cur.fetchone() is not None
