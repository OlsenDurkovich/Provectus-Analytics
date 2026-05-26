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


def test_instructor_detail_per_rating_shape(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    rows = c.get("/api/instructors").json()
    if not rows:
        return
    # Find an instructor whose detail has at least one perRating entry.
    target = None
    for row in rows:
        body = c.get(f"/api/instructors/{row['id']}").json()
        if body.get("perRating"):
            target = body
            break
    if target is None:
        return  # synthetic data may not produce any completed-rating instructors
    pr = target["perRating"][0]
    # New field names exist, old field names are gone.
    assert {"rating", "n", "avgHrs", "avgCost", "avgDays", "studentIds"} <= pr.keys()
    assert "medianHrs" not in pr
    assert "medianCost" not in pr
    assert "medianDays" not in pr
    # studentIds is a list of stringified student ids; length matches n.
    assert isinstance(pr["studentIds"], list)
    assert all(isinstance(s, str) for s in pr["studentIds"])
    assert len(pr["studentIds"]) == pr["n"]
