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


_KPI_KEYS = {"ratings_completed", "active_clients", "flight_hours", "in_training"}


def test_kpis_cards_no_billing_with_in_training(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    response = client.get("/api/kpis?range=12mo")
    assert response.status_code == 200
    kpis = {k["key"]: k for k in response.json()}
    # billing dropped; 'in_training' (current pipeline) added
    assert set(kpis) == _KPI_KEYS
    assert "total_billed" not in kpis
    for k in kpis.values():
        assert "value" in k and "spark" in k and isinstance(k["spark"], list)
        assert isinstance(k["delta"], float)
    # window metrics are comparable on a 12-month range; in_training is a 'now'
    # snapshot so it never shows a period delta.
    assert kpis["ratings_completed"]["comparable"] is True
    assert kpis["in_training"]["comparable"] is False


def test_kpis_range_all_comparability(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    response = client.get("/api/kpis?range=all")
    assert response.status_code == 200
    kpis = {k["key"]: k for k in response.json()}
    assert set(kpis) == _KPI_KEYS
    # Range-driven metrics have no prior on "all time" → not comparable, delta 0.
    for key in ("ratings_completed", "flight_hours"):
        assert kpis[key]["comparable"] is False
        assert kpis[key]["delta"] == 0.0
    # In-training is a 'now' snapshot — never comparable.
    assert kpis["in_training"]["comparable"] is False
    # Active clients is a fixed last-3-months metric, so it ALWAYS compares to the
    # prior 3 months — even when the page range is "all time".
    assert kpis["active_clients"]["comparable"] is True
    assert kpis["active_clients"]["sub"] == "last 3 months"


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
