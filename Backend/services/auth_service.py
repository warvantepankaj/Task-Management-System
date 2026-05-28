from datetime import datetime, timezone

from fastapi import HTTPException

from dao import refresh_token_dao
from dao.user_dao import create_user, get_user_by_email, get_user_by_id
from utils.security import hash_password, verify_password
from core.jwt import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from core.config import ACCESS_TOKEN_TTL_MIN


def register_user(conn, username, email, password, role):
    existing_user = get_user_by_email(conn, email)
    if existing_user:
        return None, "Email already registered"

    hashed = hash_password(password)
    user = create_user(conn, username, email, hashed, role)
    return user, None


def _issue_token_pair(conn, user, user_agent: str | None, ip: str | None) -> dict:
    """
    Issue a fresh (access, refresh) pair and persist the refresh-token hash.
    Returns the wire-format dict the controller will send back as JSON.
    """
    access_token = create_access_token({"user_id": user["id"], "role": user["role"]})

    refresh_raw = create_refresh_token()
    refresh_token_dao.create(
        conn,
        user_id=user["id"],
        token_hash=hash_refresh_token(refresh_raw),
        expires_at=refresh_token_expiry(),
        user_agent=user_agent,
        ip=ip,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_raw,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_TTL_MIN * 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "username": user["username"],
        },
    }


def login_user(conn, email: str, password: str, user_agent: str | None = None, ip: str | None = None):
    """Verify credentials, issue (access, refresh), persist refresh hash, commit."""
    user = get_user_by_email(conn, email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = _issue_token_pair(conn, user, user_agent, ip)
    conn.commit()
    return payload


def refresh_tokens(conn, refresh_token: str, user_agent: str | None = None, ip: str | None = None):
    """
    Validate the supplied refresh token, revoke it, and issue a new pair
    (rotation). Raises 401 on any failure.
    """
    token_hash = hash_refresh_token(refresh_token)
    row = refresh_token_dao.get_active_by_hash(conn, token_hash)

    if not row or row["revoked_at"] is not None:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")

    expires_at = row["expires_at"]
    # psycopg2 returns timezone-aware timestamps for TIMESTAMPTZ columns.
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="invalid_refresh_token")

    user = get_user_by_id(conn, row["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="user_inactive")
    # get_user_by_id already filters on is_active = TRUE; the absence above
    # covers both "deleted" and "deactivated".

    # Rotate: revoke the presented token, mint a new pair.
    refresh_token_dao.revoke(conn, token_hash)
    payload = _issue_token_pair(conn, user, user_agent, ip)
    conn.commit()
    return payload


def logout(conn, refresh_token: str) -> None:
    """Idempotently revoke the supplied refresh token."""
    token_hash = hash_refresh_token(refresh_token)
    refresh_token_dao.revoke(conn, token_hash)
    conn.commit()
