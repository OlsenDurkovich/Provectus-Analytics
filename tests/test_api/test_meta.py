from fastapi.testclient import TestClient

from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data


def _fresh_synthetic(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app())


def test_meta_returns_synthetic_when_no_real_exports(tmp_path, monkeypatch):
    client = _fresh_synthetic(tmp_path, monkeypatch)
    response = client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "synthetic"
    assert body["liveClientCount"] == 0
    assert body["dataState"]["flights"] > 0
    assert "overrides" in body["dataState"]
