from datetime import datetime

from psycopg2.extras import RealDictCursor

from queries.refresh_token_queries import (
    INSERT_REFRESH_TOKEN,
    GET_REFRESH_TOKEN_BY_HASH,
    REVOKE_REFRESH_TOKEN,
    REVOKE_ALL_FOR_USER,
)


def create(
    conn,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip: str | None = None,
):
    """Insert a new refresh-token row. Caller commits."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            INSERT_REFRESH_TOKEN,
            (user_id, token_hash, expires_at, user_agent, ip),
        )
        return cur.fetchone()


def get_active_by_hash(conn, token_hash: str):
    """
    Return the row matching ``token_hash``. The caller is responsible for
    checking ``expires_at`` / ``revoked_at`` — returning the raw row keeps the
    DAO query-agnostic.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(GET_REFRESH_TOKEN_BY_HASH, (token_hash,))
        return cur.fetchone()


def revoke(conn, token_hash: str) -> bool:
    """Mark the row revoked. Returns True if a row was updated. Caller commits."""
    with conn.cursor() as cur:
        cur.execute(REVOKE_REFRESH_TOKEN, (token_hash,))
        return cur.fetchone() is not None


def revoke_all_for_user(conn, user_id: int) -> None:
    """Revoke every active refresh token for a user. Caller commits."""
    with conn.cursor() as cur:
        cur.execute(REVOKE_ALL_FOR_USER, (user_id,))
