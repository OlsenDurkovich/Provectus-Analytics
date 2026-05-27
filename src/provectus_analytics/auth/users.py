"""User table CRUD + the User domain object.

Lives in the same SQLite database as the analytics tables — there's no
operational reason to split them for a 2-3 user app.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from .passwords import hash_password, verify_password

Role = Literal["admin", "boss"]

USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    user_id          INTEGER PRIMARY KEY,
    email            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    hashed_password  TEXT NOT NULL,
    is_active        INTEGER NOT NULL DEFAULT 1,
    role             TEXT NOT NULL DEFAULT 'boss',
    created_at       TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class User:
    user_id: int
    email: str
    is_active: bool
    role: Role

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        return cls(
            user_id=row["user_id"],
            email=row["email"],
            is_active=bool(row["is_active"]),
            role=row["role"],
        )


def ensure_users_table(conn: sqlite3.Connection) -> None:
    """Idempotent. Safe to call on every startup."""
    conn.execute(USERS_DDL)
    conn.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
    role: Role = "boss",
    is_active: bool = True,
) -> User:
    """Create a new user. Raises ValueError on duplicate email."""
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("email must be a valid address")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    try:
        cur = conn.execute(
            """INSERT INTO users (email, hashed_password, is_active, role, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (email, hash_password(password), 1 if is_active else 0, role, _now_iso()),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"user with email {email!r} already exists") from exc
    conn.commit()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (cur.lastrowid,)
    ).fetchone()
    return User.from_row(row)


def get_user_by_email(conn: sqlite3.Connection, email: str) -> User | None:
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    return User.from_row(row) if row else None


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return User.from_row(row) if row else None


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> User | None:
    """Verify credentials. Returns the User on success or None on failure.

    Constant-time-ish: always runs the hash verify even on missing user so
    user-enumeration timing attacks have less of a signal."""
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    if row is None:
        # Run a verify against a known-bad hash to spend roughly the same
        # cpu as a real verify would.
        verify_password(password, "$2b$12$" + "x" * 53)
        return None
    if not verify_password(password, row["hashed_password"]):
        return None
    if not row["is_active"]:
        return None
    return User.from_row(row)


def count_users(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def seed_initial_admin(
    conn: sqlite3.Connection,
    email: str | None,
    password: str | None,
) -> User | None:
    """If the users table is empty AND both env vars are set, seed an admin.

    Returns the new User, or None if no seeding happened.
    Never overwrites an existing user.
    """
    if not email or not password:
        return None
    if count_users(conn) > 0:
        return None
    return create_user(conn, email, password, role="admin", is_active=True)
