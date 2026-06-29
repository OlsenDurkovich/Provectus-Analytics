"""DB query layer for the Dash app.

All SQL lives here. Pages call these and get DataFrames / dicts back.
Functions are LRU-cached on (db_path, args); call `clear_caches()` after rebuild.
"""
from __future__ import annotations

import os
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .. import db as _db, ingest, reconcile, partition, guesstimate, milestones, norms

REPO_ROOT = Path(__file__).resolve().parents[3]

# Storage paths are env-driven so Railway (and any other container host) can
# point them at a persistent volume mounted at /data without code changes.
# Defaults preserve the existing local-dev layout.
DEFAULT_DB = Path(os.getenv("DB_PATH", str(REPO_ROOT / "provectus.db")))
FSP_EXPORTS_DIR = Path(os.getenv("FSP_EXPORTS_DIR", str(REPO_ROOT / "FSP Exports")))

# Alumni survey file paths. Real responses live in alumni_survey.xlsx (Google
# Forms export); synthetic dataset uses the CSV variant for tests.
# The real survey path is env-driven for the same reason as DB_PATH.
REAL_SURVEY_XLSX = Path(os.getenv("REAL_SURVEY_PATH", str(REPO_ROOT / "alumni_survey.xlsx")))
SYNTHETIC_SURVEY_CSV = REPO_ROOT / "synthetic_alumni_survey.csv"

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

MILESTONE_LABELS = {
    "first_solo":         "First solo",
    "xc_solos_complete":  "Cross-country solos complete",
    "xc_pic_complete":    "Instrument XC PIC complete",
    "checkride":          "Checkride",
}


# ── Pipeline plumbing ───────────────────────────────────────────────────────

def _find_xlsx(patterns: list[str]) -> Path | None:
    """Return the newest XLSX in FSP_EXPORTS_DIR matching any of the substrings."""
    if not FSP_EXPORTS_DIR.exists():
        return None
    candidates = []
    for p in FSP_EXPORTS_DIR.iterdir():
        if not p.is_file() or p.suffix.lower() != ".xlsx":
            continue
        name_lower = p.name.lower()
        if any(pat.lower() in name_lower for pat in patterns):
            candidates.append(p)
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def _has_real_exports() -> tuple[Path | None, Path | None]:
    """Returns (flight_xlsx, invoice_xlsx) — either may be None if missing."""
    # Match either the canonical name or messy FSP-emitted names like
    # "2026 Flight 5:25:26.xlsx" or "FlightDetail_Report SG.xlsx".
    flight = _find_xlsx(["flightdetail", "flight "])
    if flight is None:
        flight = _find_xlsx(["flight"])  # last-ditch
    invoice = _find_xlsx(["invoice"])
    return flight, invoice


def _snapshot_users(db_path: Path):
    """Capture the users table (login accounts) before a destructive rebuild.

    Returns (columns, rows) or None if the DB / table doesn't exist yet. The
    synthetic rebuild path replaces the whole DB file, and logins live in that
    same file — so we snapshot here and restore afterward to avoid wiping every
    account on a rebuild.
    """
    if not db_path.exists():
        return None
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT * FROM users")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return cols, rows
    except sqlite3.Error:
        # No users table yet (OperationalError) OR the DB is unreadable/corrupt
        # (DatabaseError: "database disk image is malformed"). Either way we have
        # nothing to preserve — let the rebuild proceed and replace the file.
        return None
    finally:
        conn.close()


def _restore_users(db_path: Path, snapshot) -> None:
    """Recreate the users table after a synthetic rebuild and re-insert any
    snapshotted accounts. Always ensures the table exists (so auth keeps working
    even if there were no accounts yet); re-inserts rows when present."""
    # Local import dodges a circular import (auth.deps imports queries lazily).
    from ..auth.users import ensure_users_table
    conn = _db.connect(db_path)
    try:
        ensure_users_table(conn)
        if snapshot:
            cols, rows = snapshot
            if rows:
                collist = ",".join(cols)
                placeholders = ",".join("?" * len(cols))
                conn.executemany(
                    f"INSERT OR REPLACE INTO users ({collist}) VALUES ({placeholders})",
                    rows,
                )
                conn.commit()
    finally:
        conn.close()


