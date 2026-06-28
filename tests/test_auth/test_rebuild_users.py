"""Rebuild DB safety: it must NOT wipe login accounts, and it's admin-only.

The synthetic rebuild path replaces the whole DB file, and logins live in the
same file — so build_db snapshots + restores the users table, and the /rebuild
and /import-fsp endpoints are gated to admins.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from provectus_analytics import db as _db
from provectus_analytics.api import queries as web_data
from provectus_analytics.auth import users
from provectus_analytics.auth.rate_limit import limiter


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    p = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", p)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(p, force_synthetic=True)
    web_data.clear_caches()
    conn = _db.connect(p)
    users.ensure_users_table(conn)
    users.create_user(conn, "admin@example.com", "adminpassword", role="admin")
    users.create_user(conn, "viewer@example.com", "viewerpassword", role="viewer")
    conn.close()
    return p


# --- preservation (unit, calls build_db directly) --------------------------

def test_synthetic_rebuild_preserves_accounts(db_path):
    before = {u.email: u.role for u in users.list_users(_db.connect(db_path))}
    assert before == {"admin@example.com": "admin", "viewer@example.com": "viewer"}

    # A rebuild that replaces the whole file...
    web_data.build_db(db_path, force_synthetic=True)

    conn = _db.connect(db_path)
    after = {u.email: u.role for u in users.list_users(conn)}
    assert after == before, "rebuild must not drop login accounts"
    # And the restored hash still authenticates (rows copied verbatim).
    assert users.authenticate(conn, "admin@example.com", "adminpassword") is not None
    conn.close()


def test_rebuild_with_no_prior_users_still_leaves_a_usable_table(tmp_path, monkeypatch):
    p = tmp_path / "fresh.db"
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(p, force_synthetic=True)  # never had a users table
    conn = _db.connect(p)
    # The table exists and a freshly created account works.
    users.ensure_users_table(conn)
    users.create_user(conn, "a@example.com", "passwordzz", role="admin")
    assert users.authenticate(conn, "a@example.com", "passwordzz") is not None
    conn.close()


# --- admin-only gating (API) -----------------------------------------------

@pytest.fixture
def client(db_path):
    limiter.reset()
    from provectus_analytics.api import create_app
    c = TestClient(create_app())
    yield c
    limiter.reset()


def _tok(client, email, pw):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_rebuild_endpoint_is_admin_only(client):
    viewer = _tok(client, "viewer@example.com", "viewerpassword")
    assert client.post("/api/rebuild?synthetic=true", headers=viewer).status_code == 403
    admin = _tok(client, "admin@example.com", "adminpassword")
    r = client.post("/api/rebuild?synthetic=true", headers=admin)
    assert r.status_code == 200 and r.json()["built"]["mode"] == "synthetic"
    # accounts survived the admin rebuild
    assert client.post(
        "/api/auth/login", json={"email": "viewer@example.com", "password": "viewerpassword"}
    ).status_code == 200


def test_import_fsp_endpoint_is_admin_only(client):
    viewer = _tok(client, "viewer@example.com", "viewerpassword")
    # The auth gate fires before any import work runs.
    assert client.post("/api/import-fsp", headers=viewer).status_code == 403


def test_meta_stays_open_to_any_authenticated_user(client):
    viewer = _tok(client, "viewer@example.com", "viewerpassword")
    assert client.get("/api/meta", headers=viewer).status_code == 200
