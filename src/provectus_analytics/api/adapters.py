"""Adapters bridge web/data.py outputs to api/schemas.py.

This is the only module that imports from web/data.py. Routers import from here.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from . import queries as web_data
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


def _kpi_window(conn: sqlite3.Connection, lo: date | None, hi: date | None) -> tuple[int, int, float, float]:
    """Return (ratings_completed, active, hours, billed) for [lo, hi).

    lo=None means no lower bound; hi=None means no upper bound (i.e., open-ended to today).
    For all 4 metrics, more-is-better — % delta direction is consistent across them.
    """
    where = []
    params: list = []
    if lo is not None:
        where.append("flight_date >= ?")
        params.append(lo.isoformat())
    if hi is not None:
        where.append("flight_date < ?")
        params.append(hi.isoformat())
    flight_where = (" WHERE " + " AND ".join(where)) if where else ""

    # Milestones use milestone_date, not flight_date.
    ms_where = []
    ms_params: list = []
    if lo is not None:
        ms_where.append("milestone_date >= ?")
        ms_params.append(lo.isoformat())
    if hi is not None:
        ms_where.append("milestone_date < ?")
        ms_params.append(hi.isoformat())
    ms_clause = (" AND " + " AND ".join(ms_where)) if ms_where else ""

    ratings_completed = conn.execute(
        f"SELECT COUNT(*) FROM milestones WHERE milestone_name='checkride'{ms_clause}",
        ms_params,
    ).fetchone()[0]
    active = conn.execute(
        f"SELECT COUNT(DISTINCT student_id) FROM flights{flight_where}",
        params,
    ).fetchone()[0]
    hours = conn.execute(
        f"SELECT COALESCE(SUM(length_hrs),0) FROM flights{flight_where}",
        params,
    ).fetchone()[0]
    # Invoices join through flights so the window applies to the *flown* date, not the
    # invoice date — matches how the dashboard frames "revenue from work done in window".
    if where:
        billed = conn.execute(
            "SELECT COALESCE(SUM(i.amount),0) FROM invoices i "
            "JOIN flights f ON f.flight_id = i.flight_id "
            "WHERE " + " AND ".join(w.replace("flight_date", "f.flight_date") for w in where),
            params,
        ).fetchone()[0]
    else:
        billed = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM invoices"
        ).fetchone()[0]
    return int(ratings_completed), int(active), float(hours), float(billed)


def _pct_delta(current: float, prior: float) -> float:
    """Return % change from prior to current, rounded to 3 decimals.

    Returns 0.0 if prior is 0 (avoids div-by-zero and bogus +infinity deltas
    for KPIs that simply didn't exist in the prior window).
    """
    if prior == 0:
        return 0.0
    return round((current - prior) / prior, 3)


def kpis(range_key: schemas.RangeKey, today: date | None = None) -> list[schemas.Kpi]:
    today = today or date.today()
    cutoff = range_cutoff(range_key, today)

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        cur_ratings, cur_active, cur_hours, cur_billed = _kpi_window(conn, cutoff, None)

        # Prior window: equal-length stretch immediately before the current cutoff.
        # For "all" there's no prior — leave deltas at 0.
        if cutoff is None:
            prior_ratings = prior_active = 0
            prior_hours = prior_billed = 0.0
            has_prior = False
        else:
            window_days = (today - cutoff).days
            prior_lo = cutoff - timedelta(days=window_days)
            prior_hi = cutoff
            prior_ratings, prior_active, prior_hours, prior_billed = _kpi_window(
                conn, prior_lo, prior_hi
            )
            has_prior = True
    finally:
        conn.close()

    sub = _RANGE_SUB[range_key]
    if has_prior:
        d_ratings = _pct_delta(cur_ratings, prior_ratings)
        d_active = _pct_delta(cur_active, prior_active)
        d_hours = _pct_delta(cur_hours, prior_hours)
        d_billed = _pct_delta(cur_billed, prior_billed)
    else:
        d_ratings = d_active = d_hours = d_billed = 0.0

    return [
        schemas.Kpi(
            key="ratings_completed", label="Ratings completed",
            value=str(cur_ratings), sub=sub, delta=d_ratings, positive=d_ratings >= 0,
            spark=[float(cur_ratings)] * 8, color="#6E56F8",
        ),
        schemas.Kpi(
            key="active_clients", label="Active clients",
            value=str(cur_active), sub=sub, delta=d_active, positive=d_active >= 0,
            spark=[float(cur_active)] * 8, color="#3DD68C",
        ),
        schemas.Kpi(
            key="flight_hours", label="Flight hours",
            value=f"{cur_hours:,.0f}", sub=sub, delta=d_hours, positive=d_hours >= 0,
            spark=[float(cur_hours)] * 8, color="#22D3EE",
        ),
        schemas.Kpi(
            key="total_billed", label="Total billed",
            value=f"${cur_billed:,.0f}", sub=sub, delta=d_billed, positive=d_billed >= 0,
            spark=[float(cur_billed)] * 8, color="#F59E0B",
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


def rating_cohort(code: schemas.RatingCode) -> list[schemas.RatingCohortMember]:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT e.student_id, s.fsp_display_name,
                      m.cumulative_hours, m.cumulative_cost, m.days_from_rating_start
               FROM milestones m
               JOIN enrollments e USING (enrollment_id)
               JOIN ratings r USING (rating_id)
               JOIN students s USING (student_id)
               WHERE m.milestone_name = 'checkride' AND r.code = ?
               ORDER BY m.cumulative_hours""",
            (code,),
        ).fetchall()
    finally:
        conn.close()
    return [
        schemas.RatingCohortMember(
            studentId=str(row["student_id"]),
            name=row["fsp_display_name"] or "Unknown",
            hours=float(row["cumulative_hours"] or 0),
            cost=float(row["cumulative_cost"] or 0),
            days=int(row["days_from_rating_start"] or 0),
        )
        for row in rows
    ]


