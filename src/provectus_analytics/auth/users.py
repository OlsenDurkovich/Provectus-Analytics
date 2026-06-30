"""User table CRUD + the User domain object.

Lives in the same SQLite database as the analytics tables — there's no
operational reason to split them for a small-team app.

Access model (2026-06-27):
  - role: admin | instructor | viewer | student (admin = full capabilities).
  - pages: per-user set of dashboard pages the user may see, a subset of
    ALL_PAGES. Roles act as presets (setting a role re-applies its default
    page set); admins can then tweak per user. Flights/upload/user-management
    are admin *capabilities*, not page toggles, so they're not in ALL_PAGES.
  - student: a self-service account scoped to ONE person's own training data.
    Students get an EMPTY page set (none of the internal dashboard pages) and
    are instead linked to a single `student_id`; they can only reach
    `/api/me/training`, which serves their own record. The empty page set means
    every `require_page()`-gated endpoint already returns 403 for them, so no
    extra blocking is needed.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .passwords import hash_password, verify_password

Role = Literal["admin", "instructor", "viewer", "student"]
VALID_ROLES: frozenset[str] = frozenset({"admin", "instructor", "viewer", "student"})

# Toggleable dashboard pages (in canonical order). Flights is NOT here — it's
# the override surface, an admin-only capability.
ALL_PAGES: tuple[str, ...] = ("overview", "ratings", "students", "instructors", "insights")
_DEFAULT_PAGES_CSV = ",".join(ALL_PAGES)
# Pages that existed before "insights" was added — used to grant the new page to
# users who already had full dashboard access (see _migrate_add_page).
_LEGACY_FULL_PAGES = frozenset(("overview", "ratings", "students", "instructors"))

# ── Dedicated auth database ───────────────────────────────────────────────────
# Login accounts + per-user settings live in their OWN SQLite file, separate
# from the analytics DB. The analytics DB is a regenerable artifact that the
# "Rebuild DB" flow replaces wholesale; keeping users out of that file means a
# rebuild (or a corrupt analytics DB) can never wipe accounts. Compartmentalized
# durable state — a deliberate best-practice split.
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_auth_db() -> Path:
    """AUTH_DB_PATH if set; else sit next to the analytics DB (same volume);
    else fall back to the repo root for local/dev."""
    explicit = os.getenv("AUTH_DB_PATH")
    if explicit:
        return Path(explicit)
    analytics = os.getenv("DB_PATH")
    if analytics:
        return Path(analytics).parent / "auth.db"
    return _REPO_ROOT / "auth.db"


# Module-level so tests can monkeypatch it (mirrors queries.DEFAULT_DB).
AUTH_DB: Path = _resolve_auth_db()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the auth DB (creating + migrating the users table if needed).

    Every user read/write goes through here, so user data is always read from
    and written to the dedicated auth database — never the analytics file.
    """
    from .. import db as _db  # local import avoids any import-order coupling
    conn = _db.connect(db_path or AUTH_DB)
    ensure_users_table(conn)
    return conn


# Roles scoped to their own data via a dedicated endpoint instead of the shared
# dashboard. They get NO dashboard pages, so every require_page() gate already
# 403s for them: student → /api/me/training, instructor → /api/me/students.
_SCOPED_ROLES: frozenset[str] = frozenset({"student", "instructor"})


def default_pages_for_role(role: str) -> tuple[str, ...]:
    """Preset page set for a role. Admin/viewer start with every dashboard page
    (admins then restrict per user); the scoped roles (student, instructor) get
    NO dashboard pages — they see only their own data via /api/me/*."""
    if role in _SCOPED_ROLES:
        return ()
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
    student_id       INTEGER,
    instructor_name  TEXT,
    display_name     TEXT,
    phone            TEXT,
    theme            TEXT,                -- 'dark' | 'light' | NULL (follow browser)
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
    # Set only for `student`-role accounts: the students.student_id this login
    # is allowed to see. None for every other role.
    student_id: int | None = None
    # Set only for `instructor`-role accounts: the flights.instructor name whose
    # students this login may see. None for every other role.
    instructor_name: str | None = None
    # Self-service profile fields (any role can edit their own).
    display_name: str | None = None
    phone: str | None = None
    theme: str | None = None  # 'dark' | 'light' | None (follow browser)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def is_instructor(self) -> bool:
        return self.role == "instructor"

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        keys = row.keys()
        return cls(
            user_id=row["user_id"],
            email=row["email"],
            is_active=bool(row["is_active"]),
            role=row["role"],
            pages=_csv_to_pages(row["pages"]) if "pages" in keys else ALL_PAGES,
            student_id=(
                row["student_id"]
                if "student_id" in keys and row["student_id"] is not None
                else None
            ),
            instructor_name=(
                row["instructor_name"]
                if "instructor_name" in keys and row["instructor_name"] is not None
                else None
            ),
            display_name=row["display_name"] if "display_name" in keys else None,
            phone=row["phone"] if "phone" in keys else None,
            theme=row["theme"] if "theme" in keys else None,
        )


