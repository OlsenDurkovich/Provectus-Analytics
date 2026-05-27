"""Auth runtime settings, read from env.

SECRET_KEY is required in production (PROVECTUS_ENV=prod). A dev fallback
is allowed only when PROVECTUS_ENV is unset or 'dev' — and the fallback is
clearly tagged so it cannot accidentally make it to prod.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()  # idempotent; reads ./.env into os.environ if present
except ImportError:
    pass


_DEV_SECRET_TAG = "dev-only-DO-NOT-USE-IN-PROD-"


def _resolve_secret_key() -> str:
    env_val = os.getenv("SECRET_KEY")
    mode = os.getenv("PROVECTUS_ENV", "dev").lower()
    if env_val:
        return env_val
    if mode == "prod":
        raise RuntimeError(
            "SECRET_KEY must be set when PROVECTUS_ENV=prod. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
        )
    # Dev fallback — stable for the process lifetime but obvious in logs.
    return _DEV_SECRET_TAG + secrets.token_urlsafe(32)


@dataclass(frozen=True)
class _Settings:
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    login_rate_limit: str = "10/minute"
    initial_admin_email: str | None = None
    initial_admin_password: str | None = None
    env_mode: str = "dev"

    @property
    def is_prod(self) -> bool:
        return self.env_mode == "prod"


settings = _Settings(
    secret_key=_resolve_secret_key(),
    initial_admin_email=os.getenv("INITIAL_ADMIN_EMAIL"),
    initial_admin_password=os.getenv("INITIAL_ADMIN_PASSWORD"),
    env_mode=os.getenv("PROVECTUS_ENV", "dev").lower(),
)