def student_detail(student_id: str) -> schemas.StudentDetail:
    from .. import norms as _norms

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT student_id, fsp_display_name FROM students WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        if not row:
            raise LookupError(f"student {student_id}")
        name = row["fsp_display_name"] or "Unknown"
        median_by_rating = {
            n.rating: n for n in _norms.compute_rating_norms(conn)
        }
        per_rating_rows = conn.execute(
            """SELECT r.code AS rating,
                      COALESCE(SUM(f.length_hrs), 0) AS hours,
                      COALESCE((
                          SELECT SUM(i.amount) FROM invoices i
                          JOIN flights f2 ON f2.flight_id = i.flight_id
                          WHERE f2.student_id = ? AND f2.enrollment_id = e.enrollment_id
                      ), 0) AS cost,
                      MIN(f.flight_date) AS first_flight,
                      MAX(f.flight_date) AS last_flight
               FROM enrollments e
               JOIN ratings r USING (rating_id)
               LEFT JOIN flights f
                 ON f.student_id = e.student_id AND f.enrollment_id = e.enrollment_id
               WHERE e.student_id = ?
               GROUP BY r.code, r.sort_order, e.enrollment_id
               ORDER BY r.sort_order""",
            (student_id, student_id),
        ).fetchall()
    finally:
        conn.close()

    df = web_data.student_trajectory(str(web_data.DEFAULT_DB), name)
    timeline: list[schemas.StudentTimelinePoint] = []
    for rating_code, group in df.groupby("rating", sort=False):
        ms = [
            schemas.StudentTimelineMilestone(
                name=r["milestone"], date=r["milestone_date"] or ""
            )
            for _, r in group.iterrows()
        ]
        if not ms:
            continue
        timeline.append(
            schemas.StudentTimelinePoint(
                rating=rating_code,
                start=ms[0].date,
                end=ms[-1].date if len(ms) > 1 else None,
                milestones=ms,
            )
        )

    from datetime import date as _date
    today = _date.today()
    per_rating: list[schemas.StudentPerRating] = []
    for row in per_rating_rows:
        rating_code = row["rating"]
        hours = float(row["hours"] or 0)
        cost = float(row["cost"] or 0)
        first = row["first_flight"]
        last = row["last_flight"]
        days = 0
        if first and last:
            try:
                days = (_date.fromisoformat(last) - _date.fromisoformat(first)).days
            except ValueError:
                days = 0
        norm = median_by_rating.get(rating_code)
        per_rating.append(
            schemas.StudentPerRating(
                rating=rating_code,
                name=_RATING_DISPLAY.get(rating_code, rating_code),
                n=norm.n_raw if norm else 0,
                hours=hours if hours else None,
                cost=cost if cost else None,
                days=days if days else None,
                medianHrs=float(norm.median_hours) if norm and norm.median_hours else None,
                medianCost=float(norm.median_cost) if norm and norm.median_cost else None,
                medianDays=float(norm.median_days) if norm and norm.median_days else None,
                lowSample=bool(norm.low_sample_flag) if norm else False,
            )
        )

    return schemas.StudentDetail(
        id=student_id,
        name=name,
        timeline=timeline,
        perRating=per_rating,
    )


