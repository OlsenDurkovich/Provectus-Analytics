"""Security-headers middleware (Phase 14).

Defaults are tuned for a small internal analytics app:
    - No third-party iframes embed us (X-Frame-Options DENY)
    - No MIME sniffing (X-Content-Type-Options nosniff)
    - HSTS on for prod only (avoid making local dev painful with cached
      strict-transport pinning)
    - Referrer-Policy: same-origin (don't leak our paths to outbound links)
    - Permissions-Policy: empty allow lists for the things we never use

CSP is a separate problem because Vite-built React apps need inline styles
sometimes and we serve hashed assets. A conservative CSP that allows self +
the dev domain shouldn't break anything; turn it tighter once we've watched
the report-only logs.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, hsts: bool = False):
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        # Browsers fall back to MIME-sniffing if not told otherwise; force them
        # to trust our content-type and nothing else.
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "same-origin")
        h.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        # CSP — self for everything; allow data: URIs for tiny inline images
        # (favicons, sprites), and unsafe-inline styles because the Vite build
        # emits some inline <style> attributes. JS is hash-pinned so we can
        # stay strict there.
        h.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'",
        )
        if self._hsts:
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response
