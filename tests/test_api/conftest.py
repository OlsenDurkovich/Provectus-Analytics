"""Bypass auth for /api/* tests via FastAPI dependency_overrides.

The existing test suite predates Phase 11 auth and was written assuming
every endpoint is public. Rather than thread bearer tokens through every
test, we wrap fastapi.testclient.TestClient so that whatever app it's
constructed with gets the auth dependency overridden in place.

Dedicated auth tests live in tests/test_auth/ — they use the real
TestClient via direct import.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient as _RealTestClient
from starlette.testclient import TestClient as _StarletteTestClient

from provectus_analytics.auth import deps as auth_deps
from provectus_analytics.auth.users import User


_FAKE_ADMIN = User(user_id=1, email="test@example.com",
                   is_active=True, role="admin")


@pytest.fixture(autouse=True)
def _bypass_auth(monkeypatch):
    """Patch TestClient so any app it wraps gets the auth dep overridden."""
    real_init = _RealTestClient.__init__

    def patched_init(self, app, *args, **kwargs):
        if hasattr(app, "dependency_overrides"):
            app.dependency_overrides[auth_deps.current_active_user] = lambda: _FAKE_ADMIN
            app.dependency_overrides[auth_deps.current_admin_user] = lambda: _FAKE_ADMIN
        real_init(self, app, *args, **kwargs)

    monkeypatch.setattr(_RealTestClient, "__init__", patched_init)
    # FastAPI's TestClient is re-exported from starlette; both classes show up
    # depending on import path. Patch starlette's too for safety.
    if _StarletteTestClient is not _RealTestClient:
        monkeypatch.setattr(_StarletteTestClient, "__init__", patched_init)
    yield
