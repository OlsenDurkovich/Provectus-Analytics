"""JWT access + refresh tokens using PyJWT.

Token claims:
    sub  → user id (int, stringified)
    typ  → 'access' or 'refresh'
    exp  → unix timestamp
    iat  → unix timestamp
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt

from .config import settings

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """Token is invalid, expired, or the wrong type."""


def _encode(sub: int, typ: TokenType, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sub),
        "typ": typ,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key,
                      algorithm=settings.jwt_algorithm)


def make_access_token(user_id: int) -> str:
    return _encode(user_id, "access",
                   timedelta(minutes=settings.access_token_minutes))


def make_refresh_token(user_id: int) -> str:
    return _encode(user_id, "refresh",
                   timedelta(days=settings.refresh_token_days))


def decode_token(token: str, expected_type: TokenType) -> int:
    """Decode and validate a token. Returns the user_id on success."""
    try:
        payload = jwt.decode(token, settings.secret_key,
                             algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("invalid token") from exc

    if payload.get("typ") != expected_type:
        raise TokenError(f"expected {expected_type} token, got {payload.get('typ')!r}")
    sub = payload.get("sub")
    if not sub:
        raise TokenError("missing sub claim")
    try:
        return int(sub)
    except (ValueError, TypeError) as exc:
        raise TokenError("invalid sub claim") from exc
