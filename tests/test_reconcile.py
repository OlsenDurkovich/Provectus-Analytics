"""Name reconciliation tests."""
from __future__ import annotations

import json

from provectus_analytics import db as _db, reconcile


def test_name_subset_when_email_mismatches(tmp_path):
    """Direct test of the token-subset rule: build a DB where 'Jane Smith' (survey)
    must match 'Jane M. Smith' (FSP) by name alone — emails don't match."""
    conn = _db.init_db(tmp_path / "t.db")
    conn.execute(
        "INSERT INTO students (fsp_client_id, fsp_display_name, email, match_status) "
        "VALUES ('C1', 'Jane M. Smith', 'jane.work@corp.com', 'unmatched')"
    )
    raw = {"Full name": "Jane Smith", "Email": "jane.personal@gmail.com", "Consent": "Yes"}
    conn.execute("INSERT INTO surveys (student_id, raw_response) VALUES (NULL, ?)",
                 (json.dumps(raw),))
    conn.commit()

    results = reconcile.reconcile(conn)
    assert len(results) == 1
    assert results[0].method == "name_subset"
    assert "extra tokens" in results[0].notes


def test_noah_carter_matched_via_subset(pipeline_db):
    """Survey 'Noah Carter' must match FSP 'Noah J. Carter' via token-subset rule."""
    row = pipeline_db.execute(
        "SELECT survey_name, fsp_display_name, match_status, match_notes "
        "FROM students WHERE fsp_display_name = 'Noah J. Carter'"
    ).fetchone()
    assert row is not None
    assert row["survey_name"] == "Noah Carter"
    assert row["match_status"] == "matched"


def test_all_20_alumni_matched(pipeline_db):
    """Every survey respondent should end up matched (synthetic data is clean)."""
    n = pipeline_db.execute(
        "SELECT COUNT(*) FROM students WHERE survey_name IS NOT NULL AND match_status = 'matched'"
    ).fetchone()[0]
    assert n == 20


def test_current_students_not_matched_to_survey(pipeline_db):
    """Henry/Grace/Daniel are in FSP roster but not in survey — should stay survey_name=NULL."""
    for name in ["Henry Walsh", "Grace Liu", "Daniel Park"]:
        row = pipeline_db.execute(
            "SELECT survey_name FROM students WHERE fsp_display_name = ?", (name,)
        ).fetchone()
        assert row is not None, f"{name} missing from students table"
        assert row["survey_name"] is None, f"{name} should have no survey_name"


def test_apostrophe_name_survives(pipeline_db):
    """Ryan O'Brien — apostrophe must round-trip through CSV → DB → reconcile."""
    row = pipeline_db.execute(
        "SELECT survey_name FROM students WHERE fsp_display_name = ?",
        ("Ryan O'Brien",),
    ).fetchone()
    assert row["survey_name"] == "Ryan O'Brien"


def test_consent_recorded(pipeline_db):
    """Consent flag must reflect the survey response."""
    # Ryan said Yes; Marcus said No
    ryan = pipeline_db.execute(
        "SELECT consent_marketing FROM students WHERE survey_name = ?", ("Ryan O'Brien",)
    ).fetchone()
    marcus = pipeline_db.execute(
        "SELECT consent_marketing FROM students WHERE survey_name = ?", ("Marcus Johnson",)
    ).fetchone()
    assert ryan["consent_marketing"] == 1
    assert marcus["consent_marketing"] == 0
