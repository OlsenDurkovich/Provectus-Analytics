"""User CRUD + auth flow against a fresh SQLite DB."""
from __future__ import annotations

import sqlite3

import pytest

from provectus_analytics.auth import users


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "auth.db"
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    users.ensure_users_table(c)
    yield c
    c.close()


def test_create_then_get_by_email(conn):
    u = users.create_user(conn, "Test@Example.COM", "supersecure", role="admin")
    fetched = users.get_user_by_email(conn, "test@example.com")
    assert fetched is not None
    assert fetched.user_id == u.user_id
    assert fetched.email == "test@example.com"  # lower-cased
    assert fetched.role == "admin"
    assert fetched.is_active


def test_create_duplicate_raises(conn):
    users.create_user(conn, "x@y.com", "password")
    with pytest.raises(ValueError, match="already exists"):
        users.create_user(conn, "X@Y.COM", "password")


def test_password_too_short_raises(conn):
    with pytest.raises(ValueError, match="8 characters"):
        users.create_user(conn, "x@y.com", "short")


def test_invalid_email_raises(conn):
    with pytest.raises(ValueError, match="valid address"):
        users.create_user(conn, "not-an-email", "longenough")


def test_authenticate_success(conn):
    u = users.create_user(conn, "a@b.com", "rightpassword")
    assert users.authenticate(conn, "a@b.com", "rightpassword").user_id == u.user_id


def test_authenticate_wrong_password(conn):
    users.create_user(conn, "a@b.com", "rightpassword")
    assert users.authenticate(conn, "a@b.com", "wrongpassword") is None


def test_authenticate_missing_user(conn):
    assert users.authenticate(conn, "nobody@nowhere.com", "anything") is None


def test_authenticate_inactive_user(conn):
    users.create_user(conn, "a@b.com", "rightpassword", is_active=False)
    assert users.authenticate(conn, "a@b.com", "rightpassword") is None


def test_seed_initial_admin_on_empty_db(conn):
    u = users.seed_initial_admin(conn, "admin@p.com", "verysecure")
    assert u is not None
    assert u.role == "admin"
    assert users.count_users(conn) == 1


def test_seed_initial_admin_skips_when_users_exist(conn):
    users.create_user(conn, "existing@x.com", "longenough")
    u = users.seed_initial_admin(conn, "admin@p.com", "verysecure")
    assert u is None
    assert users.count_users(conn) == 1


def test_seed_initial_admin_skips_when_creds_missing(conn):
    assert users.seed_initial_admin(conn, None, None) is None
    assert users.seed_initial_admin(conn, "x@y.com", None) is None
    assert users.count_users(conn) == 0
