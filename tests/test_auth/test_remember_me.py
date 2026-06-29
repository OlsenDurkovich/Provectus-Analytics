"""'Remember me': longer-lived refresh token, preserved across silent refresh."""
from __future__ import annotations

import jwt
import pytest
from fastapi.testclient import TestClient

from provectus_analytics import db as _db
from provectus_analytics.api import queries as web_data
from provectus_analytics.auth import tokens, users
from provectus_analytics.auth.config import settings
from provectus_analytics.auth.rate_limit import limiter


def _life_days(token: str) -> float:
    p = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    return (p["exp"] - p["iat"]) / 86400.0


# --- token unit tests ------------------------------------------------------

def test_remember_token_is_long_lived_and_carries_claim():
    short = tokens.make_refresh_token(1)
    long = tokens.make_refresh_token(1, remember=True)
    assert round(_life_days(short)) == settings.refresh_token_days
    assert round(_life_days(long)) == settings.refresh_token_long_days
    assert tokens.refresh_token_remember(long) is True
    assert tokens.refresh_token_remember(short) is False


# --- endpoint tests --------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    monkeypatch.setattr(users, "AUTH_DB", tmp_path / "auth.db")
    conn = users.connect()
    users.create_user(conn, "a@example.com", "passwordzz", role="admin")
    conn.close()
    limiter.reset()
    from provectus_analytics.api import create_app
    c = TestClient(create_app())
    yield c
    limiter.reset()


def _login(client, remember):
    r = client.post("/api/auth/login",
                    json={"email": "a@example.com", "password": "passwordzz", "remember": remember})
    assert r.status_code == 200, r.text
    return r.json()


def test_login_default_is_short_session(client):
    body = _login(client, remember=False)
    assert round(_life_days(body["refresh_token"])) == settings.refresh_token_days


def test_login_remember_is_long_session(client):
    body = _login(client, remember=True)
    assert round(_life_days(body["refresh_token"])) == settings.refresh_token_long_days


def test_login_without_remember_field_defaults_off(client):
    # Older clients that don't send the field still work (defaults to short).
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "passwordzz"})
    assert r.status_code == 200
    assert round(_life_days(r.json()["refresh_token"])) == settings.refresh_token_days


def test_refresh_preserves_remember_lifetime(client):
    body = _login(client, remember=True)
    r = client.post("/api/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert r.status_code == 200
    # The re-issued refresh token keeps the long lifetime, not the 7-day default.
    assert round(_life_days(r.json()["refresh_token"])) == settings.refresh_token_long_days


def test_refresh_of_short_session_stays_short(client):
    body = _login(client, remember=False)
    r = client.post("/api/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert r.status_code == 200
    assert round(_life_days(r.json()["refresh_token"])) == settings.refresh_token_days
