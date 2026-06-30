"""Partitioner tests."""
from __future__ import annotations


def test_no_enrollments_for_tyler(pipeline_db):
    """Tyler completed nothing → no enrollment rows."""
    n = pipeline_db.execute(
        """SELECT COUNT(*) FROM enrollments e
           JOIN students s USING (student_id)
           WHERE s.survey_name = 'Tyler Brooks'"""
    ).fetchone()[0]
    assert n == 0


def test_tyler_flights_unattributed(pipeline_db):
    """Tyler's flights exist but should all have NULL enrollment_id."""
    rows = list(pipeline_db.execute(
        """SELECT enrollment_id FROM flights f
           JOIN students s USING (student_id)
           WHERE s.survey_name = 'Tyler Brooks' AND f.status = 'Completed'"""
    ))
    assert len(rows) > 0
    assert all(r["enrollment_id"] is None for r in rows)


def test_olivia_concurrent_resolved_by_aircraft(pipeline_db):
    """Olivia's COM and AMEL windows overlap Jun–Aug 2023. ME flights in that
    window must land in AMEL; SE flights must land in COM."""
    rows = list(pipeline_db.execute(
        """SELECT f.aircraft_class, r.code AS rating
           FROM flights f
           JOIN enrollments e ON f.enrollment_id = e.enrollment_id
           JOIN ratings r USING (rating_id)
           JOIN students s ON s.student_id = f.student_id
           WHERE s.fsp_display_name = 'Olivia Nguyen'
             AND f.flight_date BETWEEN '2023-06-01' AND '2023-08-31'
             AND f.status = 'Completed'"""
    ))
    assert rows, "no Olivia overlap flights found"
    for r in rows:
        if (r["aircraft_class"] or "").startswith("ME"):
            assert r["rating"] == "AMEL", f"ME flight should be AMEL, got {r['rating']}"
        else:  # SE_BASIC or SE_COMPLEX
            assert r["rating"] == "COM", f"SE flight should be COM, got {r['rating']}"


def test_excluded_types_never_attributed(pipeline_db):
    """Maintenance, Owner Flight, Introductory Flight: enrollment_id always NULL."""
    n = pipeline_db.execute(
        """SELECT COUNT(*) FROM flights
           WHERE reservation_type IN ('Maintenance', 'Owner Flight', 'Introductory Flight')
             AND enrollment_id IS NOT NULL"""
    ).fetchone()[0]
    assert n == 0


def test_current_students_have_no_enrollments(pipeline_db):
    """Henry/Grace/Daniel — no survey, so no enrollments, so all flights unattributed."""
    for name in ["Henry Walsh", "Grace Liu", "Daniel Park"]:
        n = pipeline_db.execute(
            """SELECT COUNT(*) FROM flights f
               JOIN students s USING (student_id)
               WHERE s.fsp_display_name = ? AND f.enrollment_id IS NOT NULL""",
            (name,),
        ).fetchone()[0]
        assert n == 0, f"{name} should have no attributed flights"


def test_full_career_alum_all_seven_ratings(pipeline_db):
    """Alex Martinez completed all 7 — should have 7 enrollments and 7 checkride flights."""
    enrolls = pipeline_db.execute(
        """SELECT COUNT(*) FROM enrollments e
           JOIN students s USING (student_id)
           WHERE s.fsp_display_name = 'Alex Martinez'"""
    ).fetchone()[0]
    assert enrolls == 7

    checkrides = pipeline_db.execute(
        """SELECT COUNT(*) FROM flights f
           JOIN students s USING (student_id)
           WHERE s.fsp_display_name = 'Alex Martinez'
             AND f.reservation_type = 'Check Ride'
             AND f.enrollment_id IS NOT NULL"""
    ).fetchone()[0]
    assert checkrides == 7
