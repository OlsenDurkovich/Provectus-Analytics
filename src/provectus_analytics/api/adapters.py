"""Adapters bridge web/data.py outputs to api/schemas.py.

This is the only module that imports from web/data.py. Routers import from here.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from ..web import data as web_data
from . import schemas


_RANGE_SUB = {
    "30d": "last 30 days",
    "90d": "last 90 days",
    "6mo": "last 6 months",
    "12mo": "last 12 months",
    "ytd": "year to date",
    "all": "all time",
}


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


def kpis(range_key: schemas.RangeKey) -> list[schemas.Kpi]:
    cutoff = range_cutoff(range_key)
    cutoff_iso = cutoff.isoformat() if cutoff else None

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        if cutoff_iso:
            ratings_completed = conn.execute(
                "SELECT COUNT(*) FROM milestones "
                "WHERE milestone_name='checkride' AND milestone_date >= ?",
                (cutoff_iso,),
            ).fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(DISTINCT student_id) FROM flights WHERE flight_date >= ?",
                (cutoff_iso,),
            ).fetchone()[0]
            hours = conn.execute(
                "SELECT COALESCE(SUM(length_hrs),0) FROM flights WHERE flight_date >= ?",
                (cutoff_iso,),
            ).fetchone()[0]
            billed = conn.execute(
                "SELECT COALESCE(SUM(i.amount),0) FROM invoices i "
                "JOIN flights f ON f.flight_id = i.flight_id "
                "WHERE f.flight_date >= ?",
                (cutoff_iso,),
            ).fetchone()[0]
        else:
            ratings_completed = conn.execute(
                "SELECT COUNT(*) FROM milestones WHERE milestone_name='checkride'"
            ).fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(DISTINCT student_id) FROM flights"
            ).fetchone()[0]
            hours = conn.execute(
                "SELECT COALESCE(SUM(length_hrs),0) FROM flights"
            ).fetchone()[0]
            billed = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM invoices"
            ).fetchone()[0]
    finally:
        conn.close()

    sub = _RANGE_SUB[range_key]
    return [
        schemas.Kpi(
            key="ratings_completed", label="Ratings completed",
            value=str(ratings_completed), sub=sub, delta=0.0, positive=True,
            spark=[float(ratings_completed)] * 8, color="#6E56F8",
        ),
        schemas.Kpi(
            key="active_clients", label="Active clients",
            value=str(active), sub=sub, delta=0.0, positive=True,
            spark=[float(active)] * 8, color="#3DD68C",
        ),
        schemas.Kpi(
            key="flight_hours", label="Flight hours",
            value=f"{hours:,.0f}", sub=sub, delta=0.0, positive=True,
            spark=[float(hours)] * 8, color="#22D3EE",
        ),
        schemas.Kpi(
            key="total_billed", label="Total billed",
            value=f"${billed:,.0f}", sub=sub, delta=0.0, positive=True,
            spark=[float(billed)] * 8, color="#F59E0B",
        ),
    ]
