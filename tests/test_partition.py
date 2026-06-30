"""Partitioner tests."""
from __future__ import annotations


def test_tyler_in_progress_partial_enrollment(pipeline_db):
    """Tyler is mid-PPL (no checkride). He now surfaces as a single PARTIAL PPL
    enrollment so he's visible as an active student — but with NO checkride
    milestone, so he never enters the cohort norms."""
    rows = pipeline_db.execute(
        """SELECT r.code, e.is_partial,
                  EXISTS(SELECT 1 FROM milestones m
                         WHERE m.enrollment_id = e.enrollment_id
                           AND m.milestone_name = 'checkride') AS cr
           FROM enrollments e
           JOIN ratings r USING (rating_id)
           JOIN students s USING (student_id)
           WHERE s.survey_name = 'Tyler Brooks'"""
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["code"] == "PPL"
    assert rows[0]["is_partial"] == 1
    assert rows[0]["cr"] == 0  # no checkride milestone → excluded from norms


def test_tyler_flights_now_attributed(pipeline_db):
    """His primary flights attach to the partial enrollment (so hours/cost roll up)."""
    rows = list(pipeline_db.execute(
        """SELECT enrollment_id FROM flights f
           JOIN students s USING (student_id)
           WHERE s.survey_name = 'Tyler Brooks' AND f.status = 'Completed'
             AND f.reservation_type = 'Dual Flight Training'"""
    ))
    assert len(rows) > 0
    assert any(r["enrollment_id"] is not None for r in rows)


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


def test_current_students_are_in_progress_partials(pipeline_db):
    """Henry/Grace/Daniel are actively training (no checkride). Each surfaces as a
    PARTIAL PPL enrollment with attributed flights but no checkride milestone, so
    they appear as active students without polluting the cohort norms."""
    for name in ["Henry Walsh", "Grace Liu", "Daniel Park"]:
        enr = pipeline_db.execute(
            """SELECT r.code, e.is_partial,
                      EXISTS(SELECT 1 FROM milestones m
                             WHERE m.enrollment_id = e.enrollment_id
                               AND m.milestone_name = 'checkride') AS cr
               FROM enrollments e
               JOIN ratings r USING (rating_id)
               JOIN students s USING (student_id)
               WHERE s.fsp_display_name = ?""",
            (name,),
        ).fetchall()
        assert len(enr) == 1, f"{name} should have one enrollment"
        assert enr[0]["code"] == "PPL" and enr[0]["is_partial"] == 1
        assert enr[0]["cr"] == 0, f"{name} must have no checkride milestone"
        attributed = pipeline_db.execute(
            """SELECT COUNT(*) FROM flights f
               JOIN students s USING (student_id)
               WHERE s.fsp_display_name = ? AND f.enrollment_id IS NOT NULL""",
            (name,),
        ).fetchone()[0]
        assert attributed > 0, f"{name} should have attributed flights"


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
