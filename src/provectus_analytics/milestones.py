"""Compute cumulative metrics at each milestone date for every enrollment.

Milestones per rating:
    PPL  → first_solo, xc_solos_complete, checkride
    IFR  → xc_pic_complete, checkride
    others → checkride only

Milestone date sources:
    first_solo, xc_solos_complete  — date of first/last Student Solo flight in enrollment
    xc_pic_complete                — survey-reported (no flight marker)
    checkride                       — date of Check Ride flight in enrollment
"""
from __future__ import annotations

import sqlite3
from datetime import date


def _date(s: str) -> date:
    return date.fromisoformat(s)


def compute_milestones(conn: sqlite3.Connection) -> int:
    """Populate the milestones table for every enrollment. Returns row count."""
    conn.execute("DELETE FROM milestones")

    enrollments = list(conn.execute(
        """SELECT e.enrollment_id, e.student_id, e.start_date,
                  e.first_solo_date, e.xc_solos_complete_date, e.xc_pic_complete_date,
                  r.code AS rating_code
           FROM enrollments e
           JOIN ratings r USING (rating_id)"""
    ))

    n = 0
    for e in enrollments:
        # Flights attributed to this enrollment, sorted by date
        flights = list(conn.execute(
            """SELECT flight_id, flight_date, length_hrs, reservation_type
               FROM flights
               WHERE enrollment_id = ? AND status = 'Completed'
               ORDER BY flight_date""",
            (e["enrollment_id"],),
        ))

        # Determine which milestones to compute and their dates
        milestones: list[tuple[str, date]] = []
        if e["rating_code"] == "PPL":
            solos = [f for f in flights if f["reservation_type"] == "Student Solo"]
            if solos:
                milestones.append(("first_solo", _date(solos[0]["flight_date"])))
                milestones.append(("xc_solos_complete", _date(solos[-1]["flight_date"])))
        elif e["rating_code"] == "IFR" and e["xc_pic_complete_date"]:
            milestones.append(("xc_pic_complete", _date(e["xc_pic_complete_date"])))

        cr = [f for f in flights if f["reservation_type"] == "Check Ride"]
        if cr:
            milestones.append(("checkride", _date(cr[0]["flight_date"])))

        rating_start = _date(e["start_date"])

        for mname, mdate in milestones:
            cum_flights = [f for f in flights if _date(f["flight_date"]) <= mdate]
            n_flights = len(cum_flights)
            hours = sum(f["length_hrs"] for f in cum_flights)

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
