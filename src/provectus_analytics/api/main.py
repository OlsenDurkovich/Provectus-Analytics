"""FastAPI app factory + uvicorn entry."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import kpis as kpis_router
from .routers import meta as meta_router

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

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


app = create_app()
