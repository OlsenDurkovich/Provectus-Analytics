"""Password hashing using bcrypt directly (passlib's bcrypt backend has known
compat issues with bcrypt>=4.0). Bcrypt's stored hash format includes the
salt + cost factor, so we don't need to manage salt separately.
"""
from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """Hash a plaintext password. Returns a UTF-8 string for SQLite storage."""
    if not plain:
        raise ValueError("password must be non-empty")
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext against a bcrypt hash. Returns False on any error
    (mismatched, malformed, empty) — never raises."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
