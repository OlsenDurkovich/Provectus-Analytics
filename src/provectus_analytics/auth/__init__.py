"""Phase 11 auth — JWT-based session auth backed by a DEDICATED auth SQLite DB.

User accounts + per-user settings live in their own database (see users.AUTH_DB),
separate from the regenerable analytics DB, so an analytics rebuild can never
wipe them. Public surface re-exported here for convenience.
"""
from .config import settings
from .deps import current_active_user, current_admin_user
from .users import (
    User,
    connect,
    ensure_users_table,
    migrate_legacy_users,
    seed_initial_admin,
)

__all__ = [
    "settings",
    "current_active_user",
    "current_admin_user",
    "User",
    "connect",
    "ensure_users_table",
    "migrate_legacy_users",
    "seed_initial_admin",
]
