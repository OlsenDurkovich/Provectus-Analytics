"""Tests for ingest.ingest_survey_xlsx — real alumni-survey XLSX path."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from provectus_analytics import db as _db, ingest, reconcile, partition


REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_SURVEY = REPO_ROOT / "alumni_survey.xlsx"


@pytest.mark.skipif(not REAL_SURVEY.exists(),
                    reason="alumni_survey.xlsx not present")
def test_ingest_survey_xlsx_round_trips_dates(tmp_path):
    """Datetime cells get normalized to the same string shape the synthetic
    CSV uses, so partition.build_enrollments can parse them unchanged."""
    db_path = tmp_path / "test.db"
    conn = _db.init_db(db_path)

    n = ingest.ingest_survey_xlsx(conn, REAL_SURVEY)
    assert n > 0, "should have ingested at least one response"

    row = conn.execute(
        "SELECT submitted_at, raw_response FROM surveys LIMIT 1"
    ).fetchone()
    assert row is not None
    raw = json.loads(row["raw_response"])

    # All dates land as strings (never datetime in JSON anyway).
    assert isinstance(raw.get("PPL training start"), str)

    # Dates that were datetime in Excel are now "Month YYYY" — same format
    # partition.parse_month_year expects.
    start = raw.get("PPL training start")
    if start:
        parsed = partition.parse_month_year(start)
        assert parsed is not None, f"could not parse {start!r}"


@pytest.mark.skipif(not REAL_SURVEY.exists(),
                    reason="alumni_survey.xlsx not present")
def test_ingest_survey_xlsx_feeds_reconcile_and_partition(tmp_path):
    """End-to-end: real survey → reconcile (creates unmatched students) →
    partition builds enrollments from the normalized dates."""
    db_path = tmp_path / "test.db"
    conn = _db.init_db(db_path)

    ingest.ingest_survey_xlsx(conn, REAL_SURVEY)
    reconcile.reconcile(conn)

    # Reconcile should have linked surveys → students (even if unmatched, it
    # creates new student rows).
    linked = conn.execute(
        "SELECT COUNT(*) FROM surveys WHERE student_id IS NOT NULL"
    ).fetchone()[0]
    assert linked > 0

    # Partition should build at least one enrollment from the survey rows.
    n_enroll = partition.build_enrollments(conn)
    assert n_enroll > 0