def ensure_users_table(conn: sqlite3.Connection) -> None:
    """Idempotent. Safe to call on every startup."""
    conn.execute(USERS_DDL)
    conn.commit()
    _migrate_legacy_roles(conn)
    _migrate_pages_column(conn)
    _migrate_add_page(conn)
    _migrate_student_id_column(conn)
    _migrate_instructor_name_column(conn)
    _migrate_profile_columns(conn)


def _migrate_profile_columns(conn: sqlite3.Connection) -> None:
    """Add the self-service profile columns to pre-existing DBs."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
    for col in ("display_name", "phone", "theme"):
        if col not in cols:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
    conn.commit()


def _migrate_legacy_roles(conn: sqlite3.Connection) -> None:
    """One-time, idempotent: fold the legacy owner role `'boss'` into `'admin'`."""
    conn.execute("UPDATE users SET role = 'admin' WHERE role = 'boss'")
    conn.commit()


def _migrate_pages_column(conn: sqlite3.Connection) -> None:
    """Add the `pages` column to DBs created before it existed, and backfill ONLY
    genuinely-uninitialized (NULL) rows.

    IMPORTANT: this runs on every connect (ensure_users_table), so it must not
    clobber an *intentionally* empty page set. An empty string '' is a valid
    "no dashboard pages" state (an admin can block a viewer, and scoped roles
    are empty by design) — only NULL means "column never set". Backfilling ''
    here would silently re-grant access to blocked users.
    """
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
    if "pages" not in cols:
        conn.execute(
            f"ALTER TABLE users ADD COLUMN pages TEXT NOT NULL "
            f"DEFAULT '{_DEFAULT_PAGES_CSV}'"
        )
    conn.execute(
        f"UPDATE users SET pages = '{_DEFAULT_PAGES_CSV}' WHERE pages IS NULL"
    )
    conn.commit()


def _migrate_add_page(conn: sqlite3.Connection) -> None:
    """Grant a newly-added page to users who already had the full legacy set.

    When a new toggleable page ships (e.g. 'insights'), existing users' stored
    `pages` CSV won't include it, so they'd silently lose access to the new tab.
    Idempotent: only touches users whose set is a superset of the legacy full set
    and is missing the new page — leaves intentionally-restricted/empty sets and
    scoped roles (empty pages) untouched.
    """
    new_pages = [p for p in ALL_PAGES if p not in _LEGACY_FULL_PAGES]
    if not new_pages:
        return
    for row in conn.execute("SELECT user_id, pages FROM users").fetchall():
        present = {p for p in (row["pages"] or "").split(",") if p}
        if _LEGACY_FULL_PAGES <= present and not all(p in present for p in new_pages):
            merged = _pages_to_csv(present | set(new_pages))
            conn.execute(
                "UPDATE users SET pages = ? WHERE user_id = ?", (merged, row["user_id"])
            )
    conn.commit()


def _migrate_student_id_column(conn: sqlite3.Connection) -> None:
    """Add the nullable `student_id` link column to pre-existing DBs."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
    if "student_id" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN student_id INTEGER")
        conn.commit()


