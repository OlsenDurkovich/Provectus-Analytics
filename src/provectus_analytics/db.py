"""SQLite connection helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .schema import DDL, RATING_SEED


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with sensible defaults.

    WAL mode lets readers and a single writer work concurrently — critical
    when a long-running rebuild would otherwise block the API serving pages.
    journal_mode is per-database (sticks across opens), so this is effectively
    a one-time set; running it on every connect is cheap and idempotent.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_db(db_path: str | Path, drop_existing: bool = True) -> sqlite3.Connection:
    """Create a fresh DB at db_path. The DB is a derived artifact — safe to drop.

    Legacy path: still used by tests that want a known-empty DB.
    For the production rebuild flow, use `open_or_create` instead — it preserves
    flight_overrides and other persistent rows across rebuilds.
    """
    p = Path(db_path)
    if drop_existing and p.exists():
        try:
            p.unlink()
        except PermissionError:
            # On some mounted filesystems unlink is blocked (e.g. macOS FUSE
            # mounts in the Cowork sandbox).  Build in /tmp then copy over.
            import tempfile
            tmp = Path(tempfile.mktemp(suffix=".db"))
            conn_tmp = connect(tmp)
            for stmt in DDL:
                conn_tmp.execute(stmt)
            conn_tmp.executemany(
                "INSERT OR IGNORE INTO ratings "
                "(rating_id, code, display, sort_order) VALUES (?, ?, ?, ?)",
                RATING_SEED,
            )
            conn_tmp.commit()
            conn_tmp.close()
            with open(p, "wb") as fout:
                fout.write(tmp.read_bytes())
            tmp.unlink()
            return connect(p)  # return early — DDL already applied
    conn = connect(p)
    for stmt in DDL:
        conn.execute(stmt)
    conn.executemany(
        "INSERT OR IGNORE INTO ratings (rating_id, code, display, sort_order) VALUES (?, ?, ?, ?)",
        RATING_SEED,
    )
    conn.commit()
    return conn


def _migrate_enrollments(conn: sqlite3.Connection) -> None:
    """Recreate the enrollments table if it predates the instance_num/source/is_partial columns.

    Safe to call on a fresh DB (no-op if the new schema is already in place).
    Clears milestones and enrollment_id references from flights since those are
    always rebuilt from scratch by build_db() anyway.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(enrollments)").fetchall()}
    if "instance_num" in cols:
        return  # Already on new schema

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DELETE FROM milestones")
    conn.execute("UPDATE flights SET enrollment_id = NULL, partition_notes = NULL")
    conn.execute("ALTER TABLE enrollments RENAME TO _enrollments_old")
    conn.execute(
        """
        CREATE TABLE enrollments (
            enrollment_id          INTEGER PRIMARY KEY,
            student_id             INTEGER NOT NULL REFERENCES students(student_id),
            rating_id              INTEGER NOT NULL REFERENCES ratings(rating_id),
            instance_num           INTEGER NOT NULL DEFAULT 0,
            start_date             TEXT NOT NULL,
            checkride_date         TEXT NOT NULL,
            first_solo_date        TEXT,
            xc_solos_complete_date TEXT,
            xc_pic_complete_date   TEXT,
            source                 TEXT NOT NULL DEFAULT 'survey',
            is_partial             INTEGER NOT NULL DEFAULT 0,
            UNIQUE (student_id, rating_id, instance_num)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO enrollments
            (enrollment_id, student_id, rating_id, instance_num,
             start_date, checkride_date,
             first_solo_date, xc_solos_complete_date, xc_pic_complete_date,
             source, is_partial)
        SELECT enrollment_id, student_id, rating_id, 0,
               start_date, checkride_date,
               first_solo_date, xc_solos_complete_date, xc_pic_complete_date,
               'survey', 0
        FROM _enrollments_old
        """
    )
    conn.execute("DROP TABLE _enrollments_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_milestones_enrollment ON milestones(enrollment_id)")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def _migrate_flights_add_rating_label(conn: sqlite3.Connection) -> None:
    """Add flights.rating_label if it doesn't exist yet (Phase 10.3)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(flights)").fetchall()}
    if "rating_label" in cols:
        return
    conn.execute("ALTER TABLE flights ADD COLUMN rating_label TEXT")
    conn.commit()


def open_or_create(db_path: str | Path) -> sqlite3.Connection:
    """Open DB at db_path, creating tables/indexes that don't exist yet.

    Idempotent: safe to call on a fresh path or an existing populated DB. Schema
    additions land via the IF NOT EXISTS clauses in DDL, so this also functions
    as a forward-only migrator.
    """
    conn = connect(db_path)
    for stmt in DDL:
        conn.execute(stmt)
    conn.executemany(
        "INSERT OR IGNORE INTO ratings (rating_id, code, display, sort_order) VALUES (?, ?, ?, ?)",
        RATING_SEED,
    )
    conn.commit()
    _migrate_enrollments(conn)  # forward-only: no-op if already on new schema
    _migrate_flights_add_rating_label(conn)
    return conn


def rating_id_by_code(conn: sqlite3.Connection, code: str) -> int:
    row = conn.execute("SELECT rating_id FROM ratings WHERE code = ?", (code,)).fetchone()
    if row is None:
        raise KeyError(f"Unknown rating code: {code}")
    return row["rating_id"]
