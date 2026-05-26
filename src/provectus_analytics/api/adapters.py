"""Adapters bridge web/data.py outputs to api/schemas.py.

This is the only module that imports from web/data.py. Routers import from here.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..web import data as web_data
from . import schemas


def range_cutoff(range_key: schemas.RangeKey, today: date | None = None) -> date | None:
    today = today or date.today()
    if range_key == "30d":
        return today - timedelta(days=30)
    if range_key == "90d":
        return today - timedelta(days=90)
    if range_key == "6mo":
        return today - timedelta(days=180)
    if range_key == "12mo":
        return today - timedelta(days=365)
    if range_key == "ytd":
        return date(today.year, 1, 1)
    if range_key == "all":
        return None
    raise ValueError(f"unknown range_key: {range_key}")


def meta() -> schemas.Meta:
    counts = web_data.row_counts(web_data.DEFAULT_DB)
    live_count = web_data.is_live_data(web_data.DEFAULT_DB)
    flight, invoice = web_data._has_real_exports()
    mode: schemas.Meta.__annotations__["mode"]  # noqa: F841 — for type hinting only
    is_real = flight is not None and invoice is not None and live_count > 0
    return schemas.Meta(
        mode="real" if is_real else "synthetic",
        liveClientCount=live_count,
        dataState=schemas.DataState(
            flights=counts.get("flights", 0),
            invoices=counts.get("invoices", 0),
            students=counts.get("students", 0),
            surveys=counts.get("surveys", 0),
            overrides=counts.get("flight_overrides", 0),
        ),
    )
