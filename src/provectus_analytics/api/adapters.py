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


_RATING_DISPLAY = {
    "PPL": "Private Pilot",
    "IFR": "Instrument",
    "COM": "Commercial SE",
    "AMEL": "Multi-Engine",
    "CFI": "CFI",
    "CFII": "CFII",
    "MEI": "MEI",
}


def rating_bars(
    metric: schemas.MetricKey, range_key: schemas.RangeKey
) -> list[schemas.RatingBarPoint]:
    from .. import norms

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        norm_rows = norms.compute_rating_norms(conn)
    finally:
        conn.close()

    metric_attrs = {
        "hours": ("median_hours", "p25_hours", "p75_hours"),
        "cost": ("median_cost", "p25_cost", "p75_cost"),
        "days": ("median_days", "p25_days", "p75_days"),
    }
    med_a, p25_a, p75_a = metric_attrs[metric]

    out: list[schemas.RatingBarPoint] = []
    for n in norm_rows:
        out.append(
            schemas.RatingBarPoint(
                code=n.rating,
                name=_RATING_DISPLAY.get(n.rating, n.rating),
                n=n.n_raw,
                median=float(getattr(n, med_a) or 0),
                p25=float(getattr(n, p25_a) or 0),
                p75=float(getattr(n, p75_a) or 0),
            )
        )
    return out


def ratings_completed(range_key: schemas.RangeKey) -> list[schemas.RatingsCompletedRow]:
    cutoff = range_cutoff(range_key)
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        if cutoff:
            rows = conn.execute(
                """SELECT r.code, COUNT(*) FROM milestones m
                   JOIN enrollments e USING (enrollment_id)
                   JOIN ratings r USING (rating_id)
                   WHERE m.milestone_name='checkride' AND m.milestone_date >= ?
                   GROUP BY r.code""",
                (cutoff.isoformat(),),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT r.code, COUNT(*) FROM milestones m
                   JOIN enrollments e USING (enrollment_id)
                   JOIN ratings r USING (rating_id)
                   WHERE m.milestone_name='checkride'
                   GROUP BY r.code"""
            ).fetchall()
    finally:
        conn.close()
    return [schemas.RatingsCompletedRow(rating=code, count=cnt) for code, cnt in rows]


def heatmap(range_key: schemas.RangeKey) -> schemas.Heatmap:
    """7×12 day-of-week × time-of-day matrix.

    FSP doesn't expose time-of-day. Until it does, count distinct flights per
    day-of-week and spread evenly across the 12 buckets — preserves the design's
    visual density per row without inventing hour-level information.
    """
    from datetime import datetime

    cutoff = range_cutoff(range_key)
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        if cutoff:
            data_rows = conn.execute(
                "SELECT flight_date FROM flights WHERE flight_date >= ?",
                (cutoff.isoformat(),),
            ).fetchall()
        else:
            data_rows = conn.execute("SELECT flight_date FROM flights").fetchall()
    finally:
        conn.close()

    buckets = ["6a", "8a", "10a", "12p", "2p", "4p", "6p", "8p", "10p", "12a", "2a", "4a"]
    rows = [[0.0] * 12 for _ in range(7)]
    for (date_s,) in data_rows:
        if not date_s:
            continue
        try:
            dow = datetime.fromisoformat(date_s).weekday()
        except ValueError:
            continue
        for col in range(12):
            rows[dow][col] += 1 / 12
    return schemas.Heatmap(rows=rows, buckets=buckets)


def rating_detail(code: schemas.RatingCode) -> schemas.Rating:
    from .. import norms as _norms

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        norm_rows = _norms.compute_rating_norms(conn)
    finally:
        conn.close()

    for n in norm_rows:
        if n.rating == code:
            return schemas.Rating(
                code=code,
                name=_RATING_DISPLAY.get(code, code),
                n=n.n_raw,
                medianHrs=float(n.median_hours or 0),
                p25Hrs=float(n.p25_hours or 0),
                p75Hrs=float(n.p75_hours or 0),
                medianCost=float(n.median_cost or 0),
                p25Cost=float(n.p25_cost or 0),
                p75Cost=float(n.p75_cost or 0),
                medianDays=float(n.median_days or 0),
                p25Days=float(n.p25_days or 0),
                p75Days=float(n.p75_days or 0),
                lowSample=bool(n.low_sample_flag),
            )
    raise LookupError(f"rating not found: {code}")


def clients(
    range_key: schemas.RangeKey, rating: schemas.RatingCode | None = None
) -> list[schemas.ClientRow]:
    from datetime import date as _date

    from .. import norms as _norms

    cutoff = range_cutoff(range_key)

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        median_hours_by_rating = {
            n.rating: n.median_hours for n in _norms.compute_rating_norms(conn)
        }

        sql = """
            SELECT s.student_id, s.fsp_display_name, r.code AS rating_code,
                   COALESCE(SUM(f.length_hrs), 0) AS hours,
                   MIN(f.flight_date) AS first_flight,
                   MAX(f.flight_date) AS last_flight,
                   EXISTS (
                       SELECT 1 FROM milestones m
                       JOIN enrollments e2 USING (enrollment_id)
                       WHERE e2.student_id = s.student_id
                         AND e2.rating_id = r.rating_id
                         AND m.milestone_name = 'checkride'
                   ) AS has_checkride
            FROM students s
            JOIN enrollments e USING (student_id)
            JOIN ratings r USING (rating_id)
            LEFT JOIN flights f
              ON f.student_id = s.student_id AND f.enrollment_id = e.enrollment_id
            WHERE 1=1
        """
        params: list = []
        if cutoff:
            sql += " AND (f.flight_date >= ? OR f.flight_date IS NULL)"
            params.append(cutoff.isoformat())
        if rating:
            sql += " AND r.code = ?"
            params.append(rating)
        sql += " GROUP BY s.student_id, r.code ORDER BY s.fsp_display_name"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    out: list[schemas.ClientRow] = []
    today = _date.today()
    for row in rows:
        rating_code = row["rating_code"]
        hours = float(row["hours"] or 0)
        median = median_hours_by_rating.get(rating_code) or 0.0
        progress = round(min(hours / median, 1.5), 3) if median > 0 else 0.0

        first = row["first_flight"]
        days = 0
        if first:
            try:
                days = (today - _date.fromisoformat(first)).days
            except ValueError:
                days = 0

        if row["has_checkride"]:
            status = "Completed"
        elif progress >= 0.9:
            status = "On checkride"
        else:
            status = "Active"

        out.append(
            schemas.ClientRow(
                id=str(row["student_id"]),
                name=row["fsp_display_name"] or "Unknown",
                rating=rating_code,
                progressPct=progress,
                hoursToDate=hours,
                daysEnrolled=int(days),
                status=status,
            )
        )
    return out