_BILLING_VALUES = {"Hobbs", "Tach", "Block"}
_ACCLASS_VALUES = {"SE_BASIC", "SE_COMPLEX", "ME_BASIC", "HP_COMPLEX"}


def _norm_billing(v) -> schemas.BillingKind:
    return v if v in _BILLING_VALUES else "—"


# Map legacy / alternate aircraft-class tokens onto the canonical schema set.
# The classifier historically emitted "ME" for multi-engine; the schema/UI use
# "ME_BASIC". Without this alias, _norm_acclass silently relabeled every
# multi-engine flight as SE_BASIC in the Flights tab.
_ACCLASS_ALIASES = {"ME": "ME_BASIC"}


def _norm_acclass(v) -> schemas.AcClass:
    v = _ACCLASS_ALIASES.get(v, v)
    return v if v in _ACCLASS_VALUES else "SE_BASIC"


def _flight_by_id(flight_id: int) -> schemas.FlightRow | None:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        row = conn.execute(
            """SELECT f.flight_id, f.flight_date, f.client_raw, f.instructor,
                      f.reservation_type, f.billing_category, f.aircraft_class,
                      f.is_ground_lesson, f.length_hrs,
                      COALESCE(
                          (SELECT SUM(amount) FROM invoices i WHERE i.flight_id = f.flight_id),
                          0
                      ) AS cost
               FROM flights f
               WHERE f.flight_id = ?""",
            (flight_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    (
        fid,
        date,
        client,
        instructor,
        rtype,
        billing,
        acclass,
        is_ground,
        hours,
        cost,
    ) = row
    return schemas.FlightRow(
        id=str(fid),
        date=date or "",
        client=client or "",
        instructor=instructor or "",
        type=rtype or "Dual flight training",
        billing=_norm_billing(billing),
        acClass=_norm_acclass(acclass),
        ground="Ground (1)" if is_ground else "Flight (0)",
        hours=float(hours or 0),
        cost=float(cost or 0),
    )


def update_flight(flight_id: str, patch: schemas.FlightUpdate) -> schemas.FlightRow:
    from .. import ingest, milestones, partition

    try:
        fid_int = int(flight_id)
    except (TypeError, ValueError) as exc:
        raise LookupError(f"flight {flight_id}") from exc

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        exists = conn.execute(
            "SELECT 1 FROM flights WHERE flight_id = ?", (fid_int,)
        ).fetchone()
        if not exists:
            raise LookupError(f"flight {flight_id}")
        if patch.value is None:
            ingest.clear_flight_override(conn, fid_int, patch.field)
            # Clear semantics: reset to a sentinel that mirrors "no override".
            # is_ground_lesson is NOT NULL (default 0); other fields are nullable.
            sentinel = 0 if patch.field == "is_ground_lesson" else None
            conn.execute(
                f"UPDATE flights SET {patch.field} = ? WHERE flight_id = ?",
                (sentinel, fid_int),
            )
        else:
            raw = patch.value
            if patch.field == "is_ground_lesson":
                raw = 1 if bool(raw) else 0
            ingest.set_flight_override(conn, fid_int, patch.field, raw)
            ingest.apply_overrides(conn)
        partition.partition_flights(conn)
        milestones.compute_milestones(conn)
        conn.commit()
    finally:
        conn.close()
    web_data.clear_caches()

    row = _flight_by_id(fid_int)
    if row is None:
        raise LookupError(f"flight {flight_id}")
    return row


def flights(filter: dict) -> list[schemas.FlightRow]:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        sql = """
            SELECT f.flight_id, f.flight_date, f.client_raw, f.instructor,
                   f.reservation_type, f.billing_category, f.aircraft_class,
                   f.is_ground_lesson, f.length_hrs,
                   COALESCE(
                       (SELECT SUM(amount) FROM invoices i WHERE i.flight_id = f.flight_id),
                       0
                   ) AS cost
            FROM flights f
            WHERE 1=1
        """
        params: list = []
        if filter.get("instructor"):
            sql += " AND f.instructor = ?"
            params.append(filter["instructor"])
        if filter.get("client"):
            sql += " AND f.client_raw LIKE ?"
            params.append(f"%{filter['client']}%")
        if filter.get("ground") == "Flight (0)":
            sql += " AND COALESCE(f.is_ground_lesson, 0) = 0"
        elif filter.get("ground") == "Ground (1)":
            sql += " AND COALESCE(f.is_ground_lesson, 0) = 1"
        sort = filter.get("sort") or "-date"
        order = "DESC" if sort.startswith("-") else "ASC"
        sql += f" ORDER BY f.flight_date {order}, f.flight_id {order} LIMIT 500"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    out: list[schemas.FlightRow] = []
    for (
        flight_id,
        date,
        client,
        instructor,
        rtype,
        billing,
        acclass,
        is_ground,
        hours,
        cost,
    ) in rows:
        out.append(
            schemas.FlightRow(
                id=str(flight_id),
                date=date or "",
                client=client or "",
                instructor=instructor or "",
                type=rtype or "Dual flight training",
                billing=_norm_billing(billing),
                acClass=_norm_acclass(acclass),
                ground="Ground (1)" if is_ground else "Flight (0)",
                hours=float(hours or 0),
                cost=float(cost or 0),
            )
        )
    return out


def instructors_list() -> list[schemas.InstructorSummary]:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        rows = conn.execute(
            """SELECT instructor,
                      COALESCE(SUM(length_hrs), 0) AS hours,
                      COUNT(DISTINCT student_id) AS students
               FROM flights
               WHERE instructor IS NOT NULL AND instructor != ''
               GROUP BY instructor
               ORDER BY hours DESC"""
        ).fetchall()
    finally:
        conn.close()
    return [
        schemas.InstructorSummary(
            id=name,
            name=name,
            hours=float(hours or 0),
            students=int(students or 0),
            passRate=0.0,
        )
        for name, hours, students in rows
    ]


def instructor_detail(instructor_id: str) -> schemas.InstructorDetail:
    from datetime import date as _date

    from .. import norms as _norms

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        exists = conn.execute(
            "SELECT 1 FROM flights WHERE instructor = ? LIMIT 1",
            (instructor_id,),
        ).fetchone()
        if not exists:
            raise LookupError(f"instructor {instructor_id}")
        norm_by_rating = {n.rating: n for n in _norms.compute_rating_norms(conn)}
        # Students taught by this instructor — one row per student/rating they touched.
        student_rows = conn.execute(
            """SELECT s.student_id, s.fsp_display_name AS name,
                      r.code AS rating,
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
               FROM flights f
               JOIN students s USING (student_id)
               JOIN enrollments e
                 ON e.enrollment_id = f.enrollment_id AND e.student_id = s.student_id
               JOIN ratings r USING (rating_id)
               WHERE f.instructor = ?
               GROUP BY s.student_id, r.code
               ORDER BY s.fsp_display_name""",
            (instructor_id,),
        ).fetchall()
        # Per-rating aggregates for this instructor (from completed milestones).
        per_rating_rows = conn.execute(
            """SELECT r.code AS rating, COUNT(*) AS n,
                      AVG(m.cumulative_hours) AS avg_hours,
                      AVG(m.cumulative_cost) AS avg_cost,
                      AVG(m.days_from_rating_start) AS avg_days,
                      GROUP_CONCAT(DISTINCT CAST(e.student_id AS TEXT)) AS student_ids
               FROM milestones m
               JOIN enrollments e USING (enrollment_id)
               JOIN ratings r USING (rating_id)
               WHERE m.milestone_name = 'checkride'
                 AND e.enrollment_id IN (
                     SELECT DISTINCT f.enrollment_id FROM flights f
                     WHERE f.instructor = ? AND f.enrollment_id IS NOT NULL
                 )
               GROUP BY r.code, r.sort_order
               ORDER BY r.sort_order""",
            (instructor_id,),
        ).fetchall()
    finally:
        conn.close()

    today = _date.today()
    students: list[schemas.ClientRow] = []
    for row in student_rows:
        rating_code = row["rating"]
        hours = float(row["hours"] or 0)
        norm = norm_by_rating.get(rating_code)
        median = float(norm.median_hours) if norm and norm.median_hours else 0.0
        progress = round(min(hours / median, 1.5), 3) if median > 0 else 0.0
        first = row["first_flight"]
        days = 0
        if first:
            try:
                days = (today - _date.fromisoformat(first)).days
            except ValueError:
                days = 0
        if row["has_checkride"]:
            status: schemas.FlightStatus = "Completed"
        elif progress >= 0.9:
            status = "On checkride"
        else:
            status = "Active"
        students.append(
            schemas.ClientRow(
                id=str(row["student_id"]),
                name=row["name"] or "Unknown",
                rating=rating_code,
                progressPct=progress,
                hoursToDate=hours,
                daysEnrolled=int(days),
                status=status,
            )
        )

    per_rating = [
        schemas.InstructorPerRating(
            rating=row["rating"],
            n=int(row["n"] or 0),
            avgHrs=float(row["avg_hours"] or 0),
            avgCost=float(row["avg_cost"] or 0),
            avgDays=float(row["avg_days"] or 0),
            studentIds=(
                row["student_ids"].split(",") if row["student_ids"] else []
            ),
        )
        for row in per_rating_rows
    ]
    return schemas.InstructorDetail(
        id=instructor_id, name=instructor_id, students=students, perRating=per_rating
    )


# ── Insights tab ──────────────────────────────────────────────────────────────
# Sample thresholds: an (instructor, rating) pair needs >= _IR_MIN students to
# show; below _IR_GOOD it's flagged low-sample. Overall efficiency needs
# >= _EFF_MIN enrollments. Tuned for the ~80-enrollment / 5-instructor cohort.
_IR_MIN = 2
_IR_GOOD = 3
_EFF_MIN = 3
ME_RATINGS = ("AMEL", "MEI")  # local copy; partition.ME_RATINGS is the source


def _insights_base(conn: sqlite3.Connection):
    """One pass: every completed (checkride) enrollment with its primary
    instructor + the cohort norm for its rating. Shared by all three insights."""
    from .. import norms as _norms

    norm_by_rating = {n.rating: n for n in _norms.compute_rating_norms(conn)}
    rows = conn.execute(
        """SELECT e.enrollment_id, s.student_id, s.fsp_display_name AS name,
                  r.code AS rating,
                  m.cumulative_hours AS hours, m.cumulative_cost AS cost,
                  m.days_from_rating_start AS days,
                  (SELECT f3.instructor FROM flights f3
                     WHERE f3.enrollment_id = e.enrollment_id
                       AND f3.instructor IS NOT NULL AND f3.instructor != ''
                     GROUP BY f3.instructor
                     ORDER BY SUM(f3.length_hrs) DESC LIMIT 1) AS primary_instructor
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN ratings r USING (rating_id)
           JOIN students s USING (student_id)
           WHERE m.milestone_name = 'checkride'"""
    ).fetchall()
    return rows, norm_by_rating


def _pct_over(value: float, median: float) -> float:
    return (value - median) / median if median and median > 0 else 0.0


def insights_at_risk(
    conn: sqlite3.Connection, norm_by_rating, base_rows, threshold: float
) -> list[schemas.AtRiskRow]:
    """Students whose hours OR cost ran >= threshold over the cohort median."""
    out: list[schemas.AtRiskRow] = []
    for row in base_rows:
        norm = norm_by_rating.get(row["rating"])
        if not norm or not norm.median_hours or not norm.median_cost:
            continue
        hours = float(row["hours"] or 0)
        cost = float(row["cost"] or 0)
        po_h = _pct_over(hours, float(norm.median_hours))
        po_c = _pct_over(cost, float(norm.median_cost))
        worst = max(po_h, po_c)
        if worst < threshold:
            continue
        out.append(
            schemas.AtRiskRow(
                studentId=str(row["student_id"]),
                name=row["name"] or "Unknown",
                rating=row["rating"],
                hours=hours,
                medianHours=float(norm.median_hours),
                pctOverHours=round(po_h, 4),
                cost=cost,
                medianCost=float(norm.median_cost),
                pctOverCost=round(po_c, 4),
                days=int(row["days"] or 0),
                worstPct=round(worst, 4),
                status="Completed",
            )
        )
    out.sort(key=lambda r: r.worstPct, reverse=True)
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _loo_instructor_rating_stats(base_rows):
    """Per (instructor, rating): their averages and their LEAVE-ONE-OUT deviation
    — i.e. compared against every OTHER instructor's students in that rating, not
    against a cohort baseline that includes their own students. Returns a flat
    list of dicts (all groups, no sample filter)."""
    from collections import defaultdict

    by_rating: dict[str, list] = defaultdict(list)
    for row in base_rows:
        if row["primary_instructor"]:
            by_rating[row["rating"]].append(row)

    stats: list[dict] = []
    for rating, rows in by_rating.items():
        instructors = {r["primary_instructor"] for r in rows}
        for inst in instructors:
            mine = [r for r in rows if r["primary_instructor"] == inst]
            others = [r for r in rows if r["primary_instructor"] != inst]
            mh = _mean([float(r["hours"] or 0) for r in mine])
            mc = _mean([float(r["cost"] or 0) for r in mine])
            md = _mean([float(r["days"] or 0) for r in mine])
            if others:
                oh = _mean([float(r["hours"] or 0) for r in others])
                oc = _mean([float(r["cost"] or 0) for r in others])
                vs_h = (mh - oh) / oh if oh else 0.0
                vs_c = (mc - oc) / oc if oc else 0.0
                comparable = True
            else:
                vs_h = vs_c = 0.0
                comparable = False
            stats.append({
                "instructor": inst, "rating": rating, "n": len(mine),
                "avgHours": mh, "avgCost": mc, "avgDays": md,
                "vsRestHoursPct": vs_h, "vsRestCostPct": vs_c, "comparable": comparable,
            })
    return stats


def insights_instructor_ratings(
    norm_by_rating, base_rows
) -> list[schemas.RatingStrength]:
    """Per rating, each instructor vs the OTHER instructors' students (leave-one-
    out), ranked best-first by avg hours."""
    from collections import defaultdict

    by_rating: dict[str, list[schemas.InstructorRatingStat]] = defaultdict(list)
    for s in _loo_instructor_rating_stats(base_rows):
        if s["n"] < _IR_MIN:
            continue
        by_rating[s["rating"]].append(
            schemas.InstructorRatingStat(
                instructor=s["instructor"], rating=s["rating"], n=s["n"],
                avgHours=round(s["avgHours"], 1), avgCost=round(s["avgCost"], 0),
                avgDays=round(s["avgDays"], 0),
                vsRestHoursPct=round(s["vsRestHoursPct"], 4),
                vsRestCostPct=round(s["vsRestCostPct"], 4),
                comparable=s["comparable"],
                lowSample=s["n"] < _IR_GOOD, rank=0,
            )
        )

    out: list[schemas.RatingStrength] = []
    for rating, group in by_rating.items():
        group.sort(key=lambda s: s.avgHours)  # lower hours = better
        for i, s in enumerate(group, start=1):
            s.rank = i
        norm = norm_by_rating.get(rating)
        out.append(
            schemas.RatingStrength(
                rating=rating,
                medianHours=float(norm.median_hours) if norm and norm.median_hours else 0.0,
                medianCost=float(norm.median_cost) if norm and norm.median_cost else 0.0,
                instructors=group,
            )
        )
    order = {c: i for i, c in enumerate(("PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"))}
    out.sort(key=lambda rs: order.get(rs.rating, 99))
    return out


def insights_instructor_efficiency(
    norm_by_rating, base_rows
) -> list[schemas.InstructorEfficiency]:
    """Each instructor's overall efficiency = n-weighted mean of their per-rating
    leave-one-out deviations (vs every other instructor's students)."""
    from collections import defaultdict

    by_inst: dict[str, list[dict]] = defaultdict(list)
    for s in _loo_instructor_rating_stats(base_rows):
        if s["comparable"]:
            by_inst[s["instructor"]].append(s)

    out: list[schemas.InstructorEfficiency] = []
    for inst, entries in by_inst.items():
        total_n = sum(e["n"] for e in entries)
        if total_n == 0:
            continue
        avg_h = sum(e["vsRestHoursPct"] * e["n"] for e in entries) / total_n
        avg_c = sum(e["vsRestCostPct"] * e["n"] for e in entries) / total_n
        out.append(
            schemas.InstructorEfficiency(
                instructor=inst, students=total_n, ratings=len(entries),
                avgHoursVsRestPct=round(avg_h, 4),
                avgCostVsRestPct=round(avg_c, 4),
                score=round((avg_h + avg_c) / 2, 4),
                rank=0, lowSample=total_n < _EFF_MIN,
            )
        )
    out.sort(key=lambda e: e.score)  # most efficient (most below the rest) first
    for i, e in enumerate(out, start=1):
        e.rank = i
    return out


_PREDICT_PACE_WINDOW_DAYS = 84   # look at the trailing 12 weeks for current pace
_PREDICT_STALLED_DAYS = 75       # no flight in this long → stalled, don't predict
_PRIMARY_RATINGS = ("PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI")


def insights_predictions(conn, norm_by_rating) -> list[schemas.PredictionRow]:
    """Project each in-progress (partial, no-checkride) student's path to
    checkride-readiness from their recent flight pace."""
    from datetime import date as _date, timedelta as _td

    today = _date.today()
    rows = conn.execute(
        """SELECT e.enrollment_id, s.student_id, s.fsp_display_name AS name, r.code AS rating
           FROM enrollments e
           JOIN ratings r USING (rating_id)
           JOIN students s USING (student_id)
           WHERE e.is_partial = 1
             AND r.code IN ('PPL','IFR','COM','AMEL','CFI','CFII','MEI')
             AND NOT EXISTS (SELECT 1 FROM milestones m
                             WHERE m.enrollment_id = e.enrollment_id
                               AND m.milestone_name = 'checkride')"""
    ).fetchall()

    out: list[schemas.PredictionRow] = []
    for row in rows:
        flights = conn.execute(
            """SELECT flight_date, length_hrs FROM flights
               WHERE enrollment_id = ? AND status = 'Completed'
                 AND reservation_type != 'Check Ride' AND length_hrs > 0
               ORDER BY flight_date""",
            (row["enrollment_id"],),
        ).fetchall()
        if not flights:
            continue
        current = sum(float(f["length_hrs"] or 0) for f in flights)
        last_flight = _date.fromisoformat(flights[-1]["flight_date"])
        first_flight = _date.fromisoformat(flights[0]["flight_date"])
        days_since = (today - last_flight).days

        norm = norm_by_rating.get(row["rating"])
        median = float(norm.median_hours) if norm and norm.median_hours else 0.0

        # Recent pace: hours in the trailing window ÷ weeks of that window.
        window_start = today - _td(days=_PREDICT_PACE_WINDOW_DAYS)
        recent_hours = sum(
            float(f["length_hrs"] or 0) for f in flights
            if _date.fromisoformat(f["flight_date"]) >= window_start
        )
        window_days = min(_PREDICT_PACE_WINDOW_DAYS, max(1, (today - first_flight).days))
        pace = recent_hours / (window_days / 7.0)

        weeks_remaining: float | None = None
        projected: str | None = None
        if days_since > _PREDICT_STALLED_DAYS or pace <= 0.05:
            status = "stalled"
        elif median and current >= median * 0.98:
            status = "over_median"
        else:
            status = "on_track"
            if median and pace > 0:
                weeks_remaining = round(max(0.0, (median - current)) / pace, 1)
                projected = (today + _td(days=int(weeks_remaining * 7))).isoformat()

        out.append(schemas.PredictionRow(
            studentId=str(row["student_id"]), name=row["name"] or "Unknown",
            rating=row["rating"], currentHours=round(current, 1),
            medianHours=round(median, 1), pacePerWeek=round(pace, 1),
            weeksRemaining=weeks_remaining, projectedDate=projected,
            lastFlight=last_flight.isoformat(), daysSinceLastFlight=days_since,
            status=status,
        ))
    # On-track first (soonest projected), then over-median, then stalled.
    order = {"on_track": 0, "over_median": 1, "stalled": 2}
    out.sort(key=lambda p: (order[p.status], p.weeksRemaining if p.weeksRemaining is not None else 1e9))
    return out


_CADENCE_BUCKETS = [
    ("Under 1.5×/week", 0.0, 1.5),
    ("1.5–2.5×/week", 1.5, 2.5),
    ("2.5×+/week", 2.5, 1e9),
]


def insights_cadence(conn, rating: str = "PPL") -> schemas.CadenceInsight | None:
    """Bucket completed students in a rating by training cadence (flights/week)
    and show avg hours, cost, and calendar days per bucket. Defaults to PPL,
    which has the most data."""
    rows = conn.execute(
        """SELECT m.cumulative_hours AS hours, m.cumulative_cost AS cost,
                  m.days_from_rating_start AS days,
                  (SELECT COUNT(*) FROM flights f
                   WHERE f.enrollment_id = e.enrollment_id AND f.status = 'Completed'
                     AND f.reservation_type != 'Check Ride') AS nfl
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN ratings r USING (rating_id)
           WHERE m.milestone_name = 'checkride' AND r.code = ?""",
        (rating,),
    ).fetchall()
    if not rows:
        return None

    grouped: dict[str, list] = {b[0]: [] for b in _CADENCE_BUCKETS}
    for r in rows:
        days = max(1, int(r["days"] or 1))
        cadence = float(r["nfl"] or 0) / (days / 7.0)
        for label, lo, hi in _CADENCE_BUCKETS:
            if lo <= cadence < hi:
                grouped[label].append((cadence, float(r["hours"] or 0), float(r["cost"] or 0), float(r["days"] or 0)))
                break

    buckets = []
    for label, _lo, _hi in _CADENCE_BUCKETS:
        v = grouped[label]
        if not v:
            continue
        n = len(v)
        buckets.append(schemas.CadenceBucket(
            label=label, n=n,
            avgCadence=round(sum(x[0] for x in v) / n, 2),
            avgHours=round(sum(x[1] for x in v) / n, 1),
            avgCost=round(sum(x[2] for x in v) / n, 0),
            avgDays=round(sum(x[3] for x in v) / n, 0),
        ))
    return schemas.CadenceInsight(rating=rating, n=len(rows), buckets=buckets)


def insights(threshold: float = 0.25) -> schemas.Insights:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        base_rows, norm_by_rating = _insights_base(conn)
        at_risk = insights_at_risk(conn, norm_by_rating, base_rows, threshold)
        strengths = insights_instructor_ratings(norm_by_rating, base_rows)
        efficiency = insights_instructor_efficiency(norm_by_rating, base_rows)
        predictions = insights_predictions(conn, norm_by_rating)
        cadence = insights_cadence(conn, "PPL")
    finally:
        conn.close()
    return schemas.Insights(
        atRiskThresholdPct=threshold,
        atRisk=at_risk,
        strengths=strengths,
        efficiency=efficiency,
        predictions=predictions,
        cadence=cadence,
    )


def _trailing_8_months(today: date) -> list[str]:
    """Return 8 YYYY-MM strings, oldest first, ending at today's month."""
    out: list[str] = []
    year, month = today.year, today.month
    for _ in range(8):
        out.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return list(reversed(out))


def _sparkline_by_enrollment(
    conn: sqlite3.Connection, months: list[str]
) -> dict[tuple[int, int], list[float]]:
    """Build {(student_id, enrollment_id) → 8 hour totals, oldest first}.

    One DB pass over flights — keyed on enrollment, not student, so a student
    enrolled in PPL and IFR gets two distinct sparklines.
    """
    if not months:
        return {}
    oldest = months[0]
    rows = conn.execute(
        """SELECT student_id, enrollment_id, substr(flight_date,1,7) AS ym,
                  COALESCE(SUM(length_hrs), 0) AS hrs
           FROM flights
           WHERE flight_date >= ? AND enrollment_id IS NOT NULL
           GROUP BY student_id, enrollment_id, ym""",
        (oldest + "-01",),
    ).fetchall()
    by_key: dict[tuple[int, int], dict[str, float]] = {}
    for student_id, enrollment_id, ym, hrs in rows:
        if not ym:
            continue
        by_key.setdefault((student_id, enrollment_id), {})[ym] = float(hrs)
    out: dict[tuple[int, int], list[float]] = {}
    for key, ym_map in by_key.items():
        out[key] = [ym_map.get(m, 0.0) for m in months]
    return out


def clients(
    range_key: schemas.RangeKey, rating: schemas.RatingCode | None = None
) -> list[schemas.ClientRow]:
    from datetime import date as _date

    from .. import norms as _norms

    cutoff = range_cutoff(range_key)
    today = _date.today()
    spark_months = _trailing_8_months(today)

    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        median_hours_by_rating = {
            n.rating: n.median_hours for n in _norms.compute_rating_norms(conn)
        }

        spark_by_key = _sparkline_by_enrollment(conn, spark_months)

        sql = """
            SELECT s.student_id, s.fsp_display_name, r.code AS rating_code,
                   e.enrollment_id,
                   COALESCE(SUM(f.length_hrs), 0) AS hours,
                   MIN(f.flight_date) AS first_flight,
                   MAX(f.flight_date) AS last_flight,
                   COALESCE((
                       SELECT SUM(i.amount) FROM invoices i
                       JOIN flights f2 ON f2.flight_id = i.flight_id
                       WHERE f2.student_id = s.student_id
                         AND f2.enrollment_id = e.enrollment_id
                   ), 0) AS cost,
                   (
                       SELECT f3.instructor FROM flights f3
                       WHERE f3.student_id = s.student_id
                         AND f3.enrollment_id = e.enrollment_id
                         AND f3.instructor IS NOT NULL
                         AND f3.instructor != ''
                       GROUP BY f3.instructor
                       ORDER BY SUM(f3.length_hrs) DESC
                       LIMIT 1
                   ) AS primary_instructor,
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
        sql += " GROUP BY s.student_id, r.code, e.enrollment_id ORDER BY s.fsp_display_name"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    out: list[schemas.ClientRow] = []
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

        spark = spark_by_key.get(
            (row["student_id"], row["enrollment_id"]), [0.0] * len(spark_months)
        )

        out.append(
            schemas.ClientRow(
                id=str(row["student_id"]),
                name=row["fsp_display_name"] or "Unknown",
                rating=rating_code,
                progressPct=progress,
                hoursToDate=hours,
                daysEnrolled=int(days),
                status=status,
                costToDate=float(row["cost"] or 0),
                instructor=row["primary_instructor"] or "",
                sparkline=spark,
            )
        )
    return out
