"""Compute cumulative metrics at each milestone date for every enrollment.

Milestones per rating:
    PPL  → first_solo, xc_solos_complete, checkride
    IFR  → xc_pic_complete, checkride
    others → checkride only

Milestone date sources:
    first_solo, xc_solos_complete  — date of first/last Student Solo in enrollment
    xc_pic_complete                — survey-reported (no flight marker)
    checkride                       — date of the *passed* Check Ride flight
                                      (last Check Ride on or before survey checkride date);
                                      falls back to survey checkride_date when no
                                      Check Ride flight is logged (e.g. older PPL/IFR/COM)

Failed / discontinued checkrides:
    All checkride attempts are counted in cumulative flights, hours, and cost
    up to the passed checkride date.  Only the passed checkride sets the
    milestone_date.

Flight hours:
    Real data  → hobbs_hours (null for ground lessons → 0 hrs)
    Synthetic  → length_hrs (hobbs_hours is null for synthetic rows)
    Formula:   CASE WHEN is_ground_lesson = 1 THEN 0
                    WHEN hobbs_hours IS NOT NULL THEN hobbs_hours
                    ELSE length_hrs END
"""
from __future__ import annotations

import sqlite3
from datetime import date


def _date(s: str) -> date:
    return date.fromisoformat(s)


def _flight_hours(f: sqlite3.Row) -> float:
    """Return actual flight hours for a row, handling real vs synthetic data."""
    if f["is_ground_lesson"]:
        return 0.0
    if f["hobbs_hours"] is not None:
        return float(f["hobbs_hours"])
    return float(f["length_hrs"])


def compute_milestones(conn: sqlite3.Connection) -> int:
    """Populate the milestones table for every enrollment. Returns row count."""
    conn.execute("DELETE FROM milestones")

    enrollments = list(conn.execute(
        """SELECT e.enrollment_id, e.student_id, e.start_date,
                  e.first_solo_date, e.xc_solos_complete_date, e.xc_pic_complete_date,
                  e.checkride_date AS survey_checkride_date,
                  e.is_partial,
                  r.code AS rating_code
           FROM enrollments e
           JOIN ratings r USING (rating_id)
           WHERE r.code != 'OTHER'"""
    ))

    n = 0
    for e in enrollments:
        # All completed flights attributed to this enrollment, sorted by date
        flights = list(conn.execute(
            """SELECT flight_id, flight_date, length_hrs, hobbs_hours,
                      is_ground_lesson, reservation_type
               FROM flights
               WHERE enrollment_id = ? AND status = 'Completed'
               ORDER BY flight_date""",
            (e["enrollment_id"],),
        ))

        # ── Identify the passed checkride ────────────────────────────────────
        # The passed checkride = the last Check Ride on or before the
        # survey-reported checkride month end-date.
        survey_cr_date = _date(e["survey_checkride_date"])
        cr_flights = [
            f for f in flights
            if f["reservation_type"] == "Check Ride"
            and _date(f["flight_date"]) <= survey_cr_date
        ]
        passed_cr = cr_flights[-1] if cr_flights else None  # last = most recent

        # If no Check Ride flight logged (common for PPL/IFR/COM in older data),
        # fall back to the survey-reported date directly.
        checkride_date = (
            _date(passed_cr["flight_date"]) if passed_cr else survey_cr_date
        )

        # ── Determine milestones ─────────────────────────────────────────────
        milestones: list[tuple[str, date]] = []

        if e["rating_code"] == "PPL":
            solos = [f for f in flights if f["reservation_type"] == "Student Solo"]
            if solos:
                milestones.append(("first_solo",        _date(solos[0]["flight_date"])))
                milestones.append(("xc_solos_complete", _date(solos[-1]["flight_date"])))
        elif e["rating_code"] == "IFR" and e["xc_pic_complete_date"]:
            milestones.append(("xc_pic_complete", _date(e["xc_pic_complete_date"])))

        # Partial enrollments (no checkride found yet) use a sentinel date;
        # skip the checkride milestone so '2099-12-31' never surfaces in the UI.
        if not e["is_partial"]:
            milestones.append(("checkride", checkride_date))

        rating_start = _date(e["start_date"])

        for mname, mdate in milestones:
            cum_flights = [f for f in flights if _date(f["flight_date"]) <= mdate]
            n_flights   = len(cum_flights)
            hours       = sum(_flight_hours(f) for f in cum_flights)

            cost_row = conn.execute(
                """SELECT COALESCE(SUM(i.amount), 0) AS total
                   FROM invoices i
                   JOIN flights f ON f.flight_id = i.flight_id
                   WHERE f.enrollment_id = ? AND f.flight_date <= ? AND f.status = 'Completed'""",
                (e["enrollment_id"], mdate.isoformat()),
            ).fetchone()
            cost = float(cost_row["total"])
            days = (mdate - rating_start).days

            conn.execute(
                """INSERT INTO milestones
                       (enrollment_id, milestone_name, milestone_date,
                        days_from_rating_start, cumulative_flights,
                        cumulative_hours, cumulative_cost)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (e["enrollment_id"], mname, mdate.isoformat(), days,
                 n_flights, round(hours, 1), round(cost, 2)),
            )
            n += 1

    conn.commit()
    return n
