"""Build enrollments from survey responses, then assign flights to enrollments.

Attribution hierarchy (applied in order):
    1. billing_category (real FSP data only — null for synthetic):
         AMEL/MEI/CFI/CFII  → direct match to that rating's enrollment
         PRIMARY             → filter candidates to PPL/IFR/COM, then fall through
         MISC                → flag as misc, skip (no rating attribution)
         NONE                → Check Rides and Student Solos: infer from preceding
                               flights, then fall through to date-window logic
    2. Check Ride month match (checkride_date month == flight month)
    3. Aircraft class (ME → AMEL/MEI; SE → other)
    4. Fallback: earliest-started rating in window

Reads:  students, surveys, flights
Writes: enrollments, flights.enrollment_id, flights.partition_notes
"""
from __future__ import annotations

import json
import sqlite3
from calendar import monthrange
from datetime import date, datetime

from .db import rating_id_by_code

SURVEY_TO_RATING = {
    "PPL": "PPL", "IFR": "IFR", "ASEL COM": "COM", "AMEL": "AMEL",
    "CFI": "CFI", "CFII": "CFII", "MEI": "MEI",
}

SURVEY_COLUMNS = {
    "PPL":      {"completed": "Completed PPL", "start": "PPL training start",
                 "checkride": "PPL checkride", "first_solo": "First solo",
                 "xc_solos": "XC solos complete"},
    "IFR":      {"completed": "Completed IFR", "start": "IFR training start",
                 "checkride": "IFR checkride", "xc_pic": "XC PIC complete"},
    "ASEL COM": {"completed": "Completed ASEL COM", "start": "ASEL COM start",
                 "checkride": "ASEL COM checkride"},
    "AMEL":     {"completed": "Completed AMEL", "start": "AMEL start",
                 "checkride": "AMEL checkride"},
    "CFI":      {"completed": "Completed CFI", "start": "CFI start",
                 "checkride": "CFI checkride"},
    "CFII":     {"completed": "Completed CFII", "start": "CFII start",
                 "checkride": "CFII checkride"},
    "MEI":      {"completed": "Completed MEI", "start": "MEI start",
                 "checkride": "MEI checkride"},
}

EXCLUDED_RES_TYPES = {"Maintenance", "Owner Flight", "Introductory Flight"}
ME_RATINGS  = {"AMEL", "MEI"}
SE_RATINGS  = {"PPL", "IFR", "COM", "CFI", "CFII"}

# Billing category → rating code (unambiguous mappings only)
BILLING_TO_RATING = {
    "AMEL": "AMEL",
    "MEI":  "MEI",
    "CFI":  "CFI",
    "CFII": "CFII",
}
# PRIMARY maps to PPL/IFR/COM — ambiguous, resolved by date window
PRIMARY_RATINGS = {"PPL", "IFR", "COM"}


def parse_month_year(s: str | None, end_of_month: bool = False) -> date | None:
    if not s or not s.strip():
        return None
    dt = datetime.strptime(s.strip(), "%B %Y").date()
    if end_of_month:
        return date(dt.year, dt.month, monthrange(dt.year, dt.month)[1])
    return dt


