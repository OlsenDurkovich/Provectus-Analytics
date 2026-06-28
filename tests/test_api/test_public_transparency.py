"""Public transparency endpoint: shape, anonymity, consent filtering."""
from __future__ import annotations

from fastapi.testclient import TestClient

from provectus_analytics import db as _db, norms
from provectus_analytics.api import create_app
from provectus_analytics.api import queries as web_data

_FIELDS = (
    "code", "label", "n", "low_sample",
    "median_cost", "p25_cost", "p75_cost",
    "median_hours", "p25_hours", "p75_hours", "median_days",
)


def _fresh(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    return db_path, TestClient(create_app())


def test_transparency_shape_and_no_pii(tmp_path, monkeypatch):
    _, client = _fresh(tmp_path, monkeypatch)
    r = client.get("/api/public/transparency")
    assert r.status_code == 200
    body = r.json()
    assert body["data_mode"] == "synthetic"
    assert isinstance(body["ratings"], list) and body["ratings"]
    for n in body["ratings"]:
        for f in _FIELDS:
            assert f in n, f"missing {f}"
        # aggregate-only — no per-student identifiers may leak
        assert "name" not in n and "email" not in n and "student_id" not in n
        assert n["low_sample"] is (n["n"] < 10)


def test_transparency_consent_filtered(tmp_path, monkeypatch):
    db_path, _ = _fresh(tmp_path, monkeypatch)
    conn = _db.connect(db_path)
    try:
        all_n = {x.rating: x.n_raw for x in norms.compute_rating_norms(conn)}
        consented_n = {
            x.rating: x.n_raw
            for x in norms.compute_rating_norms(conn, consented_only=True)
        }
        n_consenting = conn.execute(
            "SELECT COUNT(*) FROM students WHERE consent_marketing = 1"
        ).fetchone()[0]
        n_total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    finally:
        conn.close()
    # The consented cohort is a subset, so per-rating sample never exceeds all.
    for rating, n in consented_n.items():
        assert n <= all_n.get(rating, 0)
    # Synthetic data includes non-consenting students, so filtering is real.
    assert n_consenting < n_total
