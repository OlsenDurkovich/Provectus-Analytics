"""Instructor role: an account scoped to its own students' progress (no cost).

Covers the link model, the locked-down /api/me/students endpoint, the cost
omission, and that the empty page set blocks every internal endpoint.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from provectus_analytics import db as _db
from provectus_analytics.api import queries as web_data
from provectus_analytics.auth import users
from provectus_analytics.auth.rate_limit import limiter


@pytest.fixture
def env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()

    monkeypatch.setattr(users, "AUTH_DB", tmp_path / "auth.db")
    ac = users.connect()
    users.create_user(ac, "admin@example.com", "adminpassword", role="admin")
    ac.close()
    conn = _db.connect(db_path)
    # An instructor name with students, to link against.
    name = conn.execute(
        "SELECT instructor FROM flights WHERE instructor != '' "
        "GROUP BY instructor ORDER BY COUNT(DISTINCT student_id) DESC LIMIT 1"
    ).fetchone()[0]
    conn.close()

    limiter.reset()
    from provectus_analytics.api import create_app
    app = create_app()
    yield app, name
    limiter.reset()


@pytest.fixture
def client(env):
    return TestClient(env[0])


@pytest.fixture
def instructor_name(env):
    return env[1]


def _tok(client, email, pw):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _make_instructor(client, admin, name, email="cfi@example.com"):
    r = client.post(
        "/api/users", headers=_h(admin),
        json={"email": email, "password": "instructpass1", "role": "instructor", "instructor_name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- model / creation ------------------------------------------------------

def test_instructor_defaults_to_no_pages_and_carries_link(client, instructor_name):
    admin = _tok(client, "admin@example.com", "adminpassword")
    body = _make_instructor(client, admin, instructor_name)
    assert body["role"] == "instructor"
    assert body["pages"] == []
    assert body["instructor_name"] == instructor_name
    assert body["is_admin"] is False


def test_creating_instructor_without_link_is_rejected(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    r = client.post(
        "/api/users", headers=_h(admin),
        json={"email": "nolink@example.com", "password": "instructpass1", "role": "instructor"},
    )
    assert r.status_code == 422


def test_creating_instructor_with_bad_link_is_rejected(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    r = client.post(
        "/api/users", headers=_h(admin),
        json={"email": "bad@example.com", "password": "instructpass1",
              "role": "instructor", "instructor_name": "Nobody McGhost"},
    )
    assert r.status_code == 422


# --- /me + /api/me/students (cost-free) ------------------------------------

def test_instructor_me_and_roster(client, instructor_name):
    admin = _tok(client, "admin@example.com", "adminpassword")
    _make_instructor(client, admin, instructor_name)
    tok = _tok(client, "cfi@example.com", "instructpass1")

    me = client.get("/api/auth/me", headers=_h(tok)).json()
    assert me["role"] == "instructor" and me["instructor_name"] == instructor_name and me["pages"] == []

    r = client.get("/api/me/students", headers=_h(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["instructor_name"] == instructor_name
    assert len(body["students"]) > 0


def test_roster_omits_cost(client, instructor_name):
    admin = _tok(client, "admin@example.com", "adminpassword")
    _make_instructor(client, admin, instructor_name)
    tok = _tok(client, "cfi@example.com", "instructpass1")
    body = client.get("/api/me/students", headers=_h(tok)).json()
    # No cost field anywhere in the payload the instructor receives.
    assert all("costToDate" not in s for s in body["students"])
    assert all("avgCost" not in r for r in body["perRating"])


def test_roster_endpoint_rejects_non_instructors(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    assert client.get("/api/me/students", headers=_h(admin)).status_code == 403


# --- the empty page set blocks every internal endpoint ---------------------

def test_instructor_is_blocked_from_all_internal_endpoints(client, instructor_name):
    admin = _tok(client, "admin@example.com", "adminpassword")
    _make_instructor(client, admin, instructor_name)
    tok = _tok(client, "cfi@example.com", "instructpass1")

    assert client.get("/api/kpis?range=12mo", headers=_h(tok)).status_code == 403
    assert client.get("/api/students?range=12mo", headers=_h(tok)).status_code == 403
    assert client.get("/api/instructors", headers=_h(tok)).status_code == 403
    assert client.get("/api/ratings/PPL", headers=_h(tok)).status_code == 403
    assert client.get("/api/users", headers=_h(tok)).status_code == 403
    # student endpoint is closed to instructors too
    assert client.get("/api/me/training", headers=_h(tok)).status_code == 403
    # meta stays open (shell)
    assert client.get("/api/meta", headers=_h(tok)).status_code == 200


# --- admin linking flows ---------------------------------------------------

def test_admin_lists_instructor_records(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    r = client.get("/api/users/instructor-records", headers=_h(admin))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0 and "name" in rows[0] and "students" in rows[0]


def test_promote_viewer_to_instructor_then_link(client, instructor_name):
    admin = _tok(client, "admin@example.com", "adminpassword")
    created = client.post(
        "/api/users", headers=_h(admin),
        json={"email": "later@example.com", "password": "viewerpass1", "role": "viewer"},
    ).json()
    uid = created["user_id"]
    r = client.patch(
        f"/api/users/{uid}", headers=_h(admin),
        json={"role": "instructor", "instructor_name": instructor_name},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "instructor" and r.json()["instructor_name"] == instructor_name
    assert r.json()["pages"] == []


def test_switching_instructor_back_to_viewer_clears_link(client, instructor_name):
    admin = _tok(client, "admin@example.com", "adminpassword")
    ins = _make_instructor(client, admin, instructor_name)
    r = client.patch(f"/api/users/{ins['user_id']}", headers=_h(admin), json={"role": "viewer"})
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"
    assert r.json()["instructor_name"] is None
    assert sorted(r.json()["pages"]) == sorted(["overview", "ratings", "students", "instructors"])
