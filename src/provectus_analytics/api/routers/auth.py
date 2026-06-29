"""Auth endpoints: login, refresh, logout, me.

Logout is client-side only (drop the token) — there's no token denylist;
short access-token TTL (15min) bounds the risk.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...auth import deps, tokens, users
from ...auth.config import settings
from ...auth.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    # `str` not EmailStr — we don't want to expose whether an email is
    # well-formed vs whether credentials match (information leak), and the
    # strict validator rejects perfectly usable corporate TLDs (.local, etc.).
    # users.authenticate handles missing/wrong credentials uniformly.
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)
    # "Remember me" — issue a longer-lived refresh token so the session
    # survives a longer absence. Defaults off (safer on shared machines).
    remember: bool = False


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
    pages: list[str]
    is_admin: bool
    student_id: int | None = None
    instructor_name: str | None = None
    display_name: str | None = None
    phone: str | None = None
    theme: str | None = None


def _user_out(user: users.User) -> "UserOut":
    return UserOut(
        user_id=user.user_id, email=user.email, role=user.role,
        is_active=user.is_active, pages=list(user.pages), is_admin=user.is_admin,
        student_id=user.student_id, instructor_name=user.instructor_name,
        display_name=user.display_name, phone=user.phone, theme=user.theme,
    )


def _build_token_pair(user_id: int, remember: bool = False) -> TokenPair:
    return TokenPair(
        access_token=tokens.make_access_token(user_id),
        refresh_token=tokens.make_refresh_token(user_id, remember=remember),
    )


@router.post("/login", response_model=TokenPair)
@limiter.limit(settings.login_rate_limit)
def login(request: Request, body: LoginRequest) -> TokenPair:
    conn = users.connect()
    try:
        user = users.authenticate(conn, body.email, body.password)
    finally:
        conn.close()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return _build_token_pair(user.user_id, remember=body.remember)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest) -> TokenPair:
    try:
        user_id = tokens.decode_token(body.refresh_token, expected_type="refresh")
    except tokens.TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    conn = users.connect()
    try:
        user = users.get_user_by_id(conn, user_id)
    finally:
        conn.close()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist or is inactive",
        )
    # Preserve the "remember me" lifetime across silent refreshes.
    remember = tokens.refresh_token_remember(body.refresh_token)
    return _build_token_pair(user.user_id, remember=remember)


@router.post("/logout", status_code=204)
def logout(_=Depends(deps.current_active_user)) -> None:
    """Client should discard tokens. Server-side this is a no-op until/unless
    we add a token denylist (overkill for a 2-3 user app)."""
    return None


@router.get("/me", response_model=UserOut)
def me(user: users.User = Depends(deps.current_active_user)) -> UserOut:
    return _user_out(user)


class ProfileUpdateRequest(BaseModel):
    # All optional — only the fields present are changed. Self-service: a user
    # editing their OWN profile (display name, email, phone, theme preference).
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    theme: str | None = None


@router.patch("/me", response_model=UserOut)
def update_me(
    body: ProfileUpdateRequest,
    user: users.User = Depends(deps.current_active_user),
) -> UserOut:
    """Self-service profile update for the logged-in user. Only the fields the
    client sends are changed. Email collisions / bad input raise ValueError
    (→400 via the app handler)."""
    fields = body.model_dump(exclude_unset=True)
    conn = users.connect()
    try:
        updated = users.set_user_profile(conn, user.user_id, **fields)
    finally:
        conn.close()
    return _user_out(updated)


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
    conn = users.connect()
    try:
        users.change_password(
            conn, user.user_id, body.current_password, body.new_password
        )
    finally:
        conn.close()
    return None
