from fastapi.testclient import TestClient

from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data


def _fresh(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app())


def test_flights_list(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/flights")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert rows, "synthetic build should produce flights"
    first = rows[0]
    assert {"id", "date", "client", "instructor", "type", "billing", "acClass", "ground", "hours", "cost"} <= first.keys()


def test_flights_filter_ground(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    flights_only = c.get("/api/flights", params={"ground": "Flight (0)"}).json()
    ground_only = c.get("/api/flights", params={"ground": "Ground (1)"}).json()
    assert all(r["ground"] == "Flight (0)" for r in flights_only)
    assert all(r["ground"] == "Ground (1)" for r in ground_only)


def test_flights_sort_asc(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    desc = c.get("/api/flights", params={"sort": "-date"}).json()
    asc = c.get("/api/flights", params={"sort": "date"}).json()
    if len(desc) >= 2:
        assert desc[0]["date"] >= desc[-1]["date"]
    if len(asc) >= 2:
        assert asc[0]["date"] <= asc[-1]["date"]
