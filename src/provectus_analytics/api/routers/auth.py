"""Auth endpoints: login, refresh, logout, me.

Logout is client-side only (drop the token) — there's no token denylist;
short access-token TTL (15min) bounds the risk.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ... import db as _db
from ...auth import deps, tokens, users
from ...auth.config import settings
from ...auth.rate_limit import limiter
from .. import queries as web_data

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    # `str` not EmailStr — we don't want to expose whether an email is
    # well-formed vs whether credentials match (information leak), and the
    # strict validator rejects perfectly usable corporate TLDs (.local, etc.).
    # users.authenticate handles missing/wrong credentials uniformly.
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserOut(BaseModel):
    user_id: int
    email: str
    role: str
    is_active: bool


def _build_token_pair(user_id: int) -> TokenPair:
    return TokenPair(
        access_token=tokens.make_access_token(user_id),
        refresh_token=tokens.make_refresh_token(user_id),
    )


@router.post("/login", response_model=TokenPair)
@limiter.limit(settings.login_rate_limit)
def login(request: Request, body: LoginRequest) -> TokenPair:
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        user = users.authenticate(conn, body.email, body.password)
    finally:
        conn.close()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return _build_token_pair(user.user_id)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest) -> TokenPair:
    try:
        user_id = tokens.decode_token(body.refresh_token, expected_type="refresh")
    except tokens.TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        user = users.get_user_by_id(conn, user_id)
    finally:
        conn.close()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist or is inactive",
        )
    return _build_token_pair(user.user_id)


@router.post("/logout", status_code=204)
def logout(_=Depends(deps.current_active_user)) -> None:
    """Client should discard tokens. Server-side this is a no-op until/unless
    we add a token denylist (overkill for a 2-3 user app)."""
    return None


@router.get("/me", response_model=UserOut)
def me(user: users.User = Depends(deps.current_active_user)) -> UserOut:
    return UserOut(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


@router.post("/change-password", status_code=204)
def change_password_endpoint(
    body: ChangePasswordRequest,
    user: users.User = Depends(deps.current_active_user),
) -> None:
    """Self-service password change for the logged-in user.

    users.change_password raises ValueError (→400) on wrong current password
    or a too-short new one; the app-level handler converts it.
    """
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        users.change_password(
            conn, user.user_id, body.current_password, body.new_password
        )
    finally:
        conn.close()
    return None
