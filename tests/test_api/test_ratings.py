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


def test_rating_bars_one_row_per_rating(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    r = client.get("/api/ratings?metric=hours&range=all")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0
    assert {row["code"] for row in rows} <= {"PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"}
    for row in rows:
        assert row["median"] >= 0
        assert row["p25"] <= row["median"] <= row["p75"]
        assert row["n"] > 0


def test_rating_bars_cost_metric(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    r = client.get("/api/ratings?metric=cost&range=all")
    assert r.status_code == 200
    rows = r.json()
    for row in rows:
        assert row["median"] >= 0


def test_ratings_completed_shape(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    r = client.get("/api/ratings/completed?range=all")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    for row in rows:
        assert row["rating"] in {"PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"}
        assert row["count"] >= 1


def test_heatmap_returns_7x12_matrix(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    r = client.get("/api/heatmap?range=all")
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) == 7
    assert all(len(row) == 12 for row in body["rows"])
    assert len(body["buckets"]) == 12
