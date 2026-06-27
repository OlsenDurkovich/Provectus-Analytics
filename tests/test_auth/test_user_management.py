"""User management, role permissions, change-password, and role migration.

Uses a real (non-bypassed) TestClient with seeded admin/instructor/viewer
users, mirroring tests/test_auth/test_endpoints.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from provectus_analytics import db as _db
from provectus_analytics.api import queries as web_data
from provectus_analytics.auth import users
from provectus_analytics.auth.rate_limit import limiter


@pytest.fixture
def app_with_users(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()

    conn = _db.connect(db_path)
    users.ensure_users_table(conn)
    users.create_user(conn, "admin@example.com", "adminpassword", role="admin")
    users.create_user(conn, "instructor@example.com", "instrpassword", role="instructor")
    users.create_user(conn, "viewer@example.com", "viewerpassword", role="viewer")
    conn.close()

    limiter.reset()
    from provectus_analytics.api import create_app
    app = create_app()
    yield app
    limiter.reset()


@pytest.fixture
def client(app_with_users):
    return TestClient(app_with_users)


def _token(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# --- permission matrix -----------------------------------------------------

def test_admin_can_list_users(client):
    tok = _token(client, "admin@example.com", "adminpassword")
    r = client.get("/api/users", headers=_auth(tok))
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert {"admin@example.com", "instructor@example.com", "viewer@example.com"} <= emails


@pytest.mark.parametrize("email,password", [
    ("viewer@example.com", "viewerpassword"),
    ("instructor@example.com", "instrpassword"),
])
def test_non_admin_cannot_list_or_create_users(client, email, password):
    tok = _token(client, email, password)
    assert client.get("/api/users", headers=_auth(tok)).status_code == 403
    r = client.post("/api/users", headers=_auth(tok),
                    json={"email": "new@example.com", "password": "newpassword", "role": "viewer"})
    assert r.status_code == 403


def test_non_admin_blocked_from_flights(client):
    tok = _token(client, "viewer@example.com", "viewerpassword")
    assert client.get("/api/flights", headers=_auth(tok)).status_code == 403


def test_non_admin_blocked_from_upload(client):
    tok = _token(client, "viewer@example.com", "viewerpassword")
    # POST is the only method; the router-level admin dependency rejects with
    # 403 before the handler's body validation runs.
    r = client.post("/api/upload/fsp", headers=_auth(tok))
    assert r.status_code == 403


def test_viewer_can_read_dashboards(client):
    tok = _token(client, "viewer@example.com", "viewerpassword")
    assert client.get("/api/kpis?range=12mo", headers=_auth(tok)).status_code == 200


# --- create / update -------------------------------------------------------

def test_admin_creates_user_with_role(client):
    tok = _token(client, "admin@example.com", "adminpassword")
    r = client.post("/api/users", headers=_auth(tok),
                    json={"email": "newinstr@example.com", "password": "newpassword", "role": "instructor"})
    assert r.status_code == 201
    assert r.json()["role"] == "instructor"
    # the new user can log in
    assert _token(client, "newinstr@example.com", "newpassword")


def test_create_duplicate_email_409(client):
    tok = _token(client, "admin@example.com", "adminpassword")
    r = client.post("/api/users", headers=_auth(tok),
                    json={"email": "viewer@example.com", "password": "anotherpassword", "role": "viewer"})
    assert r.status_code == 409


def test_create_weak_password_422(client):
    tok = _token(client, "admin@example.com", "adminpassword")
    r = client.post("/api/users", headers=_auth(tok),
                    json={"email": "weak@example.com", "password": "short", "role": "viewer"})
    assert r.status_code == 422


def test_create_invalid_role_422(client):
    tok = _token(client, "admin@example.com", "adminpassword")
    r = client.post("/api/users", headers=_auth(tok),
                    json={"email": "bad@example.com", "password": "goodpassword", "role": "superuser"})
    assert r.status_code == 422


def test_admin_updates_role_and_deactivates(client):
    tok = _token(client, "admin@example.com", "adminpassword")
    listing = client.get("/api/users", headers=_auth(tok)).json()
    viewer_id = next(u["user_id"] for u in listing if u["email"] == "viewer@example.com")

    r = client.patch(f"/api/users/{viewer_id}", headers=_auth(tok), json={"role": "instructor"})
    assert r.status_code == 200 and r.json()["role"] == "instructor"

    r = client.patch(f"/api/users/{viewer_id}", headers=_auth(tok), json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    # deactivated user can no longer log in
    assert client.post("/api/auth/login",
                       json={"email": "viewer@example.com", "password": "viewerpassword"}).status_code == 401


# --- last-admin guard ------------------------------------------------------

def test_cannot_demote_or_deactivate_last_admin(client):
    tok = _token(client, "admin@example.com", "adminpassword")
    listing = client.get("/api/users", headers=_auth(tok)).json()
    admin_id = next(u["user_id"] for u in listing if u["email"] == "admin@example.com")

    assert client.patch(f"/api/users/{admin_id}", headers=_auth(tok),
                        json={"role": "viewer"}).status_code == 400
    assert client.patch(f"/api/users/{admin_id}", headers=_auth(tok),
                        json={"is_active": False}).status_code == 400


def test_patch_unknown_user_404(client):
    tok = _token(client, "admin@example.com", "adminpassword")
    assert client.patch("/api/users/9999", headers=_auth(tok),
                        json={"role": "viewer"}).status_code == 404


# --- change password -------------------------------------------------------

def test_change_own_password(client):
    tok = _token(client, "viewer@example.com", "viewerpassword")
    r = client.post("/api/auth/change-password", headers=_auth(tok),
                    json={"current_password": "viewerpassword", "new_password": "brandnewpassword"})
    assert r.status_code == 204
    # old password fails, new one works
    assert client.post("/api/auth/login",
                       json={"email": "viewer@example.com", "password": "viewerpassword"}).status_code == 401
    assert _token(client, "viewer@example.com", "brandnewpassword")


def test_change_password_wrong_current_400(client):
    tok = _token(client, "viewer@example.com", "viewerpassword")
    r = client.post("/api/auth/change-password", headers=_auth(tok),
                    json={"current_password": "wrongpassword", "new_password": "brandnewpassword"})
    assert r.status_code == 400


def test_change_password_requires_auth(client):
    r = client.post("/api/auth/change-password",
                    json={"current_password": "x", "new_password": "brandnewpassword"})
    assert r.status_code == 401


# --- legacy role migration -------------------------------------------------

def test_boss_role_migrates_to_admin(tmp_path):
    db_path = tmp_path / "legacy.db"
    conn = _db.connect(db_path)
    users.ensure_users_table(conn)
    # Simulate a pre-migration row by inserting role='boss' directly.
    conn.execute(
        "INSERT INTO users (email, hashed_password, is_active, role, created_at) "
        "VALUES ('owner@example.com', 'x', 1, 'boss', '2026-01-01T00:00:00+00:00')"
    )
    conn.commit()
    # Re-running ensure_users_table should fold 'boss' into 'admin'.
    users.ensure_users_table(conn)
    migrated = users.get_user_by_email(conn, "owner@example.com")
    conn.close()
    assert migrated is not None and migrated.role == "admin"
