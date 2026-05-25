"""SQLite connection helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .schema import DDL, RATING_SEED


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with sensible defaults."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | Path, drop_existing: bool = True) -> sqlite3.Connection:
    """Create a fresh DB at db_path. The DB is a derived artifact — safe to drop.

    Legacy path: still used by tests that want a known-empty DB.
    For the production rebuild flow, use `open_or_create` instead — it preserves
    flight_overrides and other persistent rows across rebuilds.
    """
    p = Path(db_path)
    if drop_existing and p.exists():
        p.unlink()
    conn = connect(p)
    for stmt in DDL:
        conn.execute(stmt)
    conn.executemany(
        "INSERT OR IGNORE INTO ratings (rating_id, code, display, sort_order) VALUES (?, ?, ?, ?)",
        RATING_SEED,
    )
    conn.commit()
    return conn


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
    return conn


def rating_id_by_code(conn: sqlite3.Connection, code: str) -> int:
    row = conn.execute("SELECT rating_id FROM ratings WHERE code = ?", (code,)).fetchone()
    if row is None:
        raise KeyError(f"Unknown rating code: {code}")
    return row["rating_id"]
