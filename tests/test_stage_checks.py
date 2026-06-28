"""Stage-check ingest + reconcile, validated against the synthetic pipeline.

Proves the integration plumbing: the form's stage-check rows load, join to the
correct FSP student (by email/name), and line up with that student's computed
milestones (each stage check precedes the milestone it's a check for).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from provectus_analytics import ingest, reconcile

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE_CSV = REPO_ROOT / "synthetic_stage_checks.csv"

# stage code -> the milestone it precedes
STAGE_TO_MILESTONE = {
    "pre_solo": "first_solo",
    "pre_xc": "xc_solos_complete",
    "xc_complete": "xc_pic_complete",
    "pre_checkride": "checkride",
}


@pytest.fixture
def db(pipeline_db):
    """Full synthetic pipeline DB (students/enrollments/milestones) + stage checks
    ingested and reconciled."""
    n = ingest.ingest_stage_checks(pipeline_db, STAGE_CSV)
    assert n > 0
    tally = reconcile.reconcile_stage_checks(pipeline_db)
    return pipeline_db, tally


# --- ingest + match --------------------------------------------------------

def test_all_synthetic_stage_checks_match_by_email(db):
    conn, tally = db
    total = conn.execute("SELECT COUNT(*) FROM stage_checks").fetchone()[0]
    assert tally["matched"] == total
    assert tally["unmatched"] == 0 and tally["ambiguous"] == 0


def test_matched_student_name_agrees(db):
    conn, _ = db
    rows = conn.execute(
        """SELECT sc.student_name, s.fsp_display_name, s.survey_name
           FROM stage_checks sc JOIN students s ON s.student_id = sc.student_id"""
    ).fetchall()
    assert rows
    for r in rows:
        assert r["student_name"] in (r["fsp_display_name"], r["survey_name"])


def test_stage_and_result_normalized(db):
    conn, _ = db
    stages = {r[0] for r in conn.execute("SELECT DISTINCT stage FROM stage_checks")}
    assert stages <= {"pre_solo", "pre_xc", "xc_complete", "pre_checkride"}
    results = {r[0] for r in conn.execute("SELECT DISTINCT result FROM stage_checks")}
    assert results <= {"satisfactory", "unsatisfactory", "partial"}


def test_engine_class_derived(db):
    conn, _ = db
    # BE-76 is multi; C172/PA-28 are single.
    for ac, cls in conn.execute("SELECT DISTINCT aircraft, engine_class FROM stage_checks"):
        if ac == "BE-76":
            assert cls == "ME"
        elif ac in ("C172", "PA-28"):
            assert cls == "SE"


# --- coherence with computed milestones ------------------------------------

def test_each_stage_check_precedes_its_milestone(db):
    conn, _ = db
    rows = conn.execute(
        """SELECT sc.stage, sc.check_date, sc.rating, m.milestone_name, m.milestone_date
           FROM stage_checks sc
           JOIN enrollments e ON e.student_id = sc.student_id
           JOIN ratings r     ON r.rating_id = e.rating_id AND r.code = sc.rating
           JOIN milestones m  ON m.enrollment_id = e.enrollment_id
           WHERE m.milestone_name = (
               CASE sc.stage
                   WHEN 'pre_solo' THEN 'first_solo'
                   WHEN 'pre_xc' THEN 'xc_solos_complete'
                   WHEN 'xc_complete' THEN 'xc_pic_complete'
                   WHEN 'pre_checkride' THEN 'checkride'
               END)"""
    ).fetchall()
    # Every stage check should resolve to its milestone, and not occur after it.
    assert len(rows) == conn.execute("SELECT COUNT(*) FROM stage_checks").fetchone()[0]
    for r in rows:
        assert r["check_date"] <= r["milestone_date"], (
            f"{r['rating']} {r['stage']} on {r['check_date']} after "
            f"{r['milestone_name']} {r['milestone_date']}"
        )


# --- the unmatched (manual fix-up) path ------------------------------------

def test_unknown_student_is_left_unmatched(pipeline_db):
    pipeline_db.execute(
        """INSERT INTO stage_checks
             (student_name, student_email, check_date, rating, stage, match_status)
           VALUES ('Ghost Pilot', 'ghost@nowhere.test', '2024-01-01', 'PPL', 'pre_solo', 'unmatched')"""
    )
    pipeline_db.commit()
    tally = reconcile.reconcile_stage_checks(pipeline_db)
    assert tally["unmatched"] >= 1
    sid = pipeline_db.execute(
        "SELECT student_id FROM stage_checks WHERE student_email = 'ghost@nowhere.test'"
    ).fetchone()[0]
    assert sid is None
