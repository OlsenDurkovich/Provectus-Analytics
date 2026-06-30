from fastapi.testclient import TestClient

from provectus_analytics.api import create_app
from provectus_analytics.api import queries as web_data
from provectus_analytics.api import adapters


def _fresh(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app())


def test_insights_shape(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/insights")
    assert r.status_code == 200, r.text
    body = r.json()
    assert {"atRiskThresholdPct", "atRisk", "strengths", "efficiency"} <= body.keys()
    assert body["atRiskThresholdPct"] == 0.25
    assert isinstance(body["atRisk"], list)
    assert body["strengths"], "synthetic data should yield instructor-rating stats"
    assert body["efficiency"], "synthetic data should yield an efficiency ranking"


def test_at_risk_respects_threshold(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    low = c.get("/api/insights?threshold=0.10").json()["atRisk"]
    high = c.get("/api/insights?threshold=0.80").json()["atRisk"]
    # A stricter (higher) threshold can only flag fewer students.
    assert len(high) <= len(low)
    # Every flagged row is genuinely over the threshold it was queried with.
    for row in low:
        assert row["worstPct"] >= 0.10
        assert row["worstPct"] == max(row["pctOverHours"], row["pctOverCost"])


def test_efficiency_ranked_best_first(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    eff = c.get("/api/insights").json()["efficiency"]
    scores = [e["score"] for e in eff]
    assert scores == sorted(scores), "efficiency must be sorted by score ascending"
    assert eff[0]["rank"] == 1
    assert [e["rank"] for e in eff] == list(range(1, len(eff) + 1))


def test_strengths_ranked_lowest_hours_first(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    strengths = c.get("/api/insights").json()["strengths"]
    for rating in strengths:
        insts = rating["instructors"]
        hours = [i["avgHours"] for i in insts]
        assert hours == sorted(hours), f"{rating['rating']} not best-first"
        assert insts[0]["rank"] == 1
        # n below the 'good' sample size is flagged
        for i in insts:
            assert i["lowSample"] == (i["n"] < 3)
            assert "vsRestHoursPct" in i and "comparable" in i


def test_leave_one_out_resolves_dominant_instructor_paradox(tmp_path, monkeypatch):
    """CFI's top instructor taught most of the cohort, so a self-inclusive
    baseline read +1% (★ but red — the paradox). Leave-one-out compares them to
    everyone else's students, so the rank-1 instructor now reads BELOW the rest."""
    c = _fresh(tmp_path, monkeypatch)
    strengths = c.get("/api/insights").json()["strengths"]
    cfi = next(r for r in strengths if r["rating"] == "CFI")
    best = cfi["instructors"][0]
    assert best["rank"] == 1 and best["comparable"]
    assert best["vsRestHoursPct"] < 0, "rank-1 CFI instructor should be below the rest"


def test_efficiency_uses_vs_rest_fields(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    eff = c.get("/api/insights").json()["efficiency"]
    assert eff and {"avgHoursVsRestPct", "avgCostVsRestPct"} <= eff[0].keys()
    # score is the blend of the two deviations (allow for 4-dp rounding slack)
    e = eff[0]
    assert abs(e["score"] - (e["avgHoursVsRestPct"] + e["avgCostVsRestPct"]) / 2) < 1e-3


def test_predictions_cover_in_progress_states(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    preds = {p["name"]: p for p in c.get("/api/insights").json()["predictions"]}
    assert preds, "synthetic data has in-progress students to predict"
    statuses = {p["status"] for p in preds.values()}
    assert statuses <= {"on_track", "over_median", "stalled"}
    # Tyler hasn't flown in years → stalled, no projection.
    assert preds["Tyler Brooks"]["status"] == "stalled"
    assert preds["Tyler Brooks"]["projectedDate"] is None
    # An on-track student gets a future projected date + weeks remaining.
    on_track = [p for p in preds.values() if p["status"] == "on_track"]
    assert on_track and all(p["projectedDate"] and p["weeksRemaining"] is not None for p in on_track)


def test_cadence_buckets_monotonic(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    cad = c.get("/api/insights").json()["cadence"]
    assert cad and cad["scope"] == "all ratings"
    buckets = cad["buckets"]
    # all four cadence brackets should be populated by the synthetic cohort
    assert len(buckets) == 4
    cadences = [b["avgCadence"] for b in buckets]
    days = [b["avgDays"] for b in buckets]
    assert cadences == sorted(cadences)
    assert days == sorted(days, reverse=True), "more frequent training should finish sooner"
    # cost (vs each student's rating median) trends down with cadence
    assert buckets[-1]["costVsMedianPct"] <= buckets[0]["costVsMedianPct"]
    assert {"costVsMedianPct", "hoursVsMedianPct"} <= buckets[0].keys()


def test_adapter_at_risk_threshold_unit(tmp_path, monkeypatch):
    # Direct adapter call (no HTTP) — at a 200% threshold nobody is flagged.
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db, force_synthetic=True)
    web_data.clear_caches()
    assert adapters.insights(2.0).atRisk == []
