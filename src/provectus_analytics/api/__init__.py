"""FastAPI app — replaces the legacy Dash web layer.

Run dev:
    uvicorn provectus_analytics.api.main:app --reload --port 8050
"""
from .main import app, create_app

__all__ = ["app", "create_app"]
