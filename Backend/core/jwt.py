import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from core.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    ACCESS_TOKEN_TTL_MIN,
    REFRESH_TOKEN_TTL_DAYS,
)

# Backwards-compatible aliases (do not interpolate at module import; rely on
# the values loaded from core.config so callers always see env-driven values).
SECRET_KEY = JWT_SECRET
ALGORITHM = JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_TTL_MIN


def create_access_token(data: dict, expires_delta: int | None = None) -> str:
    """
    Issue a short-lived access JWT.

    A ``token_type="access"`` claim is added so callers (e.g.
    ``utils.security.get_current_user``) can reject refresh tokens that get
    presented as bearer tokens.
    """
    to_encode = data.copy()
    minutes = expires_delta if expires_delta is not None else ACCESS_TOKEN_TTL_MIN
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "token_type": "access",
    })
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str):
    """Decode a JWT, returning the claims dict on success, ``None`` on any error."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def create_refresh_token() -> str:
    """
    Return an opaque 32-byte URL-safe refresh token.

    Opaque tokens (vs. another JWT) are easier to revoke: only the SHA-256
    hash is stored server-side, and a single DB lookup tells us whether the
    token is still valid.
    """
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Return a deterministic SHA-256 hash of the raw refresh token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    """The absolute UTC expiry timestamp for a freshly-issued refresh token."""
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
