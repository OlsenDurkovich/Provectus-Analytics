from fastapi.testclient import TestClient

from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data


def _fresh(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app())


def test_kpis_returns_four_cards(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    response = client.get("/api/kpis?range=12mo")
    assert response.status_code == 200
    kpis = response.json()
    assert len(kpis) == 4
    keys = {k["key"] for k in kpis}
    assert keys == {"ratings_completed", "active_clients", "flight_hours", "total_billed"}
    for k in kpis:
        assert "value" in k and "spark" in k and isinstance(k["spark"], list)
        assert k["delta"] == 0.0  # 0% placeholder until prior-period math lands


def test_kpis_range_all(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    response = client.get("/api/kpis?range=all")
    assert response.status_code == 200
    kpis = response.json()
    assert len(kpis) == 4
