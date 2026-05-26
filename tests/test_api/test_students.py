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


def test_students_returns_rows(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/students?range=all")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0
    row = rows[0]
    assert {
        "id", "name", "rating", "progressPct", "hoursToDate", "daysEnrolled", "status",
    } <= row.keys()
    assert row["status"] in {"Active", "On checkride", "Completed"}
    assert row["rating"] in {"PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"}
    assert row["hoursToDate"] >= 0
    assert 0 <= row["progressPct"] <= 1.5  # progress can exceed 1 if student passed norm


def test_students_filtered_by_rating(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/students?range=all&rating=PPL")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0
    assert all(row["rating"] == "PPL" for row in rows)
