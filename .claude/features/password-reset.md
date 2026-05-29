# Feature: Password Reset Flow

## Why

- There is no recovery path today. If a user forgets their password, the only fix is an admin direct DB update.
- `Backend/requirements.txt` already lists `fastapi-mail==1.6.2` and `aiosmtplib==5.1.0` — installed but never imported.
- No `password_reset_tokens` table, no `/forgot-password` or `/reset-password` endpoint, no email service utility, no UI.
- `Login.jsx` has no "Forgot password?" link.

This spec adds the standard double-opt-in flow: request reset by email → click time-limited link → set new password.

## Scope

**In scope**
- `POST /auth/forgot-password` (request reset) and `POST /auth/reset-password` (consume token).
- Single-use, hashed, 1-hour-TTL reset tokens.
- SMTP-backed email via `fastapi-mail` with a plain text + HTML template.
- Two new frontend pages and a link from the login screen.
- Revoke all refresh tokens on successful reset (coordinates with `refresh-token.md`).

**Out of scope**
- Account lockout after N forgot-password requests (rate limiting noted but deferred — see Notes).
- Email verification at signup.
- 2FA / TOTP.

## API Contract

### `POST /auth/forgot-password`

**Request**

```json
{ "email": "x@y.com" }
```

**Response 202** — **always**, regardless of whether the email exists, to avoid leaking which addresses are registered.

```json
{ "message": "If an account exists for this email, a reset link has been sent." }
```

Server-side behavior:
- If the user exists and is active: generate 32-byte URL-safe token; insert `sha256(token)` into `password_reset_tokens` with `expires_at = NOW() + INTERVAL '1 hour'`; send email containing link `${FRONTEND_URL}/reset-password?token=<raw>`.
- Otherwise: no-op. Same 202 response. (Optionally still incur an artificial delay to defeat timing oracles.)

### `POST /auth/reset-password`

**Request**

```json
{ "token": "<raw token from email link>", "new_password": "..." }
```

**Response 200**

```json
{ "message": "Password updated. Please log in." }
```

**Errors**
- `400 invalid_or_expired_token` — token not found, already used (`used_at IS NOT NULL`), or expired.
- `422` — `new_password` fails strength rules (min length 8; reject if equals current — see Notes).

Server-side behavior:
1. Look up token by `sha256(raw)`.
2. Reject if `used_at IS NOT NULL` or `expires_at < NOW()`.
3. Update `users.password_hash` via `utils/security.hash_password`.
4. Mark `used_at = NOW()`.
5. Call `refresh_token_dao.revoke_all_for_user(user_id)` (see `refresh-token.md`).

## Database Changes

Add to `schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user
  ON password_reset_tokens (user_id, expires_at);
```

## Files to Change

### Backend

- `core/config.py` — add settings: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_STARTTLS=True`, `MAIL_FROM`, `MAIL_FROM_NAME="Task Management System"`, `FRONTEND_URL=http://localhost:3000`, `RESET_TOKEN_TTL_MIN=60`. Validation: warn (don't fail) if SMTP settings are missing — allow dev to log the reset link to stdout instead of sending.
- `services/email_service.py` — new. Wraps `fastapi_mail.FastMail` with one method `send_password_reset(to_email, reset_link)`. In dev (no SMTP config), logs the link instead.
- `services/email_templates/password_reset.html` and `.txt` — new. Minimal branded templates; the link is the only dynamic piece.
- `schemas/auth.py` — add `ForgotPasswordRequest`, `ResetPasswordRequest` (with `new_password: constr(min_length=8)`).
- `queries/password_reset_queries.py` — new: `INSERT_RESET_TOKEN`, `GET_RESET_TOKEN_BY_HASH`, `MARK_RESET_TOKEN_USED`, `INVALIDATE_USER_RESET_TOKENS` (called on successful reset so other outstanding links die too).
- `dao/password_reset_dao.py` — new: thin wrappers over the queries.
- `services/auth_service.py` — add `forgot_password(conn, email, request)` and `reset_password(conn, token, new_password)`. Coordinates with `refresh_token_dao.revoke_all_for_user`.
- `controllers/auth_controller.py` — add `POST /auth/forgot-password` and `POST /auth/reset-password`.
- `schema.sql` — DDL above.

### Frontend

- `src/pages/ForgotPassword.jsx` — new. Email input, submit posts to `/auth/forgot-password`, then shows a "check your email" confirmation regardless of the response (consistent with the 202 contract).
- `src/pages/ResetPassword.jsx` — new. Reads `?token=` from URL via `useSearchParams`; two password inputs ("new", "confirm") with client-side match check + min-length; on success, redirect to `/login` with a toast.
- `src/pages/Login.jsx:88` — add `<Link to="/forgot-password">Forgot password?</Link>` below the password input.
- `src/App.jsx:23` — add routes `/forgot-password` and `/reset-password` (both public).
- `src/services/api.js` — `authAPI.forgotPassword({ email })`, `authAPI.resetPassword({ token, new_password })`.

## Acceptance Criteria

- [ ] `POST /auth/forgot-password` with an unknown email returns 202 (no information leak).
- [ ] `POST /auth/forgot-password` with a known email inserts a row in `password_reset_tokens` and sends an email (or logs the link in dev mode).
- [ ] Clicking the link with a valid token reaches `/reset-password?token=...` and the form is usable.
- [ ] `POST /auth/reset-password` with a valid token updates `users.password_hash` and marks the token used.
- [ ] Replaying the same token returns 400.
- [ ] A token whose `expires_at` is in the past returns 400.
- [ ] After a successful reset, all of the user's existing refresh tokens are revoked (must re-login from every device).
- [ ] Resetting a password less than 8 chars returns 422.
- [ ] Full happy path E2E: forgot → email link → reset → login with new password.

## Notes / Open Questions

- **Rate limiting**: deferred. When implemented, throttle `/auth/forgot-password` per-IP and per-email (e.g., 3 per hour) to avoid email-bombing. A simple in-memory limiter is fine until traffic justifies Redis.
- **Reject password reuse**: spec includes "reject if equals current" — implementation must verify old password via `verify_password(new, current_hash)`; if true, return 422. This costs one bcrypt op per reset, acceptable.
- **Token entropy**: `secrets.token_urlsafe(32)` → ~43 chars, 256 bits of entropy. Plenty.
- **Email content**: template must include the expiry window ("This link expires in 1 hour") and a "If you didn't request this, ignore this email" line.
- **SMTP provider**: dev uses `smtp.mailtrap.io` or local `MailHog`; prod TBD by user.
