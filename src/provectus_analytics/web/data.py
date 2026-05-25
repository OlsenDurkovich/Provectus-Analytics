"""DB query layer for the Dash app.

All SQL lives here. Pages call these and get DataFrames / dicts back.
Functions are LRU-cached on (db_path, args); call `clear_caches()` after rebuild.
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .. import db as _db, ingest, reconcile, partition, milestones, norms

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "provectus.db"

RATING_ORDER = ["PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"]
RATING_DISPLAY = {
    "PPL":  "Private Pilot",
    "IFR":  "Instrument Rating",
    "COM":  "Commercial Single-Engine",
    "AMEL": "Multi-Engine (AMEL)",
    "CFI":  "CFI",
    "CFII": "CFII",
    "MEI":  "MEI",
}


# ── Pipeline plumbing ───────────────────────────────────────────────────────

def build_db(db_path: Path = DEFAULT_DB) -> None:
    conn = _db.init_db(db_path)
    ingest.ingest_all(
        conn,
        REPO_ROOT / "synthetic_fsp_clients.csv",
        REPO_ROOT / "synthetic_fsp_reservations.csv",
        REPO_ROOT / "synthetic_fsp_invoices.csv",
        REPO_ROOT / "synthetic_alumni_survey.csv",
    )
    reconcile.reconcile(conn)
    partition.build_enrollments(conn)
    partition.partition_flights(conn)
    milestones.compute_milestones(conn)
    conn.close()


def _has_data(db_path: Path) -> bool:
    try:
        c = sqlite3.connect(db_path)
        n = c.execute("SELECT COUNT(*) FROM milestones").fetchone()[0]
        c.close()
        return n > 0
    except Exception:
        return False


def ensure_db(db_path: Path = DEFAULT_DB) -> None:
    if not db_path.exists() or not _has_data(db_path):
        build_db(db_path)


def is_live_data(db_path: Path = DEFAULT_DB) -> int:
    """Return # of students with hobbs_hours (= real FSP rows)."""
    try:
        c = sqlite3.connect(db_path)
        n = c.execute(
            "SELECT COUNT(DISTINCT student_id) FROM flights "
            "WHERE hobbs_hours IS NOT NULL"
        ).fetchone()[0]
        c.close()
        return int(n)
    except Exception:
        return 0


def clear_caches() -> None:
    all_norms.cache_clear()
    rating_cohort.cache_clear()
    student_trajectory.cache_clear()
    all_students.cache_clear()
    instructors.cache_clear()
    instructor_detail.cache_clear()


# ── Cached queries ──────────────────────────────────────────────────────────

@lru_cache(maxsize=8)
def all_norms(db_path: str) -> tuple[dict, ...]:
    conn = _db.connect(db_path)
    result = norms.compute_rating_norms(conn)
    conn.close()
    return tuple(n.__dict__ for n in result)


@lru_cache(maxsize=64)
def rating_cohort(db_path: str, rating: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """SELECT s.fsp_display_name  AS student,
                  s.student_id,
                  m.cumulative_hours  AS hours,
                  m.cumulative_cost   AS cost,
                  m.days_from_rating_start AS days,
                  m.cumulative_flights AS flights,
                  m.milestone_date
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           WHERE r.code = ? AND m.milestone_name = 'checkride'
           ORDER BY s.fsp_display_name""",
        conn, params=(rating,),
    )
    conn.close()
    return df


@lru_cache(maxsize=128)
def student_trajectory(db_path: str, student: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """SELECT r.code AS rating,
                  r.sort_order,
                  m.milestone_name AS milestone,
                  m.milestone_date,
                  m.days_from_rating_start AS days,
                  m.cumulative_flights AS flights,
                  m.cumulative_hours AS hours,
                  m.cumulative_cost AS cost
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           WHERE s.fsp_display_name = ?
           ORDER BY r.sort_order, m.milestone_date""",
        conn, params=(student,),
    )
    conn.close()
    return df


@lru_cache(maxsize=4)
def all_students(db_path: str) -> tuple[str, ...]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT DISTINCT s.fsp_display_name
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           WHERE s.fsp_display_name IS NOT NULL
           ORDER BY s.fsp_display_name"""
    ).fetchall()
    conn.close()
    return tuple(r[0] for r in rows)


@lru_cache(maxsize=4)
def instructors(db_path: str) -> tuple[str, ...]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT DISTINCT instructor FROM flights "
        "WHERE instructor IS NOT NULL ORDER BY instructor"
    ).fetchall()
    conn.close()
    return tuple(r[0] for r in rows)


@lru_cache(maxsize=64)
def instructor_detail(db_path: str, instructor: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """SELECT s.fsp_display_name AS student,
                  r.code AS rating,
                  r.sort_order,
                  m.cumulative_hours  AS hours,
                  m.cumulative_cost   AS cost,
                  m.days_from_rating_start AS days,
                  m.cumulative_flights AS flights,
                  m.milestone_date
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           WHERE m.milestone_name = 'checkride'
             AND e.enrollment_id IN (
                 SELECT DISTINCT f.enrollment_id
                 FROM flights f
                 WHERE f.instructor = ? AND f.enrollment_id IS NOT NULL
             )
           ORDER BY r.sort_order, s.fsp_display_name""",
        conn, params=(instructor,),
    )
    conn.close()
    return df
