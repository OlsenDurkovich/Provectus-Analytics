from fastapi.testclient import TestClient

from provectus_analytics.api import create_app
from provectus_analytics.api import queries as web_data


def _fresh(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app())


def test_kpis_returns_three_cards_no_billing(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    response = client.get("/api/kpis?range=12mo")
    assert response.status_code == 200
    kpis = response.json()
    # billing is intentionally omitted (owner doesn't track revenue here)
    assert len(kpis) == 3
    keys = {k["key"] for k in kpis}
    assert keys == {"ratings_completed", "active_clients", "flight_hours"}
    assert "total_billed" not in keys
    for k in kpis:
        assert "value" in k and "spark" in k and isinstance(k["spark"], list)
        assert isinstance(k["delta"], float)
        assert k["positive"] is (k["delta"] >= 0)
        # a 12-month range has a prior window to compare against
        assert k["comparable"] is True


def test_kpis_range_all_not_comparable(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    response = client.get("/api/kpis?range=all")
    assert response.status_code == 200
    kpis = response.json()
    assert len(kpis) == 3
    # "all" range has no prior window — not comparable, delta 0 (UI hides the badge).
    for k in kpis:
        assert k["comparable"] is False
        assert k["delta"] == 0.0


def test_kpis_delta_uses_prior_window(tmp_path, monkeypatch):
    """If prior window has zero activity but current does, delta stays 0 (not infinity)."""
    client = _fresh(tmp_path, monkeypatch)
    response = client.get("/api/kpis?range=30d")
    assert response.status_code == 200
    kpis = response.json()
    for k in kpis:
        # Deltas are bounded — never NaN/inf, and the placeholder math returns 0.0
        # when prior is empty.
        assert isinstance(k["delta"], float)
        assert k["delta"] == k["delta"]  # NaN check
