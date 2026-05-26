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


def test_student_detail(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    rows = c.get("/api/students?range=all").json()
    assert rows, "synthetic build should produce students"
    sid = rows[0]["id"]
    r = c.get(f"/api/students/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == sid
    assert "timeline" in body
    assert isinstance(body["timeline"], list)
    assert "perRating" in body


def test_student_detail_unknown_returns_404(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/students/does-not-exist")
    assert r.status_code == 404
