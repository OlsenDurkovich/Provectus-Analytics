from fastapi.testclient import TestClient

from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data


def test_rebuild_synthetic(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    c = TestClient(create_app())

    r = c.post("/api/rebuild?synthetic=true")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "built" in body
    # rebuild should produce non-empty flights count
    meta = c.get("/api/meta").json()
    assert meta["dataState"]["flights"] > 0


def test_import_fsp_no_exports(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    # Point exports_dir at empty temp dir so the test cannot touch real Downloads / FSP Exports.
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    # Also redirect the downloads folder import_latest scans when called via the endpoint.
    from provectus_analytics import import_exports
    orig = import_exports.import_latest
    monkeypatch.setattr(
        import_exports,
        "import_latest",
        lambda exports_dir=None: orig(downloads=tmp_path / "no_downloads", exports_dir=exports_dir),
    )
    web_data.build_db(db, force_synthetic=True)
    c = TestClient(create_app())
    r = c.post("/api/import-fsp")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "built" in body
