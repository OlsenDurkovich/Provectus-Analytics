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


def test_instructors_list(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/instructors")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    if rows:
        first = rows[0]
        assert {"id", "name", "hours", "students", "passRate"} <= first.keys()


def test_instructor_detail(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    rows = c.get("/api/instructors").json()
    if not rows:
        return
    iid = rows[0]["id"]
    r = c.get(f"/api/instructors/{iid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == iid


def test_instructor_detail_unknown_returns_404(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/instructors/does-not-exist")
    assert r.status_code == 404
