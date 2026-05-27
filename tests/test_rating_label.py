"""Phase 10.3 — flights.rating_label takes priority over date-window attribution."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from provectus_analytics import db as _db, ingest, partition
from provectus_analytics.schema import RATING_SEED


def _setup_two_overlapping_enrollments(conn: sqlite3.Connection) -> tuple[int, int, int]:
    """Student with both IFR and COM enrollments active in the same window.
    Without rating_label, a flight in the overlap is ambiguous.
    Returns (student_id, ifr_enrollment_id, com_enrollment_id).
    """
    conn.execute(
        "INSERT INTO students (fsp_display_name, match_status) VALUES (?, 'matched')",
        ("Test Student",),
    )
    sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    ifr_id = next(rid for rid, code, _, _ in RATING_SEED if code == "IFR")
    com_id = next(rid for rid, code, _, _ in RATING_SEED if code == "COM")

    conn.execute(
        "INSERT INTO enrollments (student_id, rating_id, start_date, checkride_date) "
        "VALUES (?, ?, '2024-01-01', '2024-12-31')",
        (sid, ifr_id),
    )
    ifr_enr = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT INTO enrollments (student_id, rating_id, start_date, checkride_date) "
        "VALUES (?, ?, '2024-03-01', '2024-12-31')",
        (sid, com_id),
    )
    com_enr = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    return sid, ifr_enr, com_enr


def test_rating_label_overrides_date_window_ambiguity(tmp_path: Path):
    """An overlap that would normally fall to the earliest-started rating
    instead snaps to whatever rating_label says."""
    db_path = tmp_path / "test.db"
    conn = _db.init_db(db_path)
    sid, ifr_enr, com_enr = _setup_two_overlapping_enrollments(conn)

    # Two flights in the overlap window — one labeled COM, one unlabeled.
    conn.execute(
        """INSERT INTO flights (
               fsp_reservation, flight_date, length_hrs, reservation_type, status,
               student_id, billing_category, rating_label
           ) VALUES ('R001', '2024-06-01', 1.5, 'Dual Flight Training',
                     'Completed', ?, 'PRIMARY', 'COM')""",
        (sid,),
    )
    conn.execute(
        """INSERT INTO flights (
               fsp_reservation, flight_date, length_hrs, reservation_type, status,
               student_id, billing_category
           ) VALUES ('R002', '2024-06-15', 1.5, 'Dual Flight Training',
                     'Completed', ?, 'PRIMARY')""",
        (sid,),
    )
    conn.commit()

    partition.partition_flights(conn)

    labeled = conn.execute(
        "SELECT enrollment_id, partition_notes FROM flights WHERE fsp_reservation='R001'"
    ).fetchone()
    unlabeled = conn.execute(
        "SELECT enrollment_id FROM flights WHERE fsp_reservation='R002'"
    ).fetchone()

    assert labeled["enrollment_id"] == com_enr
    assert "rating_label=COM" in labeled["partition_notes"]
    # Without a label, PRIMARY + overlap falls to earliest-started → IFR.
    assert unlabeled["enrollment_id"] == ifr_enr


def test_rating_label_overridable_via_flight_overrides(tmp_path: Path):
    """User-set rating_label override survives a re-ingest pass."""
    db_path = tmp_path / "test.db"
    conn = _db.init_db(db_path)
    sid, _, com_enr = _setup_two_overlapping_enrollments(conn)

    conn.execute(
        """INSERT INTO flights (
               fsp_reservation, flight_date, length_hrs, reservation_type,
               status, student_id, billing_category
           ) VALUES ('R003', '2024-06-01', 1.5, 'Dual Flight Training',
                     'Completed', ?, 'PRIMARY')""",
        (sid,),
    )
    fid = conn.execute(
        "SELECT flight_id FROM flights WHERE fsp_reservation='R003'"
    ).fetchone()[0]
    conn.commit()

    ingest.set_flight_override(conn, fid, "rating_label", "COM",
                               note="manual attribution test")
    ingest.apply_overrides(conn)
    partition.partition_flights(conn)

    row = conn.execute(
        "SELECT enrollment_id, partition_notes FROM flights WHERE flight_id=?",
        (fid,),
    ).fetchone()
    assert row["enrollment_id"] == com_enr
    assert "rating_label=COM" in row["partition_notes"]
