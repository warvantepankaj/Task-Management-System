# Feature: Refresh Token System

## Why

- A single access token with a 60-minute TTL is issued at login (`core/jwt.py:6`, `controllers/auth_controller.py:30-56`). When it expires, the user is silently logged out — the response interceptor at `services/api.js` redirects to `/login` on any 401.
- `SECRET_KEY = "TOP_SECRET"` is hardcoded **twice** (`core/jwt.py:4` and `utils/security.py:20`). It must move into env config before this feature ships.
- There is no concept of revocation: a leaked token is valid for its full TTL with no kill-switch.
- The frontend has two axios instances (`src/config/api.js` and `src/services/api.js`) that disagree on the localStorage key (`access_token` vs `token`). This must be reconciled when wiring up the refresh interceptor.

## Scope

**In scope**
- Short-lived access token (15 min) + long-lived refresh token (14 days), with rotation on every refresh.
- Server-side revocation (`/auth/logout`, plus `revoked_at` column).
- Move JWT secret + TTLs into `core/config.py` env settings.
- Axios response interceptor that transparently refreshes on 401 and retries the original request.
- Single-flight refresh: concurrent 401s queue behind one in-flight refresh promise.

**Out of scope**
- Per-device session list UI ("active sessions").
- OAuth / social login.
- Sliding-window refresh (each refresh just resets the 14 days from now).

## API Contract

### `POST /login`

**Request** (`schemas/auth.UserLogin`)

```json
{ "email": "x@y.com", "password": "..." }
```

**Response 200** (new shape)

```json
{
  "access_token": "<jwt, 15 min>",
  "refresh_token": "<opaque, 14 days>",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { "id": 1, "email": "x@y.com", "role": "admin", "username": "x" }
}
```

### `POST /auth/refresh`

**Request**

```json
{ "refresh_token": "<opaque>" }
```

**Response 200** — same shape as login. **Rotation** is mandatory: the supplied refresh token is revoked, a new pair is issued.

**Errors**
- `401 invalid_refresh_token` — not found, hash mismatch, expired, or `revoked_at` set.
- `401 user_inactive` — user record has `is_active = false`.

### `POST /auth/logout`

**Request**

```json
{ "refresh_token": "<opaque>" }
```

**Response 204** — token's `revoked_at = NOW()`. Idempotent; unknown tokens return 204.

### Access-token claims

```json
{
  "user_id": 1,
  "role": "admin",
  "token_type": "access",
  "iat": ...,
  "exp": ...
}
```

`utils/security.get_current_user` (`utils/security.py:25-48`) **must** reject any token where `token_type != "access"` to stop a refresh token from being used as an access token.

## Database Changes

Add to `schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    user_agent TEXT,
    ip INET,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_active
  ON refresh_tokens (user_id, expires_at)
  WHERE revoked_at IS NULL;
```

- `token_hash` stores `sha256(refresh_token)` — never the raw token.
- Cleanup job (out of scope, but easy): `DELETE FROM refresh_tokens WHERE expires_at < NOW() - INTERVAL '30 days'`.

## Files to Change

### Backend