def build_enrollments(conn: sqlite3.Connection) -> int:
    n = 0
    surveys = list(conn.execute(
        "SELECT survey_id, student_id, raw_response FROM surveys WHERE student_id IS NOT NULL"
    ))
    for sv in surveys:
        raw = json.loads(sv["raw_response"])
        for survey_rating, cols in SURVEY_COLUMNS.items():
            if raw.get(cols["completed"], "").strip().lower() != "yes":
                continue
            start     = parse_month_year(raw.get(cols["start"]))
            checkride = parse_month_year(raw.get(cols["checkride"]), end_of_month=True)
            if start is None or checkride is None:
                continue
            rating_code = SURVEY_TO_RATING[survey_rating]
            rating_id   = rating_id_by_code(conn, rating_code)
            first_solo  = parse_month_year(raw.get(cols.get("first_solo"))) \
                          if "first_solo" in cols else None
            xc_solos    = parse_month_year(raw.get(cols.get("xc_solos")), end_of_month=True) \
                          if "xc_solos" in cols else None
            xc_pic      = parse_month_year(raw.get(cols.get("xc_pic")), end_of_month=True) \
                          if "xc_pic" in cols else None
            conn.execute(
                """INSERT OR IGNORE INTO enrollments
                       (student_id, rating_id, start_date, checkride_date,
                        first_solo_date, xc_solos_complete_date, xc_pic_complete_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (sv["student_id"], rating_id, start.isoformat(), checkride.isoformat(),
                 first_solo.isoformat() if first_solo else None,
                 xc_solos.isoformat() if xc_solos else None,
                 xc_pic.isoformat() if xc_pic else None),
            )
            n += 1
    conn.commit()
    return n


def _infer_billing_from_preceding(
    flight_date: str,
    student_id: int,
    flights_by_student: dict[int, list[dict]],
) -> str:
    """For Check Rides and NONE-billing flights: look at the 3 most recent
    completed non-checkride flights before this date and return the most
    common billing_category among them. Returns 'NONE' if nothing found.
    """
    student_flights = flights_by_student.get(student_id, [])
    preceding = [
        f for f in student_flights
        if f["flight_date"] < flight_date
        and f["reservation_type"] != "Check Ride"
        and f["status"] == "Completed"
        and f["billing_category"] not in (None, "NONE", "MISC")
    ]
    preceding.sort(key=lambda f: f["flight_date"], reverse=True)
    recent = preceding[:3]
    if not recent:
        return "NONE"
    # Most common billing_category among recent flights
    from collections import Counter
    counts = Counter(f["billing_category"] for f in recent)
    return counts.most_common(1)[0][0]


def _resolve_overlap(
    flight: sqlite3.Row,
    candidates: list[sqlite3.Row],
    effective_billing: str | None,
) -> tuple[int, str]:
    """Pick one enrollment from multiple overlapping ones.

    effective_billing: the billing_category to use (may be inferred from
    preceding flights for Check Rides / NONE-billing events).
    Returns (enrollment_id, note).
    """
    bc = effective_billing or ""

    # 0. OTHER rating takes priority — these are recheck-prep windows that were
    #    intentionally carved out; a flight in that window belongs to OTHER.
    other_c = [e for e in candidates if e["rating_code"] == "OTHER"]
    if len(other_c) == 1:
        return other_c[0]["enrollment_id"], "other training period (recheck prep)"
    if len(other_c) > 1:
        other_c.sort(key=lambda e: e["start_date"])
        return other_c[0]["enrollment_id"], "other training; multiple windows → earliest"

    # 1. Unambiguous billing category → direct match
    if bc in BILLING_TO_RATING:
        target = BILLING_TO_RATING[bc]
        bc_matches = [e for e in candidates if e["rating_code"] == target]
        if len(bc_matches) == 1:
            return bc_matches[0]["enrollment_id"], f"billing category: {bc}"
        if len(bc_matches) > 1:
            bc_matches.sort(key=lambda e: e["start_date"])
            return bc_matches[0]["enrollment_id"], f"billing category {bc}; overlap → earliest"

    # 2. PRIMARY → restrict candidates to PPL/IFR/COM, then fall through
    if bc == "PRIMARY":
        primary_candidates = [e for e in candidates if e["rating_code"] in PRIMARY_RATINGS]
        if primary_candidates:
            candidates = primary_candidates

    # 3. Check Ride month match
    if flight["reservation_type"] == "Check Ride":
        flight_ym = flight["flight_date"][:7]
        cr_matches = [e for e in candidates if e["checkride_date"][:7] == flight_ym]
        if len(cr_matches) == 1:
            return cr_matches[0]["enrollment_id"], "checkride month match"

    # 4. Aircraft class tiebreaker
    ac = flight["aircraft_class"]
    if ac == "ME":
        me_c = [e for e in candidates if e["rating_code"] in ME_RATINGS]
        if len(me_c) == 1:
            return me_c[0]["enrollment_id"], "ME aircraft → AMEL/MEI"
        if len(me_c) > 1:
            me_c.sort(key=lambda e: e["start_date"])
            return me_c[0]["enrollment_id"], "ME aircraft; AMEL/MEI overlap → earliest"
    elif ac in ("SE_BASIC", "SE_COMPLEX"):
        se_c = [e for e in candidates if e["rating_code"] in SE_RATINGS]
        if len(se_c) == 1:
            return se_c[0]["enrollment_id"], "SE aircraft → single SE rating in window"
        if len(se_c) > 1:
            if ac == "SE_COMPLEX":
                com = [e for e in se_c if e["rating_code"] == "COM"]
                if com:
                    return com[0]["enrollment_id"], "SE complex → COM"
            se_c.sort(key=lambda e: e["start_date"])
            return se_c[0]["enrollment_id"], "SE aircraft; overlap → earliest"

    # 5. Fallback: earliest-started
    candidates.sort(key=lambda e: e["start_date"])
    return candidates[0]["enrollment_id"], "fallback: earliest-started rating"


def partition_flights(conn: sqlite3.Connection) -> dict[str, int]:
    """Assign enrollment_id to each completed, non-excluded flight."""
    stats = {"attributed": 0, "unattributed": 0, "excluded": 0,
             "canceled": 0, "overlap_resolved": 0, "misc_skipped": 0}

    flights = list(conn.execute(
        """SELECT flight_id, student_id, flight_date, reservation_type, status,
                  aircraft_class, billing_category, rating_label
           FROM flights"""
    ))

    # Pre-load enrollments per student
    enroll_by_student: dict[int, list[sqlite3.Row]] = {}
    for row in conn.execute(
        """SELECT e.enrollment_id, e.student_id, e.start_date, e.checkride_date,
                  r.code AS rating_code
           FROM enrollments e JOIN ratings r USING (rating_id)"""
    ):
        enroll_by_student.setdefault(row["student_id"], []).append(row)

    # Pre-load all flights per student for checkride lookback (real data only)
    flights_by_student: dict[int, list[dict]] = {}
    for fl in flights:
        if fl["student_id"] is not None:
            flights_by_student.setdefault(fl["student_id"], []).append({
                "flight_date": fl["flight_date"],
                "reservation_type": fl["reservation_type"],
                "status": fl["status"],
                "billing_category": fl["billing_category"],
            })

    for fl in flights:
        if fl["status"] != "Completed":
            stats["canceled"] += 1
            continue
        if fl["reservation_type"] in EXCLUDED_RES_TYPES:
            stats["excluded"] += 1
            continue
        if fl["student_id"] is None:
            stats["unattributed"] += 1
            conn.execute(
                "UPDATE flights SET partition_notes = ? WHERE flight_id = ?",
                ("no student linked", fl["flight_id"]),
            )
            continue

        bc = fl["billing_category"]

        # MISC events: track cost but don't attribute to a rating
        if bc == "MISC":
            stats["misc_skipped"] += 1
            conn.execute(
                "UPDATE flights SET partition_notes = ? WHERE flight_id = ?",
                ("misc/specialty billing — not attributed to a rating", fl["flight_id"]),
            )
            continue

        # For Check Rides and NONE-billing real-data flights, infer from preceding
        effective_billing = bc
        if bc in (None, "NONE") and fl["reservation_type"] == "Check Ride":
            effective_billing = _infer_billing_from_preceding(
                fl["flight_date"], fl["student_id"], flights_by_student,
            )

        student_enrolls = enroll_by_student.get(fl["student_id"], [])
        candidates = [
            e for e in student_enrolls
            if e["start_date"] <= fl["flight_date"] <= e["checkride_date"]
        ]

        # Priority 0: an explicit rating_label trumps everything else. Picks the
        # matching enrollment regardless of date window (e.g. for back-dated
        # corrections) — falls through to date-window logic only if no match.
        rl = fl["rating_label"]
        if rl:
            label_matches = [e for e in student_enrolls if e["rating_code"] == rl]
            if label_matches:
                label_matches.sort(key=lambda e: e["start_date"])
                conn.execute(
                    "UPDATE flights SET enrollment_id = ?, partition_notes = ? "
                    "WHERE flight_id = ?",
                    (label_matches[0]["enrollment_id"],
                     f"rating_label={rl} → direct attribution",
                     fl["flight_id"]),
                )
                stats["attributed"] += 1
                continue

        if not candidates:
            stats["unattributed"] += 1
            conn.execute(
                "UPDATE flights SET partition_notes = ? WHERE flight_id = ?",
                ("no enrollment window contains this date", fl["flight_id"]),
            )
            continue

        if len(candidates) == 1:
            # Still apply billing filter: skip if billing says a different rating
            enr = candidates[0]
            if bc in BILLING_TO_RATING and BILLING_TO_RATING[bc] != enr["rating_code"]:
                stats["unattributed"] += 1
                conn.execute(
                    "UPDATE flights SET partition_notes = ? WHERE flight_id = ?",
                    (f"billing={bc} conflicts with sole window rating={enr['rating_code']}",
                     fl["flight_id"]),
                )
                continue
            enr_id, note = enr["enrollment_id"], "single window"
        else:
            enr_id, note = _resolve_overlap(fl, list(candidates), effective_billing)
            stats["overlap_resolved"] += 1

        conn.execute(
            "UPDATE flights SET enrollment_id = ?, partition_notes = ? WHERE flight_id = ?",
            (enr_id, note, fl["flight_id"]),
        )
        stats["attributed"] += 1

    conn.commit()
    return stats
