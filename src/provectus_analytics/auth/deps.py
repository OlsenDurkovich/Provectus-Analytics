"""FastAPI dependencies for resolving the current authenticated user."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .. import db as _db
from . import tokens, users
from .config import settings

# auto_error=False lets us throw a 401 (vs FastAPI's default 403) with a
# clearer message when the Authorization header is missing.
_bearer = HTTPBearer(auto_error=False)


def _get_db(request: Request):
    """Pull DB path from queries.DEFAULT_DB (lazy import dodges circularity)."""
    from ..api import queries  # local import — queries imports schema/ingest
    conn = _db.connect(queries.DEFAULT_DB)
    try:
        yield conn
    finally:
        conn.close()


def current_active_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    conn=Depends(_get_db),
) -> users.User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = tokens.decode_token(creds.credentials, expected_type="access")
    except tokens.TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = users.get_user_by_id(conn, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist or is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def current_admin_user(user: users.User = Depends(current_active_user)) -> users.User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