- `core/config.py` — add settings: `JWT_SECRET` (required), `ACCESS_TOKEN_TTL_MIN=15`, `REFRESH_TOKEN_TTL_DAYS=14`. Fail fast at startup if `JWT_SECRET` is missing or equals `"TOP_SECRET"`.
- `core/jwt.py` — remove hardcoded `SECRET_KEY`; read from config. Split into `create_access_token` (adds `token_type="access"`) and `create_refresh_token` (random 32-byte URL-safe string, **not** a JWT — opaque tokens are cheaper and safer because they're hash-stored and revocable). Provide `hash_refresh_token(token) -> str`.
- `utils/security.py:20` — drop the duplicate `SECRET_KEY`. Use `decode_token` from `core/jwt.py`. Reject if `payload["token_type"] != "access"`.
- `schemas/auth.py` — add `TokenPair`, `RefreshRequest`, `LogoutRequest`, `LoginResponse`.
- `queries/refresh_token_queries.py` — new file: `INSERT_REFRESH_TOKEN`, `GET_REFRESH_TOKEN_BY_HASH`, `REVOKE_REFRESH_TOKEN`, `REVOKE_ALL_FOR_USER`.
- `dao/refresh_token_dao.py` — new: `create(conn, user_id, token_hash, expires_at, user_agent, ip)`, `get_active_by_hash(conn, token_hash)`, `revoke(conn, token_hash)`, `revoke_all_for_user(conn, user_id)`.
- `services/auth_service.py:14-20` — rewrite `login_user` to issue both tokens, store refresh hash in DB. Add `refresh_tokens(conn, refresh_token, request)` (validate → rotate → return new pair) and `logout(conn, refresh_token)`.
- `controllers/auth_controller.py:30-56` — fix the existing import shadowing bug (the controller defines `login_user` and never calls the service). Add `POST /auth/refresh` and `POST /auth/logout` endpoints. Capture `request.client.host` and `request.headers.get("user-agent")` for the new row.
- `main.py` — no new router (auth routes stay on `auth_router`).
- `schema.sql` — DDL above.

### Frontend

- `src/config/api.js` — **delete** (consolidate into `services/api.js`). Audit all imports and switch them to the consolidated module. Standardize on localStorage keys `access_token` and `refresh_token`.
- `src/services/api.js` — replace the existing response interceptor:
  - On 401, check if the request was `/auth/refresh` itself → hard logout (avoid recursion).
  - Otherwise, queue the failing request, call `/auth/refresh` once, replay queued requests with the new access token.
  - Use a module-level `refreshPromise` so multiple concurrent 401s share one refresh.
- `src/services/api.js` — `authAPI.refresh(refresh_token)` and `authAPI.logout(refresh_token)`.
- `src/context/AuthContext.jsx` — store both tokens; `logout()` should `POST /auth/logout` (best-effort) before clearing localStorage. Remove the `axios.defaults.headers.common` mutation — the interceptor already handles it.
- `src/pages/Login.jsx:37` — destructure `{ access_token, refresh_token, user }` from the response; pass both to `login(user, access_token, refresh_token)`.
- `src/utils/constants.js` — `STORAGE_KEYS = { ACCESS: "access_token", REFRESH: "refresh_token", USER: "user" }`. Use everywhere instead of magic strings.

## Acceptance Criteria

- [ ] `POST /login` returns `{ access_token, refresh_token, ... }`; access JWT decodes to `{ token_type: "access", exp ≈ now + 15m }`.
- [ ] `POST /auth/refresh` with the issued refresh token returns a **new** pair; the old refresh token's row has `revoked_at IS NOT NULL`.
- [ ] Replaying the old refresh token (or any revoked token) returns 401.
- [ ] Using a refresh token as a bearer access token returns 401.
- [ ] `POST /auth/logout` revokes the supplied refresh token; subsequent `/auth/refresh` with it returns 401.
- [ ] Frontend: when the access token expires mid-session, the next API call transparently refreshes and the user does not see a redirect to `/login`.
- [ ] Concurrent 401s (e.g., three parallel requests after expiry) trigger exactly **one** `/auth/refresh` call (verified in network tab).
- [ ] On app start with no `JWT_SECRET` env var, the backend refuses to start.

## Notes / Open Questions

- **Refresh token format**: opaque random string is the recommendation (revocable by hash lookup, no JWT-decode surface area). Alternative is a JWT with a `jti` and a `jti_blacklist` — more moving parts, no real win here.
- **Frontend storage**: `localStorage` is acceptable for this app but vulnerable to XSS. Stronger option is HttpOnly cookies for the refresh token + access token in memory; deferred because it changes CORS and CSRF posture significantly.
- **Coordinate with `password-reset.md`**: when a user successfully resets their password, call `revoke_all_for_user(user_id)` to log out other devices.
- **Coordinate with `websockets.md`**: open sockets must reconnect with a fresh access token after refresh.
