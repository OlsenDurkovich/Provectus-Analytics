"""Per-user page access: presets, /me, server-side gating, admin reset."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from provectus_analytics import db as _db
from provectus_analytics.api import queries as web_data
from provectus_analytics.auth import users
from provectus_analytics.auth.rate_limit import limiter

ALL_PAGES = ["overview", "ratings", "students", "instructors"]


@pytest.fixture
def app_with_users(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()

    monkeypatch.setattr(users, "AUTH_DB", tmp_path / "auth.db")
    conn = users.connect()
    users.create_user(conn, "admin@example.com", "adminpassword", role="admin")
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


def _tok(client, email, pw):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _viewer_id(client, admin_tok):
    listing = client.get("/api/users", headers=_h(admin_tok)).json()
    return next(u["user_id"] for u in listing if u["email"] == "viewer@example.com")


# --- defaults + /me --------------------------------------------------------

def test_new_user_gets_all_pages_by_default(client):
    tok = _tok(client, "viewer@example.com", "viewerpassword")
    me = client.get("/api/auth/me", headers=_h(tok)).json()
    assert sorted(me["pages"]) == sorted(ALL_PAGES)
    assert me["is_admin"] is False


def test_admin_me_is_admin(client):
    tok = _tok(client, "admin@example.com", "adminpassword")
    assert client.get("/api/auth/me", headers=_h(tok)).json()["is_admin"] is True


# --- admin edits pages; gating is enforced server-side ---------------------

def test_admin_sets_pages_and_api_enforces_them(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    vid = _viewer_id(client, admin)

    r = client.patch(f"/api/users/{vid}", headers=_h(admin), json={"pages": ["overview"]})
    assert r.status_code == 200 and r.json()["pages"] == ["overview"]

    viewer = _tok(client, "viewer@example.com", "viewerpassword")
    # has overview → kpis + clients allowed
    assert client.get("/api/kpis?range=12mo", headers=_h(viewer)).status_code == 200
    assert client.get("/api/students?range=12mo", headers=_h(viewer)).status_code == 200
    # lacks instructors + students-detail + rating-detail → 403
    assert client.get("/api/instructors", headers=_h(viewer)).status_code == 403
    assert client.get("/api/students/anyid", headers=_h(viewer)).status_code == 403
    assert client.get("/api/ratings/PPL", headers=_h(viewer)).status_code == 403
    # admin still reaches everything (bypass)
    assert client.get("/api/instructors", headers=_h(admin)).status_code == 200


def test_viewer_with_no_pages_is_blocked(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    vid = _viewer_id(client, admin)
    client.patch(f"/api/users/{vid}", headers=_h(admin), json={"pages": []})
    viewer = _tok(client, "viewer@example.com", "viewerpassword")
    assert client.get("/api/kpis?range=12mo", headers=_h(viewer)).status_code == 403
    # meta stays open (the shell needs it)
    assert client.get("/api/meta", headers=_h(viewer)).status_code == 200


def test_setting_role_reapplies_page_preset(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    vid = _viewer_id(client, admin)
    client.patch(f"/api/users/{vid}", headers=_h(admin), json={"pages": ["overview"]})
    # Re-applying a full-access role (viewer) restores every page.
    r = client.patch(f"/api/users/{vid}", headers=_h(admin), json={"role": "viewer"})
    assert r.status_code == 200
    assert sorted(r.json()["pages"]) == sorted(ALL_PAGES)
    # A scoped role (instructor) re-applies to NO dashboard pages.
    r = client.patch(f"/api/users/{vid}", headers=_h(admin), json={"role": "instructor"})
    assert r.status_code == 200 and r.json()["pages"] == []


def test_invalid_page_rejected(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    vid = _viewer_id(client, admin)
    r = client.patch(f"/api/users/{vid}", headers=_h(admin), json={"pages": ["bogus"]})
    assert r.status_code == 400


# --- admin password reset --------------------------------------------------

def test_admin_resets_password(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    vid = _viewer_id(client, admin)
    r = client.patch(f"/api/users/{vid}", headers=_h(admin), json={"new_password": "resetpassword1"})
    assert r.status_code == 200
    # old fails, new works
    assert client.post("/api/auth/login",
                       json={"email": "viewer@example.com", "password": "viewerpassword"}).status_code == 401
    assert _tok(client, "viewer@example.com", "resetpassword1")


def test_admin_reset_password_too_short_400(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    vid = _viewer_id(client, admin)
    r = client.patch(f"/api/users/{vid}", headers=_h(admin), json={"new_password": "short"})
    assert r.status_code == 400


def test_pages_gating_is_not_an_auth_bypass(client):
    # No token at all → 401 (page gate sits on top of auth, not instead of it).
    assert client.get("/api/kpis?range=12mo").status_code == 401
