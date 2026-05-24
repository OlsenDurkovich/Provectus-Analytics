"""End-to-end: pipeline output must match the ground truth derived in
`compute_ground_truth.py`. This is the most important test — if it passes,
the partitioner is reproducing the synthetic answer key through legitimate means
(i.e. without using the Rating Hint column).
"""
from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_ground_truth():
    rows = []
    with open(REPO_ROOT / "ground_truth_per_milestone.csv") as f:
        for r in csv.DictReader(f):
            rows.append({
                "client_fsp": r["client_fsp"],
                "rating": r["rating"],
                "milestone": r["milestone"],
                "milestone_date": r["milestone_date"],
                "days_from_rating_start": int(r["days_from_rating_start"]),
                "cumulative_flights": int(r["cumulative_flights"]),
                "cumulative_hours": float(r["cumulative_hours"]),
                "cumulative_cost": float(r["cumulative_cost"]),
            })
    return rows


def _load_pipeline_output(conn):
    rows = []
    for r in conn.execute(
        """SELECT s.fsp_display_name AS client_fsp,
                  rt.code            AS rating,
                  m.milestone_name   AS milestone,
                  m.milestone_date,
                  m.days_from_rating_start,
                  m.cumulative_flights,
                  m.cumulative_hours,
                  m.cumulative_cost
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     rt USING (rating_id)"""
    ):
        rows.append({
            "client_fsp": r["client_fsp"],
            "rating": r["rating"],
            "milestone": r["milestone"],
            "milestone_date": r["milestone_date"],
            "days_from_rating_start": int(r["days_from_rating_start"]),
            "cumulative_flights": int(r["cumulative_flights"]),
            "cumulative_hours": float(r["cumulative_hours"]),
            "cumulative_cost": float(r["cumulative_cost"]),
        })
    return rows


def _key(row):
    return (row["client_fsp"], row["rating"], row["milestone"])


def test_pipeline_matches_ground_truth(pipeline_db):
    gt = _load_ground_truth()
    out = _load_pipeline_output(pipeline_db)

    gt_index = {_key(r): r for r in gt}
    out_index = {_key(r): r for r in out}

    missing = sorted(set(gt_index) - set(out_index))
    extra = sorted(set(out_index) - set(gt_index))
    assert not missing, f"missing from pipeline: {missing[:10]}"
    assert not extra, f"extra in pipeline: {extra[:10]}"

    mismatches = []
    for k, gt_row in gt_index.items():
        out_row = out_index[k]
        for field in ["milestone_date", "days_from_rating_start",
                      "cumulative_flights", "cumulative_hours", "cumulative_cost"]:
            if gt_row[field] != out_row[field]:
                mismatches.append((k, field, gt_row[field], out_row[field]))

    assert not mismatches, "first 5 mismatches:\n" + "\n".join(
        f"  {k} {field}: expected {gt}, got {out}"
        for k, field, gt, out in mismatches[:5]
    )


def test_pipeline_total_billed_matches(pipeline_db):
    """Sum of cumulative_cost at checkride per alum should match invoice totals."""
    by_alum = {}
    for r in pipeline_db.execute(
        """SELECT s.fsp_display_name AS name, SUM(m.cumulative_cost) AS total
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students s USING (student_id)
           WHERE m.milestone_name = 'checkride'
           GROUP BY s.fsp_display_name"""
    ):
        by_alum[r["name"]] = r["total"]

    # Spot-check a few against earlier validated numbers
    assert abs(by_alum["Alex Martinez"] - 65630.50) < 0.01
    assert abs(by_alum["Sofia Garcia"] - 14523.00) < 0.01
    assert abs(by_alum["Brandon Lee"] - 20746.00) < 0.01
