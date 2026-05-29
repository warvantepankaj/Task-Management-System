"""
Integration tests for the authentication flow.

Covers the highest-value paths a reviewer checks first: registration,
login, refresh-token rotation + reuse rejection, logout revocation, bearer
token enforcement, and the forgot/reset password lifecycle. Every test runs
against a real PostgreSQL database (see conftest.py).
"""
import pytest

pytestmark = pytest.mark.integration


# ---------- Registration ----------

def test_register_returns_user(client):
    resp = client.post(
        "/register",
        json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "Sup3rSecret!",
            "role": "user",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["email"] == "bob@example.com"
    assert body["user"]["role"] == "user"
    assert body["user"]["is_active"] is True
    # The password must never echo back.
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_register_duplicate_email_is_rejected(client):
    payload = {
        "username": "carol",
        "email": "carol@example.com",
        "password": "Sup3rSecret!",
        "role": "user",
    }
    first = client.post("/register", json=payload)
    assert first.status_code == 200, first.text

    second = client.post(
        "/register",
        json={**payload, "username": "carol2"},
    )
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"].lower()


# ---------- Login ----------

def test_login_success_returns_token_pair(register_and_login):
    body = register_and_login()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["email"] == "alice@example.com"
    # Access and refresh tokens must be distinct values.
    assert body["access_token"] != body["refresh_token"]


def test_login_wrong_password_is_401(client, register_and_login):
    register_and_login(email="dave@example.com")
    resp = client.post(
        "/login", json={"email": "dave@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


def test_login_unknown_email_is_401(client):
    resp = client.post(
        "/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert resp.status_code == 401


# ---------- Refresh-token rotation ----------

def test_refresh_rotates_and_old_token_is_rejected(client, register_and_login):
    body = register_and_login()
    old_refresh = body["refresh_token"]

    rotated = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200, rotated.text
    new_body = rotated.json()
    assert new_body["refresh_token"] != old_refresh
    assert new_body["access_token"]

    # Reusing the now-rotated (revoked) refresh token must fail.
    replay = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401
    assert replay.json()["detail"] == "invalid_refresh_token"

    # The freshly-issued refresh token still works.
    again = client.post(
        "/auth/refresh", json={"refresh_token": new_body["refresh_token"]}
    )
    assert again.status_code == 200, again.text


def test_refresh_with_garbage_token_is_401(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


# ---------- Logout ----------

def test_logout_revokes_refresh_token(client, register_and_login):
    body = register_and_login()
    refresh = body["refresh_token"]

    logout = client.post("/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 204

    # Token is dead after logout.
    resp = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


def test_logout_is_idempotent(client):
    # Unknown / already-revoked tokens still return 204.
    resp = client.post("/auth/logout", json={"refresh_token": "anything"})
    assert resp.status_code == 204


# ---------- Bearer-token enforcement ----------

def test_access_token_authorizes_protected_route(client, register_and_login):
    body = register_and_login()
    resp = client.get(
        "/tasks/filtered",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 0
    assert data["data"] == []


def test_protected_route_without_token_is_401(client):
    resp = client.get("/tasks/filtered")
    assert resp.status_code == 401


def test_refresh_token_cannot_be_used_as_bearer(client, register_and_login):
    body = register_and_login()
    # The opaque refresh token is not a valid access JWT.
    resp = client.get(
        "/tasks/filtered",
        headers={"Authorization": f"Bearer {body['refresh_token']}"},
    )
    assert resp.status_code == 401


# ---------- Forgot / reset password ----------

def test_forgot_password_always_202(client, register_and_login):
    register_and_login(email="erin@example.com")
    # Known address.
    known = client.post("/auth/forgot-password", json={"email": "erin@example.com"})
    assert known.status_code == 202
    # Unknown address — must not leak that it isn't registered.
    unknown = client.post(
        "/auth/forgot-password", json={"email": "ghost@example.com"}
    )
    assert unknown.status_code == 202
    assert known.json() == unknown.json()


def test_full_password_reset_flow(client, register_and_login, monkeypatch):
    email = "frank@example.com"
    old_password = "Sup3rSecret!"
    new_password = "BrandNewPass99!"
    register_and_login(username="frank", email=email, password=old_password)

    # Capture the reset link instead of sending an email.
    captured = {}

    async def _fake_send(to_email, reset_link):
        captured["to"] = to_email
        captured["link"] = reset_link

    monkeypatch.setattr(
        "services.email_service.send_password_reset", _fake_send
    )

    resp = client.post("/auth/forgot-password", json={"email": email})
    assert resp.status_code == 202
    assert captured["to"] == email
    token = captured["link"].split("token=", 1)[1]

    # Reset the password.
    reset = client.post(
        "/auth/reset-password", json={"token": token, "new_password": new_password}
    )
    assert reset.status_code == 200, reset.text

    # Old password no longer works; new one does.
    assert client.post(
        "/login", json={"email": email, "password": old_password}
    ).status_code == 401
    assert client.post(
        "/login", json={"email": email, "password": new_password}
    ).status_code == 200

    # The reset token is single-use.
    replay = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "AnotherPass1!"}
    )
    assert replay.status_code == 400


def test_reset_password_with_invalid_token_is_400(client):
    resp = client.post(
        "/auth/reset-password",
        json={"token": "bogus-token", "new_password": "ValidPass123!"},
    )
    assert resp.status_code == 400


def test_reset_password_rejects_short_password(client, register_and_login, monkeypatch):
    email = "grace@example.com"
    register_and_login(username="grace", email=email)

    captured = {}

    async def _fake_send(to_email, reset_link):
        captured["link"] = reset_link

    monkeypatch.setattr("services.email_service.send_password_reset", _fake_send)
    client.post("/auth/forgot-password", json={"email": email})
    token = captured["link"].split("token=", 1)[1]

    # Pydantic enforces min_length=8 -> 422 before the handler runs.
    resp = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "short"}
    )
    assert resp.status_code == 422
