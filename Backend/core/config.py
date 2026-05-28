import os
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path(
    "C:\\Pankaj's Space\\Projects\\FAST-API\\Task_Management_System\\Backend\\.env"
)
load_dotenv(ENV_PATH)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

DB_NAME = os.getenv("DATABASE_NAME")
DB_USER = os.getenv("DATABASE_USER")
DB_PASSWORD = os.getenv("DATABASE_PASSWORD")
DB_HOST = os.getenv("DATABASE_HOST")
DB_PORT = os.getenv("DATABASE_PORT")

if not DB_PASSWORD:
    raise RuntimeError("DB_PASSWORD is not set in environment")


# ---------- JWT / Auth ----------

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

# Access tokens are short-lived JWTs.
ACCESS_TOKEN_TTL_MIN = int(os.getenv("ACCESS_TOKEN_TTL_MIN", "15"))

# Refresh tokens are opaque random strings; we store sha256(token) in the DB.
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "14"))

# Fail fast at startup: do not allow the historical hardcoded value or empty/missing.
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not set. Generate one with `python -c \"import secrets; "
        "print(secrets.token_urlsafe(64))\"` and add it to Backend/.env."
    )
if JWT_SECRET == "TOP_SECRET":
    raise RuntimeError(
        "JWT_SECRET is still set to the placeholder 'TOP_SECRET'. "
        "Replace it with a real secret before starting the server."
    )


# ---------- Email / Password reset ----------

SMTP_HOST = os.getenv("SMTP_HOST") or ""
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER") or ""
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or ""
SMTP_STARTTLS = (os.getenv("SMTP_STARTTLS", "True").lower() == "true")
MAIL_FROM = os.getenv("MAIL_FROM") or "no-reply@example.com"
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME") or "Task Management System"
FRONTEND_URL = os.getenv("FRONTEND_URL") or "http://localhost:3000"
RESET_TOKEN_TTL_MIN = int(os.getenv("RESET_TOKEN_TTL_MIN", "60"))

# `EMAIL_ENABLED` is True only when we have an actual SMTP host configured.
# In dev (no SMTP), the email service falls back to logging the reset link.
EMAIL_ENABLED = bool(SMTP_HOST)
