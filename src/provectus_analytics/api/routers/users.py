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


class CreateUserRequest(BaseModel):
    # `str` (not EmailStr) to stay consistent with the login endpoint and to
    # accept corporate TLDs; create_user does the real validation.
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    role: str = "viewer"


class UpdateUserRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None


def _out(u: users.User) -> UserOut:
    return UserOut(user_id=u.user_id, email=u.email, role=u.role, is_active=u.is_active)


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
        try:
            user = users.create_user(conn, body.email, body.password, role=body.role)
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
    """Update role and/or active state.

    `set_user_role` / `set_user_active` raise LookupError (→404) for an unknown
    id and ValueError (→400) when the change would remove the last active
    admin; both are converted by the app-level exception handlers.
    """
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        result = None
        if body.role is not None:
            result = users.set_user_role(conn, user_id, body.role)
        if body.is_active is not None:
            result = users.set_user_active(conn, user_id, body.is_active)
        if result is None:
            result = users.get_user_by_id(conn, user_id)
            if result is None:
                raise HTTPException(status_code=404, detail=f"no user with id {user_id}")
        return _out(result)
    finally:
        conn.close()