def _migrate_instructor_name_column(conn: sqlite3.Connection) -> None:
    """Add the nullable `instructor_name` link column to pre-existing DBs."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
    if "instructor_name" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN instructor_name TEXT")
        conn.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
    role: Role = "viewer",
    is_active: bool = True,
    student_id: int | None = None,
    instructor_name: str | None = None,
) -> User:
    """Create a new user. Raises ValueError on duplicate email or bad input.

    Pages are seeded from the role preset; an admin can adjust them afterward.
    `student_id` (student role) and `instructor_name` (instructor role) link a
    scoped account to the data it may see; each is ignored / forced None unless
    its matching role is used.
    """
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("email must be a valid address")
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    linked_student = student_id if role == "student" else None
    linked_instructor = instructor_name if role == "instructor" else None
    pages_csv = _pages_to_csv(default_pages_for_role(role))
    try:
        cur = conn.execute(
            """INSERT INTO users (email, hashed_password, is_active, role, pages,
                                  student_id, instructor_name, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (email, hash_password(password), 1 if is_active else 0, role, pages_csv,
             linked_student, linked_instructor, _now_iso()),
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


_UNSET = object()


def set_user_profile(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    display_name=_UNSET,
    email=_UNSET,
    phone=_UNSET,
    theme=_UNSET,
) -> User:
    """Partial update of self-service profile fields. Only args you pass are
    changed (pass None to clear a nullable field). Used by both the self-service
    PATCH /api/auth/me and the admin Users screen.

    Validates email (format + uniqueness) and theme. Empty strings for the
    nullable text fields are stored as NULL.
    """
    if get_user_by_id(conn, user_id) is None:
        raise LookupError(f"no user with id {user_id}")

    sets: list[str] = []
    vals: list = []

    if display_name is not _UNSET:
        sets.append("display_name = ?")
        vals.append((display_name or "").strip() or None)
    if phone is not _UNSET:
        sets.append("phone = ?")
        vals.append((phone or "").strip() or None)
    if theme is not _UNSET:
        t = (theme or "").strip().lower() or None
        if t not in (None, "dark", "light"):
            raise ValueError("theme must be 'dark', 'light', or empty")
        sets.append("theme = ?")
        vals.append(t)
    if email is not _UNSET:
        e = (email or "").strip().lower()
        if not e or "@" not in e:
            raise ValueError("email must be a valid address")
        sets.append("email = ?")
        vals.append(e)

    if not sets:
        return get_user_by_id(conn, user_id)

    vals.append(user_id)
    try:
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE user_id = ?", vals)
    except sqlite3.IntegrityError as exc:
        raise ValueError("that email is already in use") from exc
    conn.commit()
    return get_user_by_id(conn, user_id)


def set_user_role(conn: sqlite3.Connection, user_id: int, role: Role) -> User:
    """Update a user's role AND re-apply that role's page preset.

    Refuses to remove the last active admin. Callers that also want custom
    pages should call set_user_pages afterward. The scoped links are role-bound:
    switching role keeps the link that matches the new role and clears the other
    (a student_id is meaningless on an instructor account and vice-versa). To
    (re)link, call set_user_student_link / set_user_instructor_link next.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    if get_user_by_id(conn, user_id) is None:
        raise LookupError(f"no user with id {user_id}")
    if _would_remove_last_admin(conn, user_id, new_role=role):
        raise ValueError("cannot remove the last active admin")
    pages_csv = _pages_to_csv(default_pages_for_role(role))
    if role == "student":
        conn.execute(
            "UPDATE users SET role = ?, pages = ?, instructor_name = NULL WHERE user_id = ?",
            (role, pages_csv, user_id),
        )
    elif role == "instructor":
        conn.execute(
            "UPDATE users SET role = ?, pages = ?, student_id = NULL WHERE user_id = ?",
            (role, pages_csv, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET role = ?, pages = ?, student_id = NULL, instructor_name = NULL WHERE user_id = ?",
            (role, pages_csv, user_id),
        )
    conn.commit()
    return get_user_by_id(conn, user_id)


def set_user_student_link(
    conn: sqlite3.Connection, user_id: int, student_id: int
) -> User:
    """Link a `student`-role account to the training record it may view.

    Refuses if the account isn't a student (the link is meaningless otherwise).
    Existence of the student_id in the analytics tables is validated at the API
    layer, which has the analytics DB handle.
    """
    user = get_user_by_id(conn, user_id)
    if user is None:
        raise LookupError(f"no user with id {user_id}")
    if user.role != "student":
        raise ValueError("only student accounts can be linked to a student record")
    conn.execute(
        "UPDATE users SET student_id = ? WHERE user_id = ?", (student_id, user_id)
    )
    conn.commit()
    return get_user_by_id(conn, user_id)


def set_user_instructor_link(
    conn: sqlite3.Connection, user_id: int, instructor_name: str
) -> User:
    """Link an `instructor`-role account to the instructor whose students it may
    see. Refuses if the account isn't an instructor. Existence of the name in
    the flights data is validated at the API layer."""
    user = get_user_by_id(conn, user_id)
    if user is None:
        raise LookupError(f"no user with id {user_id}")
    if user.role != "instructor":
        raise ValueError("only instructor accounts can be linked to an instructor")
    conn.execute(
        "UPDATE users SET instructor_name = ? WHERE user_id = ?",
        (instructor_name, user_id),
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


def migrate_legacy_users(auth_conn: sqlite3.Connection, legacy_db_path) -> int:
    """One-time: copy accounts from the OLD location (the analytics DB, where
    users used to live) into the dedicated auth DB. Runs only when the auth DB
    has no users yet; a no-op afterward and on fresh installs. Lets existing
    deployments keep their logins when this split ships. Returns rows migrated.
    """
    legacy_db_path = Path(legacy_db_path)
    if count_users(auth_conn) > 0 or not legacy_db_path.exists():
        return 0
    legacy = sqlite3.connect(legacy_db_path)
    try:
        cur = legacy.execute("SELECT * FROM users")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    except sqlite3.Error:
        return 0  # no users table / unreadable legacy DB — nothing to migrate
    finally:
        legacy.close()
    if not rows:
        return 0
    collist = ",".join(cols)
    placeholders = ",".join("?" * len(cols))
    auth_conn.executemany(
        f"INSERT OR IGNORE INTO users ({collist}) VALUES ({placeholders})", rows
    )
    auth_conn.commit()
    return len(rows)
