"""Streamlit dashboard — Phase 8: full web app (all 7 ratings).

Run from repo root:
    streamlit run app.py

Pages (sidebar radio):
    All Ratings   — norm summary table + bar comparison
    Rating Detail — pick a rating; cohort box plots + student overlay
    Student       — pick a student; all ratings completed + trajectories
    Instructor    — pick an instructor; student list + efficiency metrics
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import db as _db, ingest, reconcile, partition, milestones, norms

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "provectus.db"

RATING_ORDER = ["PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"]
RATING_DISPLAY = {
    "PPL":  "Private Pilot",
    "IFR":  "Instrument Rating",
    "COM":  "Commercial Single-Engine",
    "AMEL": "Multi-Engine (AMEL)",
    "CFI":  "CFI",
    "CFII": "CFII",
    "MEI":  "MEI",
}

# ── DB helpers ────────────────────────────────────────────────────────────────

def build_db(db_path: Path) -> None:
    conn = _db.init_db(db_path)
    ingest.ingest_all(
        conn,
        REPO_ROOT / "synthetic_fsp_clients.csv",
        REPO_ROOT / "synthetic_fsp_reservations.csv",
        REPO_ROOT / "synthetic_fsp_invoices.csv",
        REPO_ROOT / "synthetic_alumni_survey.csv",
    )
    reconcile.reconcile(conn)
    partition.build_enrollments(conn)
    partition.partition_flights(conn)
    milestones.compute_milestones(conn)
    conn.close()


def ensure_db(db_path: Path, force_rebuild: bool = False) -> None:
    if force_rebuild or not db_path.exists():
        build_db(db_path)


# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data
def load_all_norms(db_path: str) -> list[dict]:
    conn = _db.connect(db_path)
    result = norms.compute_rating_norms(conn)
    conn.close()
    return [n.__dict__ for n in result]


@st.cache_data
def load_rating_cohort(db_path: str, rating: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """SELECT s.fsp_display_name  AS student,
                  s.student_id,
                  m.cumulative_hours  AS hours,
                  m.cumulative_cost   AS cost,
                  m.days_from_rating_start AS days,
                  m.cumulative_flights AS flights,
                  m.milestone_date
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           WHERE r.code = ? AND m.milestone_name = 'checkride'
           ORDER BY s.fsp_display_name""",
        conn, params=(rating,),
    )
    conn.close()
    return df


@st.cache_data
def load_student_trajectory(db_path: str, student: str) -> pd.DataFrame:
    """All milestones for a student across all ratings."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """SELECT r.code AS rating,
                  r.sort_order,
                  m.milestone_name AS milestone,
                  m.milestone_date,
                  m.days_from_rating_start AS days,
                  m.cumulative_flights AS flights,
                  m.cumulative_hours AS hours,
                  m.cumulative_cost AS cost
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           WHERE s.fsp_display_name = ?
           ORDER BY r.sort_order, m.milestone_date""",
        conn, params=(student,),
    )
    conn.close()
    return df


@st.cache_data
def load_all_students(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT DISTINCT s.fsp_display_name
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           WHERE s.fsp_display_name IS NOT NULL
           ORDER BY s.fsp_display_name"""
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


