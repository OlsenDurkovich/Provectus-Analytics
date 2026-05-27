"""Phase 14 — security headers + CORS configuration."""
from __future__ import annotations

import os
from importlib import reload

from fastapi.testclient import TestClient


def _fresh_app(monkeypatch, **env: str):
    """Build a fresh app honoring the given env vars."""
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    # Reload the auth config + main so settings re-read the env.
    from provectus_analytics.auth import config as auth_config
    reload(auth_config)
    from provectus_analytics.api import main as main_mod
    reload(main_mod)
    return TestClient(main_mod.create_app())


def test_healthz_response_carries_security_headers(monkeypatch):
    client = _fresh_app(monkeypatch)
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "same-origin"
    assert "Permissions-Policy" in r.headers
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_hsts_off_in_dev(monkeypatch):
    monkeypatch.setenv("PROVECTUS_ENV", "dev")
    client = _fresh_app(monkeypatch)
    r = client.get("/api/healthz")
    assert "Strict-Transport-Security" not in r.headers


def test_hsts_on_in_prod(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("PROVECTUS_ENV", "prod")
    client = _fresh_app(monkeypatch)
    r = client.get("/api/healthz")
    assert "Strict-Transport-Security" in r.headers
    assert "max-age=" in r.headers["Strict-Transport-Security"]


def test_cors_allowed_in_dev_for_vite_origin(monkeypatch):
    client = _fresh_app(monkeypatch, PROVECTUS_ENV="dev")
    r = client.options(
        "/api/healthz",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Either 200 OK or 400 — depends on slowapi/middleware order. What
    # matters is the access-control header reflects the origin.
    assert r.headers.get("access-control-allow-origin") in {
        "http://localhost:5173", "*",
    }


def test_cors_locked_down_in_prod_by_default(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("PROVECTUS_ENV", "prod")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    client = _fresh_app(monkeypatch)
    r = client.options(
        "/api/healthz",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # No CORS middleware mounted when allowlist is empty → no
    # access-control-allow-origin reflected back.
    assert r.headers.get("access-control-allow-origin") is None


def test_cors_explicit_origin_honored_in_prod(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("PROVECTUS_ENV", "prod")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://analytics.provectusaviation.com",
    )
    client = _fresh_app(monkeypatch)
    r = client.options(
        "/api/healthz",
        headers={
            "Origin": "https://analytics.provectusaviation.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "https://analytics.provectusaviation.com"
