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


def test_override_persists(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    flights = c.get("/api/flights").json()
    assert flights, "synthetic build should produce flights"

    # Find a flight that's currently a Flight (not Ground) so the toggle is observable.
    target = next((f for f in flights if f["ground"] == "Flight (0)"), flights[0])
    fid = target["id"]

    r = c.patch(f"/api/flights/{fid}", json={"field": "is_ground_lesson", "value": True})
    assert r.status_code == 200, r.text
    after = r.json()
    assert after["id"] == fid
    assert after["ground"] == "Ground (1)"

    # Re-fetch the list and confirm persistence
    flights2 = c.get("/api/flights").json()
    persisted = next(f for f in flights2 if f["id"] == fid)
    assert persisted["ground"] == "Ground (1)"


def test_override_clear(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    flights = c.get("/api/flights").json()
    fid = flights[0]["id"]

    # Set to Ground, then clear — clear nulls the column, which displays as Flight.
    c.patch(f"/api/flights/{fid}", json={"field": "is_ground_lesson", "value": True})
    r = c.patch(f"/api/flights/{fid}", json={"field": "is_ground_lesson", "value": None})
    assert r.status_code == 200, r.text
    assert r.json()["ground"] == "Flight (0)"


def test_override_invalid_field_returns_422(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    flights = c.get("/api/flights").json()
    r = c.patch(f"/api/flights/{flights[0]['id']}", json={"field": "client_name", "value": "x"})
    assert r.status_code == 422