@st.cache_data
def load_instructors(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT DISTINCT instructor FROM flights "
        "WHERE instructor IS NOT NULL ORDER BY instructor"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


@st.cache_data
def load_instructor_detail(db_path: str, instructor: str) -> pd.DataFrame:
    """Checkride milestone rows for students taught by this instructor."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        """SELECT s.fsp_display_name AS student,
                  r.code AS rating,
                  r.sort_order,
                  m.cumulative_hours  AS hours,
                  m.cumulative_cost   AS cost,
                  m.days_from_rating_start AS days,
                  m.cumulative_flights AS flights,
                  m.milestone_date
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           WHERE m.milestone_name = 'checkride'
             AND e.enrollment_id IN (
                 SELECT DISTINCT f.enrollment_id
                 FROM flights f
                 WHERE f.instructor = ? AND f.enrollment_id IS NOT NULL
             )
           ORDER BY r.sort_order, s.fsp_display_name""",
        conn, params=(instructor,),
    )
    conn.close()
    return df


def _clear_caches() -> None:
    load_all_norms.clear()
    load_rating_cohort.clear()
    load_student_trajectory.clear()
    load_all_students.clear()
    load_instructors.clear()
    load_instructor_detail.clear()


# ── Plot helpers ──────────────────────────────────────────────────────────────

def _box_with_student(
    values: list[float],
    student_value: float | None,
    title: str,
    y_label: str,
    value_fmt: str,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Box(
        y=values, name="Cohort", boxpoints="all", jitter=0.4, pointpos=-1.5,
        marker_color="#5B9BD5", line_color="#305496",
        hovertemplate=f"{y_label}: %{{y:{value_fmt}}}<extra></extra>",
    ))
    if student_value is not None:
        fig.add_trace(go.Scatter(
            x=["Cohort"], y=[student_value], mode="markers",
            marker=dict(color="#C00000", size=14, symbol="diamond",
                        line=dict(color="white", width=2)),
            name="Selected",
            hovertemplate=f"%{{y:{value_fmt}}}<extra>Selected</extra>",
        ))
    fig.update_layout(
        title=title, yaxis_title=y_label,
        showlegend=False, height=360,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def _norm_metric_row(norm: dict) -> None:
    """Render four st.metric cards for a single RatingNorm dict."""
    c1, c2, c3, c4 = st.columns(4)
    n = norm.get("n_raw", 0)
    c1.metric("Alumni (n)", n)
    c2.metric(
        "Median hours", f"{norm.get('median_hours', 0):.1f}",
        help=f"P25–P75: {norm.get('p25_hours', 0):.1f} – {norm.get('p75_hours', 0):.1f}",
    )
    c3.metric(
        "Median cost", f"${norm.get('median_cost', 0):,.0f}",
        help=f"P25–P75: ${norm.get('p25_cost', 0):,.0f} – ${norm.get('p75_cost', 0):,.0f}",
    )
    c4.metric(
        "Median days", int(norm.get("median_days", 0)),
        help=f"P25–P75: {norm.get('p25_days', 0)} – {norm.get('p75_days', 0)} days",
    )
    if norm.get("low_sample_flag"):
        st.warning(f"Low sample (n={n} < 10). Norms are indicative only.")


# ── Pages ─────────────────────────────────────────────────────────────────────

def _page_all_ratings(db: str) -> None:
    st.header("All Ratings — Cohort Overview")

    all_norms = load_all_norms(db)
    if not all_norms:
        st.error("No milestone data found. Rebuild the DB.")
        return

    # Summary table
    rows = []
    for n in all_norms:
        rows.append({
            "Rating": n["rating"],
            "n": n["n_raw"],
            "Median hrs": f"{n['median_hours']:.1f}",
            "P25–P75 hrs": f"{n['p25_hours']:.1f} – {n['p75_hours']:.1f}",
            "Median cost": f"${n['median_cost']:,.0f}",
            "P25–P75 cost": f"${n['p25_cost']:,.0f} – ${n['p75_cost']:,.0f}",
            "Median days": int(n["median_days"]),
            "Low sample": "⚠️" if n["low_sample_flag"] else "",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Bar chart comparison — median hours per rating
    st.subheader("Median flight hours to checkride by rating")
    fig = go.Figure()
    names = [n["rating"] for n in all_norms]
    med_hrs = [n["median_hours"] for n in all_norms]
    p25_hrs = [n["p25_hours"] for n in all_norms]
    p75_hrs = [n["p75_hours"] for n in all_norms]
    fig.add_trace(go.Bar(
        x=names, y=med_hrs, name="Median",
        marker_color="#5B9BD5",
        error_y=dict(
            type="data", symmetric=False,
            array=[p75 - med for p75, med in zip(p75_hrs, med_hrs)],
            arrayminus=[med - p25 for p25, med in zip(p25_hrs, med_hrs)],
        ),
        hovertemplate="<b>%{x}</b><br>Median: %{y:.1f} hrs<extra></extra>",
    ))
    fig.update_layout(
        yaxis_title="Flight hours", height=360,
        margin=dict(l=20, r=20, t=30, b=20), showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Bar chart — median cost per rating
    st.subheader("Median cost to checkride by rating")
    fig2 = go.Figure()
    med_cost = [n["median_cost"] for n in all_norms]
    p25_cost = [n["p25_cost"] for n in all_norms]
    p75_cost = [n["p75_cost"] for n in all_norms]
    fig2.add_trace(go.Bar(
        x=names, y=med_cost, name="Median",
        marker_color="#70AD47",
        error_y=dict(
            type="data", symmetric=False,
            array=[p75 - med for p75, med in zip(p75_cost, med_cost)],
            arrayminus=[med - p25 for p25, med in zip(p25_cost, med_cost)],
        ),
        hovertemplate="<b>%{x}</b><br>Median: $%{y:,.0f}<extra></extra>",
    ))
    fig2.update_layout(
        yaxis_title="Cost (USD)", yaxis_tickprefix="$",
        height=360, margin=dict(l=20, r=20, t=30, b=20), showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)


def _page_rating_detail(db: str) -> None:
    st.header("Rating Detail")

    all_norms_list = load_all_norms(db)
    available = [n["rating"] for n in all_norms_list]
    if not available:
        st.error("No data found.")
        return

    # Filters in sidebar
    st.sidebar.subheader("Filters")
    rating = st.sidebar.selectbox("Rating", available, key="rd_rating")

    cohort = load_rating_cohort(db, rating)
    if cohort.empty:
        st.warning(f"No checkride data for {rating}.")
        return

    norm = next((n for n in all_norms_list if n["rating"] == rating), {})

    # Optional date filter
    dates = pd.to_datetime(cohort["milestone_date"])
    min_yr = int(dates.dt.year.min())
    max_yr = int(dates.dt.year.max())
    yr_range = st.sidebar.slider(
        "Checkride year range", min_yr, max_yr, (min_yr, max_yr), key="rd_yr",
    )
    mask = dates.dt.year.between(yr_range[0], yr_range[1])
    cohort_f = cohort[mask].copy()

    student = st.sidebar.selectbox(
        "Overlay student", ["(none)"] + cohort_f["student"].tolist(), key="rd_student",
    )

    # Norm summary
    display_name = RATING_DISPLAY.get(rating, rating)
    st.subheader(f"{rating} — {display_name}")
    if norm:
        _norm_metric_row(norm)

    # Box plots
    st.subheader("Cohort distribution" + (" — selected student in red" if student != "(none)" else ""))

    def _sv(col: str) -> float | None:
        if student == "(none)":
            return None
        rows = cohort_f[cohort_f["student"] == student]
        return float(rows.iloc[0][col]) if not rows.empty else None

    cols = st.columns(3)
    cols[0].plotly_chart(
        _box_with_student(cohort_f["hours"].tolist(), _sv("hours"),
                          "Flight hours to checkride", "Hours", ".1f"),
        use_container_width=True,
    )
    cols[1].plotly_chart(
        _box_with_student(cohort_f["cost"].tolist(), _sv("cost"),
                          "Total cost to checkride", "USD", ",.0f"),
        use_container_width=True,
    )
    cols[2].plotly_chart(
        _box_with_student(cohort_f["days"].tolist(), _sv("days"),
                          "Calendar days to checkride", "Days", ".0f"),
        use_container_width=True,
    )

    # Cohort table
    with st.expander("Cohort data table"):
        display = cohort_f[["student", "hours", "cost", "days", "flights", "milestone_date"]].copy()
        display["cost"] = display["cost"].apply(lambda x: f"${x:,.0f}")
        display["hours"] = display["hours"].apply(lambda x: f"{x:.1f}")
        display.columns = ["Student", "Hours", "Cost", "Days", "Flights", "Checkride date"]
        st.dataframe(display, hide_index=True, use_container_width=True)


def _page_student(db: str) -> None:
    st.header("Student Drill-down")

    students = load_all_students(db)
    if not students:
        st.error("No student data found.")
        return

    all_norms_list = load_all_norms(db)
    norm_by_rating = {n["rating"]: n for n in all_norms_list}

    st.sidebar.subheader("Student")
    student = st.sidebar.selectbox("Select student", students, key="sd_student")

    traj = load_student_trajectory(db, student)
    if traj.empty:
        st.warning(f"No milestone data for {student}.")
        return

    ratings_completed = traj["rating"].unique().tolist()

    # Summary cards — one per rating at checkride
    st.subheader(f"{student} — ratings completed")
    cr = traj[traj["milestone"] == "checkride"].copy()
    summary_cols = st.columns(len(ratings_completed))
    for i, r in enumerate(ratings_completed):
        row = cr[cr["rating"] == r]
        if row.empty:
            summary_cols[i].metric(r, "—")
        else:
            row = row.iloc[0]
            norm = norm_by_rating.get(r, {})
            med_h = norm.get("median_hours", None)
            delta_str = (
                f"{row['hours'] - med_h:+.1f}h vs median"
                if med_h else None
            )
            summary_cols[i].metric(
                r,
                f"{row['hours']:.1f}h  ${row['cost']:,.0f}",
                delta=delta_str,
                delta_color="inverse",  # more hours than median = red
                help=f"{int(row['days'])} days to checkride",
            )

    # Per-rating trajectory tables
    for r in ratings_completed:
        r_traj = traj[traj["rating"] == r].copy()
        norm = norm_by_rating.get(r, {})
        med = {
            "hours": norm.get("median_hours", 0),
            "cost": norm.get("median_cost", 0),
            "days": norm.get("median_days", 0),
        }

        def _delta_col(row: pd.Series) -> str:
            if row["milestone"] != "checkride":
                return ""
            dh = row["hours"] - med["hours"]
            dc = row["cost"] - med["cost"]
            dd = row["days"] - med["days"]
            s = lambda x: "+" if x > 0 else ""
            return f"{s(dh)}{dh:.1f}h, {s(dc)}${dc:,.0f}, {s(dd)}{dd:.0f}d"

        r_traj["Δ vs cohort median"] = r_traj.apply(_delta_col, axis=1)
        r_traj["cost"] = r_traj["cost"].apply(lambda x: f"${x:,.0f}")
        r_traj["hours"] = r_traj["hours"].apply(lambda x: f"{x:.1f}")
        display = r_traj[["milestone", "milestone_date", "days", "flights", "hours", "cost", "Δ vs cohort median"]].copy()
        display.columns = ["Milestone", "Date", "Days from start", "Flights", "Hours", "Cost", "Δ vs cohort median"]

        lsf = norm.get("low_sample_flag", False)
        caption = f"n={norm.get('n_raw', '?')} ({'⚠️ low sample' if lsf else 'sufficient sample'})"
        with st.expander(f"{r} — {RATING_DISPLAY.get(r, r)}  ({caption})", expanded=True):
            st.dataframe(display, hide_index=True, use_container_width=True)


def _page_instructor(db: str) -> None:
    st.header("Instructor View")

    instructors = load_instructors(db)
    if not instructors:
        st.error("No instructor data found.")
        return

    all_norms_list = load_all_norms(db)
    norm_by_rating = {n["rating"]: n for n in all_norms_list}

    st.sidebar.subheader("Instructor")
    instructor = st.sidebar.selectbox("Select instructor", instructors, key="iv_inst")

    detail = load_instructor_detail(db, instructor)
    if detail.empty:
        st.warning(f"No checkride data found for {instructor}.")
        return

    ratings_taught = (
        detail.sort_values("sort_order")["rating"].unique().tolist()
    )

    # Efficiency summary table vs cohort norms
    st.subheader(f"{instructor} — efficiency vs cohort norms")
    summary_rows = []
    for r in ratings_taught:
        r_rows = detail[detail["rating"] == r]
        norm = norm_by_rating.get(r, {})
        med_h = norm.get("median_hours")
        med_c = norm.get("median_cost")
        med_d = norm.get("median_days")
        inst_med_h = r_rows["hours"].median()
        inst_med_c = r_rows["cost"].median()
        inst_med_d = r_rows["days"].median()

        def _delta(inst_v, cohort_v):
            if inst_v is None or cohort_v is None:
                return "—"
            d = inst_v - cohort_v
            return f"{d:+.1f}" if abs(d) < 1000 else f"{d:+,.0f}"

        summary_rows.append({
            "Rating": r,
            "Students": len(r_rows),
            "Inst. median hrs": f"{inst_med_h:.1f}",
            "Δ vs cohort hrs": _delta(inst_med_h, med_h),
            "Inst. median cost": f"${inst_med_c:,.0f}",
            "Δ vs cohort cost": _delta(inst_med_c, med_c),
            "Inst. median days": int(inst_med_d),
            "Δ vs cohort days": _delta(inst_med_d, med_d),
        })
    st.dataframe(pd.DataFrame(summary_rows), hide_index=True, use_container_width=True)

    # Per-rating box plots with instructor's students highlighted
    st.subheader("Hours to checkride — instructor's students vs full cohort")
    filter_rating = st.selectbox(
        "Rating", ratings_taught, key="iv_rating",
    )
    cohort_df = load_rating_cohort(db, filter_rating)
    inst_students = detail[detail["rating"] == filter_rating]["student"].tolist()
    inst_hours = detail[detail["rating"] == filter_rating]["hours"].tolist()

    fig = go.Figure()
    fig.add_trace(go.Box(
        y=cohort_df["hours"].tolist(), name="All students",
        boxpoints="all", jitter=0.4, pointpos=-1.8,
        marker_color="#5B9BD5", line_color="#305496",
        hovertemplate="Hours: %{y:.1f}<extra>All students</extra>",
    ))
    if inst_hours:
        fig.add_trace(go.Box(
            y=inst_hours, name=instructor,
            boxpoints="all", jitter=0.4, pointpos=1.8,
            marker_color="#C00000", line_color="#7B0000",
            hovertemplate="Hours: %{y:.1f}<extra>" + instructor + "</extra>",
        ))
    fig.update_layout(
        yaxis_title="Flight hours", height=400,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Student list
    st.subheader(f"{instructor} — student list")
    display = detail[["student", "rating", "hours", "cost", "days", "flights", "milestone_date"]].copy()
    display["cost"] = display["cost"].apply(lambda x: f"${x:,.0f}")
    display["hours"] = display["hours"].apply(lambda x: f"{x:.1f}")
    display.columns = ["Student", "Rating", "Hours", "Cost", "Days", "Flights", "Checkride date"]
    st.dataframe(display, hide_index=True, use_container_width=True)


# ── Main entry ────────────────────────────────────────────────────────────────

def render() -> None:
    st.set_page_config(page_title="Provectus Analytics", layout="wide")
    st.title("Provectus Training Analytics")
    st.caption("Phase 8 — all 7 ratings. Synthetic data — see SYNTHETIC_DATA_README.md.")

    # Sidebar — nav + rebuild
    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Page",
        ["All Ratings", "Rating Detail", "Student", "Instructor"],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    if st.sidebar.button("Rebuild DB from synthetic CSVs"):
        _clear_caches()
        build_db(DEFAULT_DB)
        st.sidebar.success("DB rebuilt.")
        st.rerun()

    ensure_db(DEFAULT_DB)
    db = str(DEFAULT_DB)

    if page == "All Ratings":
        _page_all_ratings(db)
    elif page == "Rating Detail":
        _page_rating_detail(db)
    elif page == "Student":
        _page_student(db)
    elif page == "Instructor":
        _page_instructor(db)

    with st.expander("Methodology"):
        st.markdown("""
- **Norms:** median + P25/P75 per rating. Outliers filtered with Tukey 1.5×IQR fence per metric.
- **Low sample flag:** n < 10 per rating (per ROADMAP Phase 6).
- **Data source:** synthetic CSVs (see `SYNTHETIC_DATA_README.md`). Real-data swap = change source files; pipeline is unchanged.
- **Milestones:** PPL → first_solo, xc_solos_complete, checkride; IFR → xc_pic_complete, checkride; others → checkride only.
        """)
