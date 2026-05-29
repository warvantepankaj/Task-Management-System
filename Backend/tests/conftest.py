"""
Pytest fixtures for backend integration tests.

These tests run against a REAL PostgreSQL database (a dedicated test DB,
never the dev/prod one). Strategy:

- Configure DB + JWT env vars *before* the app is imported, forcing the app
  onto the test database.
- Ensure the test database exists and apply `schema.sql` once per session.
- Truncate all tables before every test for isolation.

Locally: needs a reachable PostgreSQL. Credentials come from your existing
`Backend/.env` (loaded by `core.config`); the test DB name is overridable via
`TEST_DATABASE_NAME` (default `task_management_system_db_test`). The DB is
created automatically if it does not exist.

CI: the workflow provides a PostgreSQL service and sets the DATABASE_* env
vars directly.
"""
import os
from pathlib import Path

# --- Force test configuration BEFORE importing anything app-related. ---------
# core.config calls load_dotenv(override=False), so values we set here win over
# whatever is in Backend/.env. We deliberately do NOT touch DATABASE_PASSWORD /
# _USER / _HOST / _PORT so that local runs inherit them from .env and CI runs
# inherit them from real environment variables.
_TEST_DB_NAME = os.getenv("TEST_DATABASE_NAME", "task_management_system_db_test")
os.environ["DATABASE_NAME"] = _TEST_DB_NAME
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5432")
os.environ.setdefault("DATABASE_USER", "postgres")
os.environ.setdefault("JWT_SECRET", "test-only-secret-not-used-in-production")
os.environ.setdefault("ACCESS_TOKEN_TTL_MIN", "15")
os.environ.setdefault("REFRESH_TOKEN_TTL_DAYS", "14")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
# SMTP intentionally unset -> email_service logs the reset link instead of
# sending. Tests monkeypatch send_password_reset to capture the link directly.

import psycopg2  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Importing the app triggers core.config (which validates JWT_SECRET etc.).
from main import app  # noqa: E402
from database.session import get_db  # noqa: E402

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schema.sql"
_TABLES = [
    "task_comments",
    "tasks",
    "password_reset_tokens",
    "refresh_tokens",
    "users",
]


def _conn_params(dbname: str) -> dict:
    return {
        "dbname": dbname,
        "user": os.environ["DATABASE_USER"],
        "password": os.environ.get("DATABASE_PASSWORD", ""),
        "host": os.environ["DATABASE_HOST"],
        "port": os.environ["DATABASE_PORT"],
    }


def _ensure_test_database() -> None:
    """Create the test database if it doesn't already exist."""
    try:
        conn = psycopg2.connect(**_conn_params(_TEST_DB_NAME))
        conn.close()
        return  # already exists and reachable
    except psycopg2.OperationalError:
        pass

    # Connect to the maintenance DB to issue CREATE DATABASE.
    admin = psycopg2.connect(**_conn_params("postgres"))
    admin.autocommit = True
    try:
        with admin.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (_TEST_DB_NAME,)
            )
            if cur.fetchone() is None:
                # Identifier can't be parameterized; _TEST_DB_NAME is operator-controlled.
                cur.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    finally:
        admin.close()


def _apply_schema() -> None:
    conn = psycopg2.connect(**_conn_params(_TEST_DB_NAME))
    try:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _db_setup():
    """Once per session: ensure the test DB exists and the schema is applied."""
    _ensure_test_database()
    _apply_schema()
    yield


@pytest.fixture(autouse=True)
def _truncate_between_tests():
    """Wipe all rows before each test so cases don't bleed into one another."""
    conn = psycopg2.connect(**_conn_params(_TEST_DB_NAME))
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE"
            )
        conn.commit()
    finally:
        conn.close()
    yield


@pytest.fixture
def client():
    """FastAPI test client wired to the test database via get_db.

    A realistic client address is supplied because the auth flow records the
    originating IP into an INET column; TestClient's default ("testclient")
    is not a valid inet value.
    """
    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        yield c


# ---- Convenience helpers -----------------------------------------------------

@pytest.fixture
def register_and_login(client):
    """
    Returns a factory that registers a user and logs them in, yielding the
    full login response body (access_token, refresh_token, user).
    """
    def _factory(
        username="alice",
        email="alice@example.com",
        password="Sup3rSecret!",
        role="user",
    ):
        reg = client.post(
            "/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "role": role,
            },
        )
        assert reg.status_code == 200, reg.text
        login = client.post("/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        return login.json()

    return _factory
