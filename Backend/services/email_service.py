"""
Email service.

In production we use `fastapi-mail` (already in requirements.txt). In dev,
when no SMTP_HOST is configured, we fall back to logging the reset link to
stdout so reviewers can copy/paste it without setting up a mail server.
"""

import logging
from pathlib import Path

from core.config import (
    EMAIL_ENABLED,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_STARTTLS,
    MAIL_FROM,
    MAIL_FROM_NAME,
    RESET_TOKEN_TTL_MIN,
)

logger = logging.getLogger("email_service")

_TEMPLATE_DIR = Path(__file__).parent / "email_templates"


def _load_template(name: str) -> str:
    return (_TEMPLATE_DIR / name).read_text(encoding="utf-8")


async def send_password_reset(to_email: str, reset_link: str) -> None:
    """
    Send the password-reset email. Falls back to a stdout log line if SMTP
    is not configured — this is the explicit dev-mode behavior.
    """
    text_body = _load_template("password_reset.txt").format(
        reset_link=reset_link, ttl_minutes=RESET_TOKEN_TTL_MIN
    )
    html_body = _load_template("password_reset.html").format(
        reset_link=reset_link, ttl_minutes=RESET_TOKEN_TTL_MIN
    )

    if not EMAIL_ENABLED:
        # Dev fallback: print the link in a way that's easy to grep.
        logger.warning(
            "[email_service] SMTP not configured. Password reset link for %s: %s",
            to_email,
            reset_link,
        )
        print(f"\n[DEV] Password reset link for {to_email}: {reset_link}\n", flush=True)
        return

    # Lazy import so missing SMTP config in dev doesn't pull fastapi-mail.
    from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

    conf = ConnectionConfig(
        MAIL_USERNAME=SMTP_USER,
        MAIL_PASSWORD=SMTP_PASSWORD,
        MAIL_FROM=MAIL_FROM,
        MAIL_FROM_NAME=MAIL_FROM_NAME,
        MAIL_PORT=SMTP_PORT,
        MAIL_SERVER=SMTP_HOST,
        MAIL_STARTTLS=SMTP_STARTTLS,
        MAIL_SSL_TLS=not SMTP_STARTTLS,
        USE_CREDENTIALS=bool(SMTP_USER),
        VALIDATE_CERTS=True,
    )

    message = MessageSchema(
        subject="Reset your Task Management System password",
        recipients=[to_email],
        body=html_body,
        alternative_body=text_body,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
    except Exception as e:
        # Don't leak SMTP errors back to the client (the controller still
        # returns 202 unconditionally). Just log them.
        logger.exception("Failed to send password-reset email to %s: %s", to_email, e)
