"""FastAPI app factory + uvicorn entry."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import kpis as kpis_router
from .routers import meta as meta_router
from .routers import ratings as ratings_router
from .routers import students as students_router

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Provectus Analytics",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.get("/api/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(LookupError)
    def _lookup_handler(request: Request, exc: LookupError):  # noqa: ARG001
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @app.exception_handler(ValueError)
    def _value_handler(request: Request, exc: ValueError):  # noqa: ARG001
        return JSONResponse(status_code=400, content={"error": str(exc)})

    app.include_router(meta_router.router)
    app.include_router(kpis_router.router)
    app.include_router(ratings_router.router)
    app.include_router(students_router.router)

    if FRONTEND_DIST.exists():
        # Mount /assets explicitly so hashed JS/CSS bundles are served directly.
        app.mount(
            "/assets",
            StaticFiles(directory=FRONTEND_DIST / "assets"),
            name="assets",
        )
        index_html = FRONTEND_DIST / "index.html"

        # SPA fallback: any non-API path that doesn't match a real file in dist/
        # gets index.html so react-router can resolve it client-side.
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
