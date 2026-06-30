"""Student role: an account scoped to one person's own training data.

Covers the link model, the locked-down /api/me/training endpoint, and that the
empty page set blocks every internal endpoint for a student.
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
    # A real student_id from the synthetic data to link against.
    sid = conn.execute("SELECT student_id FROM students ORDER BY student_id LIMIT 1").fetchone()[0]
    conn.close()

    limiter.reset()
    from provectus_analytics.api import create_app
    app = create_app()
    yield app, sid
    limiter.reset()


@pytest.fixture
def client(env):
    return TestClient(env[0])


@pytest.fixture
def student_id(env):
    return env[1]


def _tok(client, email, pw):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _make_student(client, admin, student_id, email="kid@example.com"):
    r = client.post(
        "/api/users", headers=_h(admin),
        json={"email": email, "password": "studentpass1", "role": "student", "student_id": student_id},
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- model / creation ------------------------------------------------------

def test_student_defaults_to_no_pages_and_carries_link(client, student_id):
    admin = _tok(client, "admin@example.com", "adminpassword")
    body = _make_student(client, admin, student_id)
    assert body["role"] == "student"
    assert body["pages"] == []
    assert body["student_id"] == student_id
    assert body["is_admin"] is False


def test_creating_student_without_link_is_rejected(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    r = client.post(
        "/api/users", headers=_h(admin),
        json={"email": "nolink@example.com", "password": "studentpass1", "role": "student"},
    )
    assert r.status_code == 422


def test_creating_student_with_bad_link_is_rejected(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    r = client.post(
        "/api/users", headers=_h(admin),
        json={"email": "bad@example.com", "password": "studentpass1", "role": "student", "student_id": 999999},
    )
    assert r.status_code == 422


# --- /me + /api/me/training ------------------------------------------------

def test_student_me_and_training(client, student_id):
    admin = _tok(client, "admin@example.com", "adminpassword")
    _make_student(client, admin, student_id)
    tok = _tok(client, "kid@example.com", "studentpass1")

    me = client.get("/api/auth/me", headers=_h(tok)).json()
    assert me["role"] == "student" and me["student_id"] == student_id and me["pages"] == []

    r = client.get("/api/me/training", headers=_h(tok))
    assert r.status_code == 200
    assert str(r.json()["id"]) == str(student_id)


def test_training_endpoint_rejects_non_students(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    assert client.get("/api/me/training", headers=_h(admin)).status_code == 403


# --- the empty page set blocks every internal endpoint ---------------------

def test_student_is_blocked_from_all_internal_endpoints(client, student_id):
    admin = _tok(client, "admin@example.com", "adminpassword")
    _make_student(client, admin, student_id)
    tok = _tok(client, "kid@example.com", "studentpass1")

    assert client.get("/api/kpis?range=12mo", headers=_h(tok)).status_code == 403
    assert client.get("/api/students?range=12mo", headers=_h(tok)).status_code == 403
    assert client.get(f"/api/students/{student_id}", headers=_h(tok)).status_code == 403
    assert client.get("/api/instructors", headers=_h(tok)).status_code == 403
    assert client.get("/api/ratings/PPL", headers=_h(tok)).status_code == 403
    # admin-only user management is also closed to them
    assert client.get("/api/users", headers=_h(tok)).status_code == 403
    # meta stays open (the shell needs it)
    assert client.get("/api/meta", headers=_h(tok)).status_code == 200


# --- admin linking flows ---------------------------------------------------

def test_admin_lists_student_records(client):
    admin = _tok(client, "admin@example.com", "adminpassword")
    r = client.get("/api/users/student-records", headers=_h(admin))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0 and "student_id" in rows[0] and "name" in rows[0]


def test_promote_viewer_to_student_then_link(client, student_id):
    admin = _tok(client, "admin@example.com", "adminpassword")
    created = client.post(
        "/api/users", headers=_h(admin),
        json={"email": "later@example.com", "password": "viewerpass1", "role": "viewer"},
    ).json()
    uid = created["user_id"]
    # role + link in one PATCH
    r = client.patch(
        f"/api/users/{uid}", headers=_h(admin),
        json={"role": "student", "student_id": student_id},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "student" and r.json()["student_id"] == student_id and r.json()["pages"] == []


def test_switching_student_back_to_viewer_clears_link(client, student_id):
    admin = _tok(client, "admin@example.com", "adminpassword")
    s = _make_student(client, admin, student_id)
    r = client.patch(f"/api/users/{s['user_id']}", headers=_h(admin), json={"role": "viewer"})
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"
    assert r.json()["student_id"] is None
    assert sorted(r.json()["pages"]) == sorted(["overview", "ratings", "students", "instructors", "insights"])


def test_relink_existing_student_to_different_record(client, student_id):
    admin = _tok(client, "admin@example.com", "adminpassword")
    s = _make_student(client, admin, student_id)
    conn = _db.connect(web_data.DEFAULT_DB)
    other = conn.execute(
        "SELECT student_id FROM students WHERE student_id != ? ORDER BY student_id LIMIT 1",
        (student_id,),
    ).fetchone()[0]
    conn.close()
    r = client.patch(f"/api/users/{s['user_id']}", headers=_h(admin), json={"student_id": other})
    assert r.status_code == 200 and r.json()["student_id"] == other