def _checkpoint_db(db_path: Path) -> None:
    """Fold the WAL into the main file so the single .db file is self-contained
    (no sidecar needed) before we copy/swap it."""
    conn = _db.connect(db_path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
    finally:
        conn.close()


def _atomic_replace(src: Path, dst: Path) -> None:
    """Atomically install the freshly-built DB at `src` as `dst`.

    The old non-atomic `open(dst,'wb').write(...)` could leave `dst` half-written
    (corrupt) if interrupted, AND it left the old `dst-wal`/`dst-shm` sidecars in
    place — which then mismatch the new main file and raise "database disk image
    is malformed". This writes a staging copy on the SAME filesystem as `dst`,
    removes the stale sidecars, then os.replace() — an atomic rename — so a
    reader never sees a partial file or a stale-WAL pairing.
    """
    src, dst = Path(src), Path(dst)
    staging = dst.with_name(dst.name + ".rebuilding")
    staging.write_bytes(src.read_bytes())
    # Drop the previous DB's WAL/SHM first so they can't shadow the new file.
    for side in ("-wal", "-shm"):
        p = Path(str(dst) + side)
        if p.exists():
            p.unlink()
    os.replace(staging, dst)  # atomic within the same filesystem
    # Clean up the /tmp build + its sidecars.
    for p in (src, Path(str(src) + "-wal"), Path(str(src) + "-shm")):
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass


def build_db(db_path: Path = DEFAULT_DB, force_synthetic: bool = False) -> dict:
    """Non-destructive rebuild.

    - If real FSP XLSX exports exist in FSP Exports/ AND force_synthetic is
      False, use the incremental real-data path (preserves flight_overrides).
    - Otherwise fall back to the synthetic CSV path (drops + reseeds, since
      tests assume a clean slate).
    - Pass force_synthetic=True to use synthetic data even when real exports
      are present (useful while real-data inputs are still being normalised).
    """
    flight_xlsx, invoice_xlsx = _has_real_exports()
    use_real = (flight_xlsx is not None and invoice_xlsx is not None
                and not force_synthetic)

    # The synthetic path overwrites the whole DB file, which would otherwise
    # drop the users table (logins live in the same file). Snapshot first.
    users_snapshot = None if use_real else _snapshot_users(db_path)

    if use_real:
        conn = _db.open_or_create(db_path)
        # Purge any stale synthetic rows from prior synthetic-mode runs so the
        # cohort norms / Student / Instructor pages don't mix the two. The
        # order respects FK constraints: derived rows first, then invoices
        # (which FK into flights + students), then synthetic flights, then the
        # synthetic students themselves. ingest_invoice_xlsx repopulates
        # invoices below; ingest_flight_detail_xlsx repopulates flights.
        # Flights with hobbs_hours IS NULL AND billing_category IS NULL are the
        # synthetic shape; real flights always have at least one of them.
        conn.execute("DELETE FROM milestones")
        # flights.enrollment_id FKs into enrollments; null it before the delete.
        conn.execute("UPDATE flights SET enrollment_id = NULL, partition_notes = NULL")
        conn.execute("DELETE FROM enrollments")
        conn.execute("DELETE FROM surveys")
        conn.execute("DELETE FROM invoices")
        conn.execute(
            "DELETE FROM flights "
            "WHERE hobbs_hours IS NULL AND billing_category IS NULL"
        )
        conn.execute("DELETE FROM students "
                     "WHERE fsp_client_id LIKE 'synth%' OR fsp_client_id IS NULL")
        conn.commit()

        result = {"mode": "real", "flight_xlsx": flight_xlsx.name,
                  "invoice_xlsx": invoice_xlsx.name}
        result["flights"] = ingest.ingest_flight_detail_xlsx(conn, flight_xlsx)
        result["invoice_rows"] = ingest.ingest_invoice_xlsx(conn, invoice_xlsx)
        # Auto-populate students from flight clients so the Student page is
        # usable before alumni surveys arrive. Each row gets
        # match_status='auto_from_flights' so reconcile.reconcile() can upgrade
        # them later when real survey responses land.
        result["students_auto"] = ingest.auto_populate_students_from_flights(conn)
        # Load real alumni survey responses if present. Synthetic CSV is never
        # loaded in real mode — its names won't match real FSP clients and would
        # pollute the cohort with milestones that have no flight hours.
        if REAL_SURVEY_XLSX.exists():
            result["surveys"] = ingest.ingest_survey_xlsx(conn, REAL_SURVEY_XLSX)
        else:
            result["surveys"] = 0
        # Re-apply any manual overrides from prior sessions
        result["overrides_applied"] = ingest.apply_overrides(conn)
    else:
        # Synthetic path: build in /tmp first, then copy to db_path.
        # This avoids SQLite journal-file failures on FUSE-mounted filesystems
        # (e.g. the Cowork sandbox), where unlink() and write transactions are
        # both blocked even though the file itself is writable.
        import shutil, tempfile
        tmp_path = Path(tempfile.mktemp(suffix=".db"))
        conn = _db.init_db(tmp_path, drop_existing=True)
        ingest.ingest_all(
            conn,
            REPO_ROOT / "synthetic_fsp_clients.csv",
            REPO_ROOT / "synthetic_fsp_reservations.csv",
            REPO_ROOT / "synthetic_fsp_invoices.csv",
            SYNTHETIC_SURVEY_CSV,
        )
        result = {"mode": "synthetic"}

    reconcile.reconcile(conn)
    partition.build_enrollments(conn)          # survey-backed enrollments
    guesstimate.build_guesstimate_enrollments(conn)  # heuristic enrollments for non-survey students
    partition.partition_flights(conn)
    milestones.compute_milestones(conn)
    conn.close()

    if not use_real:
        # Finish the build IN the temp DB, then atomically swap it into place.
        # Restore login accounts + checkpoint so tmp is a complete single file,
        # then _atomic_replace() installs it without ever leaving db_path
        # half-written or paired with a stale WAL (the bug that corrupted prod).
        _restore_users(tmp_path, users_snapshot)
        _checkpoint_db(tmp_path)
        _atomic_replace(tmp_path, db_path)

    return result


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


def row_counts(db_path: Path = DEFAULT_DB) -> dict[str, int]:
    """Return row counts for the user-facing tables, for the sidebar debug panel."""
    tables = ["flights", "invoices", "students", "surveys",
              "enrollments", "milestones", "flight_overrides"]
    out: dict[str, int] = {}
    try:
        c = sqlite3.connect(db_path)
        for t in tables:
            try:
                out[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except sqlite3.OperationalError:
                out[t] = 0
        c.close()
    except Exception:
        out = {t: 0 for t in tables}
    return out


def has_flights_no_surveys(db_path: Path = DEFAULT_DB) -> bool:
    """True iff we have real flights ingested but zero matched students.

    Used by Student / Instructor / Overview to show a helpful 'awaiting survey
    responses' message instead of a generic 'No data.'
    """
    try:
        c = sqlite3.connect(db_path)
        n_flights = c.execute(
            "SELECT COUNT(*) FROM flights "
            "WHERE hobbs_hours IS NOT NULL OR billing_category IS NOT NULL"
        ).fetchone()[0]
        n_milestones = c.execute("SELECT COUNT(*) FROM milestones").fetchone()[0]
        c.close()
        return n_flights > 0 and n_milestones == 0
    except Exception:
        return False


def is_live_data(db_path: Path = DEFAULT_DB) -> int:
    """Return # of distinct clients seen in real-FSP flights.

    Distinct clients (not students) so the badge flips to Live before survey
    reconciliation links flights to student rows. A flight is real when
    hobbs_hours is non-null OR billing_category was derived (synthetic data
    has both as NULL).
    """
    try:
        c = sqlite3.connect(db_path)
        n = c.execute(
            "SELECT COUNT(DISTINCT client_raw) FROM flights "
            "WHERE hobbs_hours IS NOT NULL OR billing_category IS NOT NULL"
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
    student_flights.cache_clear()
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
    """Students with at least one flight OR at least one milestone.

    Pre-survey (auto-populated path): every client in flights shows up.
    Post-survey: reconciled alumni also show up (some may have milestones but
    no remaining un-attributed flights).
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT DISTINCT fsp_display_name FROM students s
           WHERE fsp_display_name IS NOT NULL
             AND (
                 EXISTS (SELECT 1 FROM flights    f WHERE f.student_id = s.student_id)
              OR EXISTS (SELECT 1 FROM milestones m
                         JOIN enrollments e USING (enrollment_id)
                         WHERE e.student_id = s.student_id)
             )
           ORDER BY fsp_display_name"""
    ).fetchall()
    conn.close()
    return tuple(r[0] for r in rows)


@lru_cache(maxsize=256)
def student_flights(db_path: str, student: str) -> pd.DataFrame:
    """All flights for one student, newest first. Used by Student page when
    no enrollments/milestones exist yet (pre-survey state)."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """SELECT f.flight_date,
                  f.reservation_type,
                  f.aircraft_tail,
                  f.aircraft_model,
                  f.hobbs_hours,
                  f.length_hrs,
                  f.is_ground_lesson,
                  f.billing_category,
                  f.instructor
           FROM flights f
           JOIN students s USING (student_id)
           WHERE s.fsp_display_name = ?
           ORDER BY f.flight_date DESC""",
        conn, params=(student,),
    )
    conn.close()
    return df


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
