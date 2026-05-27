"""End-to-end auth endpoint tests with a real (non-bypassed) TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from provectus_analytics import db as _db
from provectus_analytics.api import queries as web_data
from provectus_analytics.auth import users
from provectus_analytics.auth.rate_limit import limiter


@pytest.fixture
def app_with_db(tmp_path, monkeypatch):
    """Build a fresh app pointing at a tmp DB with a seeded user.

    Note: we DO NOT inherit the test_api conftest's auth bypass — these tests
    live in tests/test_auth/, which is a sibling tree.
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()

    # Seed a test user directly in the DB.
    conn = _db.connect(db_path)
    users.ensure_users_table(conn)
    users.create_user(conn, "alice@example.com", "alicepassword", role="admin")
    conn.close()

    # Reset rate limiter between tests so login attempts don't leak.
    limiter.reset()

    from provectus_analytics.api import create_app
    app = create_app()
    yield app
    limiter.reset()


@pytest.fixture
def client(app_with_db):
    return TestClient(app_with_db)


def test_login_returns_token_pair(client):
    r = client.post("/api/auth/login",
                    json={"email": "alice@example.com", "password": "alicepassword"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client):
    r = client.post("/api/auth/login",
                    json={"email": "alice@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_email_returns_401(client):
    r = client.post("/api/auth/login",
                    json={"email": "ghost@nowhere.com", "password": "whatever"})
    assert r.status_code == 401


def test_login_invalid_email_format_returns_422(client):
    r = client.post("/api/auth/login",
                    json={"email": "not-an-email", "password": "anything"})
    assert r.status_code == 422


def test_protected_route_without_token_returns_401(client):
    r = client.get("/api/kpis?range=12mo")
    assert r.status_code == 401


def test_protected_route_with_bearer_token_returns_200(client):
    login = client.post("/api/auth/login",
                        json={"email": "alice@example.com", "password": "alicepassword"})
    token = login.json()["access_token"]
    r = client.get("/api/kpis?range=12mo",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_me_returns_current_user(client):
    login = client.post("/api/auth/login",
                        json={"email": "alice@example.com", "password": "alicepassword"})
    token = login.json()["access_token"]
    r = client.get("/api/auth/me",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "admin"
    assert body["is_active"] is True


def test_refresh_returns_new_token_pair(client):
    login = client.post("/api/auth/login",
                        json={"email": "alice@example.com", "password": "alicepassword"})
    refresh_tok = login.json()["refresh_token"]
    r = client.post("/api/auth/refresh", json={"refresh_token": refresh_tok})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_refresh_with_access_token_rejected(client):
    """Using an access token where a refresh token is required must fail."""
    login = client.post("/api/auth/login",
                        json={"email": "alice@example.com", "password": "alicepassword"})
    access = login.json()["access_token"]
    r = client.post("/api/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


def test_logout_requires_auth(client):
    r = client.post("/api/auth/logout")
    assert r.status_code == 401


def test_logout_with_token_returns_204(client):
    login = client.post("/api/auth/login",
                        json={"email": "alice@example.com", "password": "alicepassword"})
    token = login.json()["access_token"]
    r = client.post("/api/auth/logout",
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204


def test_healthz_remains_public(client):
    """The health check stays unauthenticated so Railway can poll it."""
    r = client.get("/api/healthz")
    assert r.status_code == 200


def test_login_rate_limited_after_threshold(client):
    """slowapi caps login attempts to settings.login_rate_limit per IP."""
    # The configured limit is "10/minute" — after 10 attempts the 11th gets 429.
    payload = {"email": "alice@example.com", "password": "wrong"}
    statuses = []
    for _ in range(12):
        r = client.post("/api/auth/login", json=payload)
        statuses.append(r.status_code)
    assert 429 in statuses, f"expected at least one 429, got {statuses}"
