"""Streamlit dashboard — Phase 7 MVP (PPL only).

Run from repo root:
    streamlit run app.py
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


@st.cache_data
def load_ppl_checkride(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    return pd.read_sql(
        """SELECT s.fsp_display_name AS student,
                  m.cumulative_hours AS hours,
                  m.cumulative_cost  AS cost,
                  m.days_from_rating_start AS days,
                  m.cumulative_flights AS flights,
                  m.milestone_date
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           WHERE r.code = 'PPL' AND m.milestone_name = 'checkride'
           ORDER BY s.fsp_display_name""",
        conn,
    )


@st.cache_data
def load_student_ppl_trajectory(db_path: str, student: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    return pd.read_sql(
        """SELECT m.milestone_name AS milestone,
                  m.milestone_date,
                  m.days_from_rating_start AS days,
                  m.cumulative_flights AS flights,
                  m.cumulative_hours AS hours,
                  m.cumulative_cost AS cost
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           WHERE r.code = 'PPL' AND s.fsp_display_name = ?
           ORDER BY m.milestone_date""",
        conn,
        params=(student,),
    )


@st.cache_data
def load_ppl_norm(db_path: str) -> dict:
    conn = _db.connect(db_path)
    result = norms.compute_rating_norms(conn)
    conn.close()
    ppl = next((n for n in result if n.rating == "PPL"), None)
    return ppl.__dict__ if ppl else {}


def _box_with_student(values: list[float], student_value: float | None,
                      title: str, y_label: str, value_fmt: str) -> go.Figure:
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
            name="Selected", hovertemplate=f"%{{y:{value_fmt}}}<extra>Selected</extra>",
        ))
    fig.update_layout(title=title, yaxis_title=y_label,
                      showlegend=False, height=360,
                      margin=dict(l=20, r=20, t=50, b=20))
    return fig


def render() -> None:
    st.set_page_config(page_title="Provectus PPL", layout="wide")
    st.title("Provectus Training Analytics")
    st.caption("Phase 7 MVP — PPL only. Synthetic data — see SYNTHETIC_DATA_README.md.")

    # Sidebar
    st.sidebar.header("Settings")
    if st.sidebar.button("Rebuild DB from synthetic CSVs"):
        load_ppl_checkride.clear()
        load_student_ppl_trajectory.clear()
        load_ppl_norm.clear()
        build_db(DEFAULT_DB)
        st.sidebar.success("DB rebuilt")

    ensure_db(DEFAULT_DB)
    db = str(DEFAULT_DB)

    cohort = load_ppl_checkride(db)
    if cohort.empty:
        st.error("No PPL checkride data in DB.")
        return

    norm = load_ppl_norm(db)

    # Sidebar — student picker
    student = st.sidebar.selectbox("Student", cohort["student"].tolist(),
                                   index=0,
                                   help="Pick a PPL alum to plot against the cohort")

    # --- Cohort overview ---
    st.subheader("PPL cohort overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Alumni (n)", norm.get("n_raw", len(cohort)))
    c2.metric("Median hours", f"{norm.get('median_hours', 0):.1f}",
              help=f"P25–P75 band: {norm.get('p25_hours', 0):.1f} – {norm.get('p75_hours', 0):.1f}")
    c3.metric("Median cost", f"${norm.get('median_cost', 0):,.0f}",
              help=f"P25–P75 band: ${norm.get('p25_cost', 0):,.0f} – ${norm.get('p75_cost', 0):,.0f}")
    c4.metric("Median days to checkride", int(norm.get("median_days", 0)),
              help=f"P25–P75 band: {norm.get('p25_days', 0)} – {norm.get('p75_days', 0)}")

    if norm.get("low_sample_flag"):
        st.warning(f"Low sample (n={norm.get('n_raw')}). Norms below n=10 are not publishable.")

    # --- Cohort distribution box plots ---
    st.subheader("Cohort distribution (selected student marked in red)")
    student_row = cohort[cohort["student"] == student].iloc[0]
    cols = st.columns(3)
    cols[0].plotly_chart(
        _box_with_student(cohort["hours"].tolist(), student_row["hours"],
                          "Flight hours to checkride", "Hours", ".1f"),
        width='stretch',
    )
    cols[1].plotly_chart(
        _box_with_student(cohort["cost"].tolist(), student_row["cost"],
                          "Total cost to checkride", "USD", ",.0f"),
        width='stretch',
    )
    cols[2].plotly_chart(
        _box_with_student(cohort["days"].tolist(), student_row["days"],
                          "Calendar days to checkride", "Days", ".0f"),
        width='stretch',
    )

    # --- Selected student trajectory ---
    st.subheader(f"{student} — PPL milestone trajectory")
    traj = load_student_ppl_trajectory(db, student)

    # Add delta vs cohort median for the checkride row
    cohort_med = {
        "hours": norm.get("median_hours", 0),
        "cost": norm.get("median_cost", 0),
        "days": norm.get("median_days", 0),
    }
    def _delta(row):
        if row["milestone"] != "checkride":
            return ""
        h_d = row["hours"] - cohort_med["hours"]
        c_d = row["cost"] - cohort_med["cost"]
        d_d = row["days"] - cohort_med["days"]
        sign = lambda x: "+" if x > 0 else ""
        return f"Δ vs median: {sign(h_d)}{h_d:.1f}h, {sign(c_d)}${c_d:,.0f}, {sign(d_d)}{d_d}d"

    display = traj.copy()
    display["vs cohort median"] = display.apply(_delta, axis=1)
    display["cost"] = display["cost"].apply(lambda x: f"${x:,.0f}")
    display["hours"] = display["hours"].apply(lambda x: f"{x:.1f}")
    display.columns = ["Milestone", "Date", "Days from start", "Flights", "Hours",
                       "Cost", "vs cohort median"]
    st.dataframe(display, hide_index=True, width='stretch')

    with st.expander("Methodology"):
        st.markdown("""
- **Cohort:** all alumni with a PPL checkride milestone in the DB.
- **Norm:** median + P25/P75. Outliers filtered with Tukey 1.5×IQR fence per metric.
- **Low sample flag:** n < 10 (per ROADMAP Phase 6).
- **Data source:** synthetic CSVs in repo root, see `SYNTHETIC_DATA_README.md`.
  Real-data swap is just changing the source files — pipeline code is unchanged.
        """)
