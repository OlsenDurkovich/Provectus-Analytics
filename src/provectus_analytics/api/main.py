"""FastAPI app factory + uvicorn entry."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .. import db as _db
from ..auth import ensure_users_table, seed_initial_admin
from ..auth.config import settings as auth_settings
from ..auth.deps import current_active_user
from ..auth.rate_limit import limiter
from .routers import auth as auth_router
from .routers import flights as flights_router
from .routers import instructors as instructors_router
from .routers import kpis as kpis_router
from .routers import meta as meta_router
from .routers import ratings as ratings_router
from .routers import students as students_router
from .routers import upload as upload_router

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


def _bootstrap_auth() -> None:
    """One-time setup at startup: ensure users table + optional admin seed."""
    from . import queries as web_data  # local import — queries imports schema
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        ensure_users_table(conn)
        seed_initial_admin(
            conn,
            auth_settings.initial_admin_email,
            auth_settings.initial_admin_password,
        )
    finally:
        conn.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Provectus Analytics",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Rate limiting (auth login). Limiter is module-level so route decorators
    # can reference it at import time.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    _bootstrap_auth()

    @app.get("/api/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(LookupError)
    def _lookup_handler(request: Request, exc: LookupError):  # noqa: ARG001
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @app.exception_handler(ValueError)
    def _value_handler(request: Request, exc: ValueError):  # noqa: ARG001
        return JSONResponse(status_code=400, content={"error": str(exc)})

    # Auth endpoints are public (login + refresh). The other endpoints on the
    # auth router (logout, me) declare their own auth dependency.
    app.include_router(auth_router.router)

    # All data routers require an authenticated user.
    protected = [Depends(current_active_user)]
    app.include_router(meta_router.router,        dependencies=protected)
    app.include_router(kpis_router.router,        dependencies=protected)
    app.include_router(ratings_router.router,     dependencies=protected)
    app.include_router(students_router.router,    dependencies=protected)
    app.include_router(instructors_router.router, dependencies=protected)
    app.include_router(flights_router.router,     dependencies=protected)
    app.include_router(upload_router.router,      dependencies=protected)

    if FRONTEND_DIST.exists():
        # Mount /assets explicitly so hashed JS/CSS bundles are served directly.
        app.mount(
            "/assets",
            StaticFiles(directory=FRONTEND_DIST / "assets"),
            name="assets",
        )
        index_html = FRONTEND_DIST / "index.html"

        # SPA fallback: any non-API path that doesn't match a real file in dist/
        # gets index.html so react-router can resolve it client-side. This is
        # public (the bundle itself isn't sensitive — the React app does its
        # own auth check on mount and redirects to /login when unauthenticated).
        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index_html)

    return app


app = create_app()
