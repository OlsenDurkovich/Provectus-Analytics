"""Rebuild DB safety + DB compartmentalization.

User accounts now live in a DEDICATED auth DB (auth.users.AUTH_DB), separate
from the analytics DB. So an analytics rebuild physically cannot touch accounts.
This also covers: the rebuild is crash/corruption-safe (atomic swap), and the
/rebuild + /import-fsp endpoints are admin-only.
"""
from __future__ import annotations

import sqlite3

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
    monkeypatch.setattr(users, "AUTH_DB", tmp_path / "auth.db")
    web_data.build_db(p, force_synthetic=True)
    web_data.clear_caches()
    conn = users.connect()  # accounts go in the dedicated auth DB
    users.create_user(conn, "admin@example.com", "adminpassword", role="admin")
    users.create_user(conn, "viewer@example.com", "viewerpassword", role="viewer")
    conn.close()
    return p


# --- compartmentalization --------------------------------------------------

def test_accounts_live_in_separate_db_not_analytics(db_path):
    # The analytics DB must NOT carry a users table at all.
    adb = sqlite3.connect(db_path)
    assert adb.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone() is None
    adb.close()
    # The accounts exist in the auth DB.
    assert {u.email for u in users.list_users(users.connect())} == {
        "admin@example.com", "viewer@example.com"}


def test_analytics_rebuild_leaves_auth_accounts_untouched(db_path):
    before = {u.email: u.role for u in users.list_users(users.connect())}
    # Rebuild the analytics DB (the action that wiped accounts before the split).
    web_data.build_db(db_path, force_synthetic=True)
    conn = users.connect()
    after = {u.email: u.role for u in users.list_users(conn)}
    assert after == before
    assert users.authenticate(conn, "admin@example.com", "adminpassword") is not None
    conn.close()


def test_fresh_auth_db_is_usable(tmp_path, monkeypatch):
    monkeypatch.setattr(users, "AUTH_DB", tmp_path / "auth.db")
    conn = users.connect()  # creates + migrates the users table on first open
    users.create_user(conn, "a@example.com", "passwordzz", role="admin")
    assert users.authenticate(conn, "a@example.com", "passwordzz") is not None
    conn.close()


def test_legacy_users_migrate_into_auth_db(tmp_path, monkeypatch):
    """Existing deployments had users in the analytics DB; on first boot with the
    split, migrate_legacy_users copies them (incl. password hashes) to the auth DB."""
    legacy = tmp_path / "provectus.db"
    monkeypatch.setattr(users, "AUTH_DB", tmp_path / "auth.db")
    lc = _db.connect(legacy)
    users.ensure_users_table(lc)
    users.create_user(lc, "olsen@example.com", "passwordzz", role="admin")
    lc.close()

    ac = users.connect()  # fresh, empty auth DB
    assert users.migrate_legacy_users(ac, legacy) == 1
    assert users.authenticate(ac, "olsen@example.com", "passwordzz") is not None
    # Idempotent: a second run (auth DB already populated) is a no-op.
    assert users.migrate_legacy_users(ac, legacy) == 0
    ac.close()


# --- analytics rebuild is corruption-safe ----------------------------------

def test_rebuild_recovers_from_corrupt_db(tmp_path, monkeypatch):
    """A malformed analytics DB + stale WAL/SHM sidecars (the prod outage) must
    self-heal on the next build_db: no crash, a clean readable DB, sidecars gone."""
    p = tmp_path / "provectus.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", p)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    p.write_bytes(b"SQLite format 3\x00" + b"\xde\xad\xbe\xef" * 500)
    (tmp_path / "provectus.db-wal").write_bytes(b"stale-wal")
    (tmp_path / "provectus.db-shm").write_bytes(b"stale-shm")

    web_data.build_db(p, force_synthetic=True)  # must not raise

    conn = _db.connect(p)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0] > 0
    conn.close()
    assert not (tmp_path / "provectus.db-wal").exists() or \
        (tmp_path / "provectus.db-wal").stat().st_size == 0


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
    # accounts survive the admin rebuild (they're in the separate auth DB)
    assert client.post(
        "/api/auth/login", json={"email": "viewer@example.com", "password": "viewerpassword"}
    ).status_code == 200


def test_import_fsp_endpoint_is_admin_only(client):
    viewer = _tok(client, "viewer@example.com", "viewerpassword")
    assert client.post("/api/import-fsp", headers=viewer).status_code == 403


def test_meta_stays_open_to_any_authenticated_user(client):
    viewer = _tok(client, "viewer@example.com", "viewerpassword")
    assert client.get("/api/meta", headers=viewer).status_code == 200
