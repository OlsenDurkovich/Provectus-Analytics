"""Phase 11 auth — JWT-based session auth backed by the same SQLite DB.

Public surface re-exported here for convenience.
"""
from .config import settings
from .deps import current_active_user, current_admin_user
from .users import User, ensure_users_table, seed_initial_admin

__all__ = [
    "settings",
    "current_active_user",
    "current_admin_user",
    "User",
    "ensure_users_table",
    "seed_initial_admin",
]
