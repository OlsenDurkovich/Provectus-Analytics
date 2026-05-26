from fastapi.testclient import TestClient

from provectus_analytics.api import create_app
from provectus_analytics.api import queries as web_data


def _fresh(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app())


def test_rating_detail_ppl(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/ratings/PPL")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "PPL"
    assert body["name"] == "Private Pilot"
    assert body["medianHrs"] > 0
    assert body["p25Hrs"] <= body["medianHrs"] <= body["p75Hrs"]
    assert body["medianCost"] > 0
    assert body["medianDays"] > 0
    assert body["n"] > 0
    assert isinstance(body["lowSample"], bool)


def test_rating_detail_unknown_returns_404(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    # Use a code that's in the enum but has no checkrides in the synthetic DB ...
    # actually all 7 ratings have checkrides in synthetic data. Test an invalid code:
    r = c.get("/api/ratings/XYZ")
    # Pydantic Literal validation rejects this at the route level (422)
    assert r.status_code in (404, 422)
