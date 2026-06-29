"""Self-service account settings: display name, email, phone, theme + admin edit."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from provectus_analytics import db as _db
from provectus_analytics.api import queries as web_data
from provectus_analytics.auth import users
from provectus_analytics.auth.rate_limit import limiter


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    conn = _db.connect(db_path)
    users.ensure_users_table(conn)
    users.create_user(conn, "admin@example.com", "adminpassword", role="admin")
    users.create_user(conn, "viewer@example.com", "viewerpassword", role="viewer")
    conn.close()
    limiter.reset()
    from provectus_analytics.api import create_app
    c = TestClient(create_app())
    yield c
    limiter.reset()


def _h(client, email, pw):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_defaults_are_null(client):
    me = client.get("/api/auth/me", headers=_h(client, "viewer@example.com", "viewerpassword")).json()
    assert me["display_name"] is None and me["phone"] is None and me["theme"] is None


def test_self_service_update_and_me_reflects(client):
    h = _h(client, "viewer@example.com", "viewerpassword")
    r = client.patch("/api/auth/me", headers=h,
                     json={"display_name": "Vicky Viewer", "phone": "555-1212", "theme": "light"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers=h).json()
    assert me["display_name"] == "Vicky Viewer"
    assert me["phone"] == "555-1212"
    assert me["theme"] == "light"


def test_partial_update_leaves_other_fields(client):
    h = _h(client, "viewer@example.com", "viewerpassword")
    client.patch("/api/auth/me", headers=h, json={"display_name": "Keep Me", "phone": "111"})
    client.patch("/api/auth/me", headers=h, json={"theme": "dark"})  # only theme
    me = client.get("/api/auth/me", headers=h).json()
    assert me["display_name"] == "Keep Me" and me["phone"] == "111" and me["theme"] == "dark"


def test_email_change(client):
    h = _h(client, "viewer@example.com", "viewerpassword")
    assert client.patch("/api/auth/me", headers=h, json={"email": "vicky@example.com"}).status_code == 200
    # new email logs in; old one doesn't
    assert client.post("/api/auth/login",
                       json={"email": "vicky@example.com", "password": "viewerpassword"}).status_code == 200
    assert client.post("/api/auth/login",
                       json={"email": "viewer@example.com", "password": "viewerpassword"}).status_code == 401


def test_email_collision_rejected(client):
    h = _h(client, "viewer@example.com", "viewerpassword")
    r = client.patch("/api/auth/me", headers=h, json={"email": "admin@example.com"})
    assert r.status_code == 400


def test_bad_theme_rejected(client):
    h = _h(client, "viewer@example.com", "viewerpassword")
    assert client.patch("/api/auth/me", headers=h, json={"theme": "neon"}).status_code == 400


def test_bad_email_rejected(client):
    h = _h(client, "viewer@example.com", "viewerpassword")
    assert client.patch("/api/auth/me", headers=h, json={"email": "not-an-email"}).status_code == 400


def test_admin_edits_another_users_profile(client):
    admin = _h(client, "admin@example.com", "adminpassword")
    vid = next(u["user_id"] for u in client.get("/api/users", headers=admin).json()
               if u["email"] == "viewer@example.com")
    r = client.patch(f"/api/users/{vid}", headers=admin,
                     json={"display_name": "Victoria V", "phone": "999"})
    assert r.status_code == 200
    assert r.json()["display_name"] == "Victoria V" and r.json()["phone"] == "999"
