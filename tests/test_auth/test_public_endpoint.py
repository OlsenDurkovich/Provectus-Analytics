"""The transparency endpoint must be reachable with NO auth (real client,
not the test_api auth bypass)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from provectus_analytics.api import queries as web_data


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "t.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    from provectus_analytics.api import create_app
    return TestClient(create_app())


def test_transparency_requires_no_auth(client):
    # No Authorization header at all — must still return data.
    r = client.get("/api/public/transparency")
    assert r.status_code == 200
    assert "ratings" in r.json()


def test_protected_route_still_requires_auth(client):
    # Sanity: a normal data route still 401s without a token, proving the
    # public endpoint's openness isn't a blanket auth bypass.
    assert client.get("/api/kpis?range=12mo").status_code == 401
