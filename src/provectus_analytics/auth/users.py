"""User table CRUD + the User domain object.

Lives in the same SQLite database as the analytics tables — there's no
operational reason to split them for a small-team app.

Access model (2026-06-27):
  - role: admin | instructor | viewer (admin = full capabilities).
  - pages: per-user set of dashboard pages the user may see, a subset of
    ALL_PAGES. Roles act as presets (setting a role re-applies its default
    page set); admins can then tweak per user. Flights/upload/user-management
    are admin *capabilities*, not page toggles, so they're not in ALL_PAGES.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from .passwords import hash_password, verify_password

Role = Literal["admin", "instructor", "viewer"]
VALID_ROLES: frozenset[str] = frozenset({"admin", "instructor", "viewer"})

# Toggleable dashboard pages (in canonical order). Flights is NOT here — it's
# the override surface, an admin-only capability.
ALL_PAGES: tuple[str, ...] = ("overview", "ratings", "students", "instructors")
_DEFAULT_PAGES_CSV = ",".join(ALL_PAGES)


def default_pages_for_role(role: str) -> tuple[str, ...]:
    """Preset page set for a role. All roles start with every dashboard page;
    admins then restrict per user as desired."""
    return ALL_PAGES


def _pages_to_csv(pages) -> str:
    seen = set(pages)
    return ",".join(p for p in ALL_PAGES if p in seen)


def _csv_to_pages(csv: str | None) -> tuple[str, ...]:
    if not csv:
        return ()
    present = {p.strip() for p in csv.split(",") if p.strip()}
    return tuple(p for p in ALL_PAGES if p in present)


USERS_DDL = f"""
CREATE TABLE IF NOT EXISTS users (
    user_id          INTEGER PRIMARY KEY,
    email            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    hashed_password  TEXT NOT NULL,
    is_active        INTEGER NOT NULL DEFAULT 1,
    role             TEXT NOT NULL DEFAULT 'viewer',
    pages            TEXT NOT NULL DEFAULT '{_DEFAULT_PAGES_CSV}',
    created_at       TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class User:
    user_id: int
    email: str
    is_active: bool
    role: Role
    pages: tuple[str, ...] = ALL_PAGES

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        keys = row.keys()
        return cls(
            user_id=row["user_id"],
            email=row["email"],
            is_active=bool(row["is_active"]),
            role=row["role"],
            pages=_csv_to_pages(row["pages"]) if "pages" in keys else ALL_PAGES,
        )


def ensure_users_table(conn: sqlite3.Connection) -> None:
    """Idempotent. Safe to call on every startup."""
    conn.execute(USERS_DDL)
    conn.commit()
    _migrate_legacy_roles(conn)
    _migrate_pages_column(conn)


def _migrate_legacy_roles(conn: sqlite3.Connection) -> None:
    """One-time, idempotent: fold the legacy owner role `'boss'` into `'admin'`."""
    conn.execute("UPDATE users SET role = 'admin' WHERE role = 'boss'")
    conn.commit()


def _migrate_pages_column(conn: sqlite3.Connection) -> None:
    """Add the `pages` column to DBs created before it existed, and backfill."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
    if "pages" not in cols:
        conn.execute(
            f"ALTER TABLE users ADD COLUMN pages TEXT NOT NULL "
            f"DEFAULT '{_DEFAULT_PAGES_CSV}'"
        )
    conn.execute(
        f"UPDATE users SET pages = '{_DEFAULT_PAGES_CSV}' "
        f"WHERE pages IS NULL OR pages = ''"
    )
    conn.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
    role: Role = "viewer",
    is_active: bool = True,
) -> User:
    """Create a new user. Raises ValueError on duplicate email or bad input.

    Pages are seeded from the role preset; an admin can adjust them afterward.
    """
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("email must be a valid address")
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    pages_csv = _pages_to_csv(default_pages_for_role(role))
    try:
        cur = conn.execute(
            """INSERT INTO users (email, hashed_password, is_active, role, pages, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (email, hash_password(password), 1 if is_active else 0, role, pages_csv, _now_iso()),
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
        verify_password(password, "$2b$12$" + "x" * 53)
        return None
    if not verify_password(password, row["hashed_password"]):
        return None
    if not row["is_active"]:
        return None
    return User.from_row(row)


def count_users(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def count_active_admins(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
    ).fetchone()[0]


def list_users(conn: sqlite3.Connection) -> list[User]:
    rows = conn.execute("SELECT * FROM users ORDER BY user_id").fetchall()
    return [User.from_row(r) for r in rows]


def _would_remove_last_admin(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    new_role: str | None = None,
    new_active: bool | None = None,
) -> bool:
    """True if applying the proposed change leaves zero active admins."""
    user = get_user_by_id(conn, user_id)
    if user is None:
        return False
    was_active_admin = user.role == "admin" and user.is_active
    if not was_active_admin:
        return False
    role_after = new_role if new_role is not None else user.role
    active_after = new_active if new_active is not None else user.is_active
    if role_after == "admin" and active_after:
        return False
    return count_active_admins(conn) <= 1


def set_user_role(conn: sqlite3.Connection, user_id: int, role: Role) -> User:
    """Update a user's role AND re-apply that role's page preset.

    Refuses to remove the last active admin. Callers that also want custom
    pages should call set_user_pages afterward.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    if get_user_by_id(conn, user_id) is None:
        raise LookupError(f"no user with id {user_id}")
    if _would_remove_last_admin(conn, user_id, new_role=role):
        raise ValueError("cannot remove the last active admin")
    conn.execute(
        "UPDATE users SET role = ?, pages = ? WHERE user_id = ?",
        (role, _pages_to_csv(default_pages_for_role(role)), user_id),
    )
    conn.commit()
    return get_user_by_id(conn, user_id)


def set_user_pages(conn: sqlite3.Connection, user_id: int, pages) -> User:
    """Set a user's visible pages. Unknown page keys raise ValueError."""
    requested = list(pages)
    bad = [p for p in requested if p not in ALL_PAGES]
    if bad:
        raise ValueError(f"unknown page(s): {bad}; valid: {list(ALL_PAGES)}")
    if get_user_by_id(conn, user_id) is None:
        raise LookupError(f"no user with id {user_id}")
    conn.execute(
        "UPDATE users SET pages = ? WHERE user_id = ?",
        (_pages_to_csv(requested), user_id),
    )
    conn.commit()
    return get_user_by_id(conn, user_id)


def set_user_active(conn: sqlite3.Connection, user_id: int, is_active: bool) -> User:
    """Activate/deactivate a user. Refuses to deactivate the last active admin."""
    if get_user_by_id(conn, user_id) is None:
        raise LookupError(f"no user with id {user_id}")
    if _would_remove_last_admin(conn, user_id, new_active=is_active):
        raise ValueError("cannot deactivate the last active admin")
    conn.execute(
        "UPDATE users SET is_active = ? WHERE user_id = ?",
        (1 if is_active else 0, user_id),
    )
    conn.commit()
    return get_user_by_id(conn, user_id)


def change_password(
    conn: sqlite3.Connection,
    user_id: int,
    current_password: str,
    new_password: str,
) -> None:
    """Self-service: change a user's own password after verifying the current one."""
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        raise LookupError(f"no user with id {user_id}")
    if not verify_password(current_password, row["hashed_password"]):
        raise ValueError("current password is incorrect")
    if len(new_password) < 8:
        raise ValueError("password must be at least 8 characters")
    conn.execute(
        "UPDATE users SET hashed_password = ? WHERE user_id = ?",
        (hash_password(new_password), user_id),
    )
    conn.commit()


def admin_reset_password(
    conn: sqlite3.Connection, user_id: int, new_password: str
) -> None:
    """Admin resets another user's password (no current-password check)."""
    if get_user_by_id(conn, user_id) is None:
        raise LookupError(f"no user with id {user_id}")
    if len(new_password) < 8:
        raise ValueError("password must be at least 8 characters")
    conn.execute(
        "UPDATE users SET hashed_password = ? WHERE user_id = ?",
        (hash_password(new_password), user_id),
    )
    conn.commit()


def seed_initial_admin(
    conn: sqlite3.Connection,
    email: str | None,
    password: str | None,
) -> User | None:
    """If the users table is empty AND both env vars are set, seed an admin."""
    if not email or not password:
        return None
    if count_users(conn) > 0:
        return None
    return create_user(conn, email, password, role="admin", is_active=True)
