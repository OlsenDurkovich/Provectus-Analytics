"""Admin-only user management: list / create / update users.

Mounted in main.py with a router-level `current_admin_user` dependency, so
every endpoint here already requires an authenticated admin.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ... import db as _db
from ...auth import users
from .. import queries as web_data

router = APIRouter(prefix="/api/users", tags=["users"])


class UserOut(BaseModel):
    user_id: int
    email: str
    role: str
    is_active: bool
    pages: list[str]
    is_admin: bool
    student_id: int | None = None


class StudentRecord(BaseModel):
    """A pickable training record, for linking a student account."""
    student_id: int
    name: str
    email: str | None = None


class CreateUserRequest(BaseModel):
    # `str` (not EmailStr) to stay consistent with the login endpoint and to
    # accept corporate TLDs; create_user does the real validation.
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    role: str = "viewer"
    student_id: int | None = None  # required (and only used) when role == student


class UpdateUserRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    pages: list[str] | None = None
    new_password: str | None = None  # admin reset (no current-password check)
    student_id: int | None = None    # (re)link a student account to a record


def _out(u: users.User) -> UserOut:
    return UserOut(
        user_id=u.user_id, email=u.email, role=u.role,
        is_active=u.is_active, pages=list(u.pages), is_admin=u.is_admin,
        student_id=u.student_id,
    )


def _assert_student_exists(conn, student_id: int) -> None:
    """Reject a link to a student_id that isn't in the analytics data."""
    row = conn.execute(
        "SELECT 1 FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=422, detail=f"no student record with id {student_id}"
        )


@router.get("/student-records", response_model=list[StudentRecord])
def list_student_records() -> list[StudentRecord]:
    """Distinct student records an admin can link a student account to."""
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        rows = conn.execute(
            "SELECT student_id, fsp_display_name, email FROM students "
            "ORDER BY fsp_display_name"
        ).fetchall()
        return [
            StudentRecord(student_id=r["student_id"], name=r["fsp_display_name"], email=r["email"])
            for r in rows
        ]
    finally:
        conn.close()


@router.get("", response_model=list[UserOut])
def list_users_endpoint() -> list[UserOut]:
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        return [_out(u) for u in users.list_users(conn)]
    finally:
        conn.close()


@router.post("", response_model=UserOut, status_code=201)
def create_user_endpoint(body: CreateUserRequest) -> UserOut:
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        if body.role == "student":
            if body.student_id is None:
                raise HTTPException(
                    status_code=422,
                    detail="a student account must be linked to a student record",
                )
            _assert_student_exists(conn, body.student_id)
        try:
            user = users.create_user(
                conn, body.email, body.password,
                role=body.role, student_id=body.student_id,
            )
        except ValueError as exc:
            # 409 for the duplicate-email case, 422 for everything else
            # (bad role, weak password, malformed email).
            code = 409 if "already exists" in str(exc) else 422
            raise HTTPException(status_code=code, detail=str(exc)) from exc
        return _out(user)
    finally:
        conn.close()


@router.patch("/{user_id}", response_model=UserOut)
def update_user_endpoint(user_id: int, body: UpdateUserRequest) -> UserOut:
    """Update role, page access, active state, student link, and/or password.

    Order matters: setting `role` re-applies that role's page preset and clears
    any stale student link, so an explicit `pages` or `student_id` (applied
    next) can override in the same request. The `users.*` helpers raise
    LookupError (→404) for an unknown id and ValueError (→400) for bad input /
    last-admin guard; the app-level handlers convert both.
    """
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        if body.student_id is not None:
            _assert_student_exists(conn, body.student_id)
        result = None
        if body.role is not None:
            result = users.set_user_role(conn, user_id, body.role)
        if body.student_id is not None:
            result = users.set_user_student_link(conn, user_id, body.student_id)
        if body.pages is not None:
            result = users.set_user_pages(conn, user_id, body.pages)
        if body.is_active is not None:
            result = users.set_user_active(conn, user_id, body.is_active)
        if body.new_password is not None:
            users.admin_reset_password(conn, user_id, body.new_password)
            result = users.get_user_by_id(conn, user_id)
        if result is None:
            result = users.get_user_by_id(conn, user_id)
            if result is None:
                raise HTTPException(status_code=404, detail=f"no user with id {user_id}")
        return _out(result)
    finally:
        conn.close()
