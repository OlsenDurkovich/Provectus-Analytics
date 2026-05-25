"""Estimate enrollment windows from FSP flight data alone.

Run AFTER build_enrollments() (survey path) and BEFORE partition_flights().
Skips any student who already has at least one survey-backed enrollment.

Algorithm
---------
Unambiguous billing categories (AMEL / MEI / CFI / CFII):
    start_date     = first completed flight with that billing
    checkride      = first Check Ride cluster where preceding billing implies
                     that rating (majority of 3 most-recent non-checkride flights)
    recheck rule   = Check Rides within RECHECK_WINDOW_DAYS of each other form
                     one cluster; only the first cluster determines the rating end
    Other training = flights between the initial and final ride in a multi-ride
                     cluster → written as an OTHER enrollment

PRIMARY billing (PPL / IFR / COM — all billed identically):
    Check Rides whose preceding billing is PRIMARY / NONE / null are treated as
    primary-rating rides, then clustered by date.  Clusters are assigned
    sequentially: 1st → PPL, 2nd → IFR, 3rd → COM.
    start_date of each rating = first PRIMARY/Solo flight after the previous
    cluster's end.

Partial enrollments:
    If no checkride cluster is found for a started rating, an enrollment is
    written with checkride_date = PARTIAL_SENTINEL ('2099-12-31') and
    is_partial = 1.  milestones.py skips the checkride milestone for these.

Other training:
    Written as an OTHER enrollment (rating code "OTHER", instance_num
    increments per period so multiple recheck episodes per student are
    supported).

Known limitation: for now at most ~100 OTHER enrollments per student are
supported (instance_num 0–99).  More than that would be truly unusual.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import date, timedelta

from .db import rating_id_by_code

RECHECK_WINDOW_DAYS = 60
PARTIAL_SENTINEL    = "2099-12-31"

PRIMARY_SEQUENCE      = ["PPL", "IFR", "COM"]
UNAMBIGUOUS_BILLING   = {"AMEL": "AMEL", "MEI": "MEI", "CFI": "CFI", "CFII": "CFII"}
UNAMBIGUOUS_CODES     = set(UNAMBIGUOUS_BILLING.values())
EXCLUDED_RES_TYPES    = {"Maintenance", "Owner Flight", "Introductory Flight"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _d(s: str) -> date:
    return date.fromisoformat(s)


def _cluster_checkrides(cr_dates: list[date]) -> list[list[date]]:
    """Group Check Ride dates within RECHECK_WINDOW_DAYS into clusters.

    Returns a list of clusters; each cluster is a sorted list of dates.
    """
    if not cr_dates:
        return []
    sorted_dates = sorted(cr_dates)
    clusters: list[list[date]] = [[sorted_dates[0]]]
    for d in sorted_dates[1:]:
        if (d - clusters[-1][-1]).days <= RECHECK_WINDOW_DAYS:
            clusters[-1].append(d)
        else:
            clusters.append([d])
    return clusters


def _majority_billing(flights: list[dict], before_date: date) -> str | None:
    """Return the most common billing_category among the 3 most recent
    completed, non-checkride flights before before_date.
    Returns None if nothing useful found.
    """
    preceding = [
        f for f in flights
        if _d(f["flight_date"]) < before_date
        and f["reservation_type"] != "Check Ride"
        and f["status"] == "Completed"
        and f["billing_category"] not in (None, "NONE", "MISC")
    ]
    preceding.sort(key=lambda f: f["flight_date"], reverse=True)
    recent = preceding[:3]
    if not recent:
        return None
    counts = Counter(f["billing_category"] for f in recent)
    return counts.most_common(1)[0][0]


def _is_primary_checkride(cr_date: date, flights: list[dict]) -> bool:
    """True if the majority billing before this checkride is PRIMARY or unknown
    (i.e. not an unambiguous rating like AMEL/MEI/CFI/CFII).
    """
    billing = _majority_billing(flights, cr_date)
    return billing not in UNAMBIGUOUS_BILLING


# ── Per-student guesstimation ─────────────────────────────────────────────────

def _guesstimate_student(
    student_id: int,
    flights: list[dict],
) -> tuple[list[dict], list[tuple[date, date]]]:
    """Return (enrollments_to_insert, other_periods).

    enrollments_to_insert: list of dicts with keys:
        rating_code, instance_num, start_date, checkride_date,
        is_partial, first_solo_date, xc_solos_complete_date, xc_pic_complete_date

    other_periods: list of (start, end) date pairs for recheck-prep windows
    (collected here; caller writes them as OTHER enrollments).
    """
    completed = [
        f for f in flights
        if f["status"] == "Completed"
        and f["reservation_type"] not in EXCLUDED_RES_TYPES
    ]
    if not completed:
        return [], []

    enrollments: list[dict] = []
    other_periods: list[tuple[date, date]] = []

    # ── Unambiguous ratings ───────────────────────────────────────────────────
    for billing_code, rating_code in UNAMBIGUOUS_BILLING.items():
        billing_flights = [f for f in completed if f["billing_category"] == billing_code]
        if not billing_flights:
            continue

        start_date = min(_d(f["flight_date"]) for f in billing_flights)

        # Find Check Ride events attributed to this rating
        cr_flights = [
            f for f in completed
            if f["reservation_type"] == "Check Ride"
            and _majority_billing(flights, _d(f["flight_date"])) == billing_code
        ]
        clusters = _cluster_checkrides([_d(f["flight_date"]) for f in cr_flights])

        if clusters:
            first_cluster = clusters[0]
            checkride_date = first_cluster[-1]
            is_partial = 0
            # Recheck prep period within the cluster
            if len(first_cluster) > 1:
                prep_start = first_cluster[0] + timedelta(days=1)
                prep_end   = first_cluster[-1] - timedelta(days=1)
                if prep_start <= prep_end:
                    other_periods.append((prep_start, prep_end))
        else:
            checkride_date = _d(PARTIAL_SENTINEL)
            is_partial = 1

        enrollments.append({
            "rating_code":            rating_code,
            "instance_num":           0,
            "start_date":             start_date,
            "checkride_date":         checkride_date,
            "is_partial":             is_partial,
            "first_solo_date":        None,
            "xc_solos_complete_date": None,
            "xc_pic_complete_date":   None,
        })

    # ── PRIMARY ratings (PPL → IFR → COM) ────────────────────────────────────
    primary_flights = [
        f for f in completed
        if f["billing_category"] == "PRIMARY"
        or f["reservation_type"] == "Student Solo"
    ]
    solo_flights = [f for f in completed if f["reservation_type"] == "Student Solo"]

    if primary_flights:
        # Identify Check Rides that belong to primary ratings
        primary_cr_flights = [
            f for f in completed
            if f["reservation_type"] == "Check Ride"
            and _is_primary_checkride(_d(f["flight_date"]), flights)
        ]
        clusters = _cluster_checkrides([_d(f["flight_date"]) for f in primary_cr_flights])

        prev_end: date | None = None

        for i, cluster in enumerate(clusters):
            if i >= len(PRIMARY_SEQUENCE):
                break
            rating_code = PRIMARY_SEQUENCE[i]

            # Flights in this rating's window (after prev_end)
            window_flights = [
                f for f in primary_flights
                if prev_end is None or _d(f["flight_date"]) > prev_end
            ]
            if not window_flights:
                prev_end = cluster[-1]
                continue

            start_date     = min(_d(f["flight_date"]) for f in window_flights)
            checkride_date = cluster[-1]

            # Recheck prep period
            if len(cluster) > 1:
                prep_start = cluster[0] + timedelta(days=1)
                prep_end   = cluster[-1] - timedelta(days=1)
                if prep_start <= prep_end:
                    other_periods.append((prep_start, prep_end))

            # First solo (PPL only)
            first_solo: date | None = None
            if rating_code == "PPL":
                window_solos = [
                    f for f in solo_flights
                    if start_date <= _d(f["flight_date"]) <= checkride_date
                ]
                if window_solos:
                    first_solo = min(_d(f["flight_date"]) for f in window_solos)

            enrollments.append({
                "rating_code":            rating_code,
                "instance_num":           0,
                "start_date":             start_date,
                "checkride_date":         checkride_date,
                "is_partial":             0,
                "first_solo_date":        first_solo,
                "xc_solos_complete_date": None,
                "xc_pic_complete_date":   None,
            })
            prev_end = checkride_date

        # Partial enrollment for the next rating in sequence (if any primary
        # flights exist after the last cluster)
        next_idx = len(clusters)
        if next_idx < len(PRIMARY_SEQUENCE):
            next_rating = PRIMARY_SEQUENCE[next_idx]
            leftover = [
                f for f in primary_flights
                if prev_end is None or _d(f["flight_date"]) > prev_end
            ]
            if leftover:
                start_date = min(_d(f["flight_date"]) for f in leftover)
                first_solo = None
                if next_rating == "PPL":
                    window_solos = [f for f in solo_flights if _d(f["flight_date"]) >= start_date]
                    if window_solos:
                        first_solo = min(_d(f["flight_date"]) for f in window_solos)
                enrollments.append({
                    "rating_code":            next_rating,
                    "instance_num":           0,
                    "start_date":             start_date,
                    "checkride_date":         _d(PARTIAL_SENTINEL),
                    "is_partial":             1,
                    "first_solo_date":        first_solo,
                    "xc_solos_complete_date": None,
                    "xc_pic_complete_date":   None,
                })

    return enrollments, other_periods


# ── Public entry point ────────────────────────────────────────────────────────

def build_guesstimate_enrollments(conn: sqlite3.Connection) -> int:
    """Create estimated enrollment windows for students without survey responses.

    Skips any student who already has at least one survey-backed enrollment
    (source = 'survey').  Returns total number of enrollment rows inserted.
    """
    students_with_surveys: set[int] = {
        row[0] for row in conn.execute(
            "SELECT DISTINCT student_id FROM enrollments WHERE source = 'survey'"
        )
    }

    all_students = conn.execute(
        "SELECT student_id FROM students WHERE student_id IS NOT NULL"
    ).fetchall()

    other_rating_id = rating_id_by_code(conn, "OTHER")
    n_inserted = 0

    for student_row in all_students:
        student_id: int = student_row["student_id"]
        if student_id in students_with_surveys:
            continue

        flights: list[dict] = [
            dict(f) for f in conn.execute(
                """SELECT flight_date, reservation_type, status,
                          billing_category, aircraft_class
                   FROM flights
                   WHERE student_id = ?
                   ORDER BY flight_date""",
                (student_id,),
            )
        ]
        if not flights:
            continue

        enrollments, other_periods = _guesstimate_student(student_id, flights)

        # Insert main rating enrollments
        for enr in enrollments:
            rating_id = rating_id_by_code(conn, enr["rating_code"])
            conn.execute(
                """INSERT OR IGNORE INTO enrollments
                       (student_id, rating_id, instance_num,
                        start_date, checkride_date,
                        first_solo_date, xc_solos_complete_date, xc_pic_complete_date,
                        source, is_partial)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'guesstimate', ?)""",
                (
                    student_id,
                    rating_id,
                    enr["instance_num"],
                    enr["start_date"].isoformat(),
                    enr["checkride_date"].isoformat(),
                    enr["first_solo_date"].isoformat() if enr["first_solo_date"] else None,
                    enr["xc_solos_complete_date"].isoformat()
                        if enr["xc_solos_complete_date"] else None,
                    enr["xc_pic_complete_date"].isoformat()
                        if enr["xc_pic_complete_date"] else None,
                    enr["is_partial"],
                ),
            )
            n_inserted += conn.execute("SELECT changes()").fetchone()[0]

        # Insert OTHER enrollments for each recheck prep period (one per period,
        # instance_num increments so multiple periods per student are supported)
        other_periods.sort(key=lambda p: p[0])
        for seq, (prep_start, prep_end) in enumerate(other_periods):
            conn.execute(
                """INSERT OR IGNORE INTO enrollments
                       (student_id, rating_id, instance_num,
                        start_date, checkride_date,
                        source, is_partial)
                   VALUES (?, ?, ?, ?, ?, 'guesstimate', 0)""",
                (
                    student_id,
                    other_rating_id,
                    seq,
                    prep_start.isoformat(),
                    prep_end.isoformat(),
                ),
            )
            n_inserted += conn.execute("SELECT changes()").fetchone()[0]

    conn.commit()
    return n_inserted
