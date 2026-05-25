"""Rating Detail — Whoop/Oura-style P25/P75 band visualization with student overlay."""
from __future__ import annotations

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from provectus_analytics.web import data
from provectus_analytics.web.components import (
    metric_card, metric_grid, page_header, section, methodology, table,
)
from provectus_analytics.web.theme import COLORS, base_layout

dash.register_page(__name__, path="/rating", name="Rating detail", order=1)


def _strip_with_band(
    values: list[float], p25: float, med: float, p75: float,
    student_value: float | None,
    student_name: str | None,
    title: str, value_fmt: str, prefix: str = "",
) -> go.Figure:
    """
    Whoop/Oura-style distribution: shaded P25–P75 band, median line, individual
    cohort points jittered as a strip, selected student highlighted.
    """
    fig = go.Figure()

    if not values:
        return fig

    y_min = min(values + ([student_value] if student_value is not None else []))
    y_max = max(values + ([student_value] if student_value is not None else []))
    y_pad = (y_max - y_min) * 0.08 or 1

    # Shaded P25–P75 band
    fig.add_shape(
        type="rect", xref="paper", yref="y",
        x0=0, x1=1, y0=p25, y1=p75,
        fillcolor=COLORS["accent_band"], line=dict(width=0), layer="below",
    )
    # Median line
    fig.add_shape(
        type="line", xref="paper", yref="y",
        x0=0, x1=1, y0=med, y1=med,
        line=dict(color=COLORS["accent_line"], width=1.5, dash="dot"),
    )
    # Cohort strip (jittered)
    import random
    random.seed(7)
    jitter = [0.4 + (random.random() - 0.5) * 0.35 for _ in values]
    fig.add_trace(go.Scatter(
        x=jitter, y=values, mode="markers",
        marker=dict(color=COLORS["text_faint"], size=7, opacity=0.55,
                    line=dict(width=0)),
        hovertemplate=f"{prefix}%{{y:{value_fmt}}}<extra>cohort</extra>",
        showlegend=False,
    ))
    # Selected student
    if student_value is not None:
        fig.add_trace(go.Scatter(
            x=[0.7], y=[student_value], mode="markers",
            marker=dict(color=COLORS["accent"], size=14, symbol="circle",
                        line=dict(color="#fff", width=2)),
            hovertemplate=(
                f"<b>{student_name}</b><br>{prefix}%{{y:{value_fmt}}}<extra></extra>"
            ),
            showlegend=False,
        ))

    fig.update_layout(
        **base_layout(
            height=300,
            xaxis=dict(visible=False, range=[0, 1]),
            yaxis=dict(
                title=title,
                range=[y_min - y_pad, y_max + y_pad],
                tickprefix=prefix,
                showgrid=True, gridcolor=COLORS["divider"],
                color=COLORS["text_muted"],
                tickfont=dict(size=11, color=COLORS["text_muted"]),
            ),
            margin=dict(l=44, r=12, t=8, b=12),
        )
    )
    return fig


def layout():
    norms = data.all_norms(str(data.DEFAULT_DB))
    if not norms:
        return html.Div([
            page_header("Detail", "Rating detail"),
            html.Div("No data found.", className="callout"),
        ])

    available = [n["rating"] for n in norms]
    default_rating = available[0]

    cohort = data.rating_cohort(str(data.DEFAULT_DB), default_rating)
    dates = pd.to_datetime(cohort["milestone_date"]) if not cohort.empty else pd.Series([])
    min_yr = int(dates.dt.year.min()) if not cohort.empty else 2020
    max_yr = int(dates.dt.year.max()) if not cohort.empty else 2026

    controls = html.Div(
        className="page-actions",
        children=[
            html.Div(className="select-wrap", children=[
                html.Div("Rating", className="select-label"),
                dcc.Dropdown(
                    id="rd-rating",
                    options=[{"label": r, "value": r} for r in available],
                    value=default_rating, clearable=False,
                    style={"width": "140px"},
                ),
            ]),
            html.Div(className="select-wrap", children=[
                html.Div("Overlay student", className="select-label"),
                dcc.Dropdown(
                    id="rd-student",
                    options=[], value=None,
                    placeholder="(none)", clearable=True,
                    style={"width": "240px"},
                ),
            ]),
        ],
    )

    return html.Div([
        page_header("Detail", "Rating detail",
                    "Cohort distribution with P25–P75 band. Compare an individual to the band.",
                    actions=[controls]),
        html.Div(id="rd-content"),
        methodology([
            "Shaded band = P25–P75 (middle 50%). Dotted line = median.",
            "Each grey dot is one alum's checkride outcome.",
            "Overlay student renders as the indigo dot.",
            "Cost / hours / days where lower is better — student below the band is more efficient.",
        ]),
    ])


# ── Callback ─────────────────────────────────────────────────────────────────
@dash.callback(
    Output("rd-student", "options"),
    Output("rd-student", "value"),
    Input("rd-rating", "value"),
)
def _update_student_options(rating: str):
    if not rating:
        return [], None
    cohort = data.rating_cohort(str(data.DEFAULT_DB), rating)
    opts = [{"label": s, "value": s} for s in cohort["student"].tolist()]
    return opts, None


@dash.callback(
    Output("rd-content", "children"),
    Input("rd-rating", "value"),
    Input("rd-student", "value"),
)
def _update_content(rating: str, student: str | None):
    if not rating:
        return html.Div()

    norms = data.all_norms(str(data.DEFAULT_DB))
    norm = next((n for n in norms if n["rating"] == rating), {})
    cohort = data.rating_cohort(str(data.DEFAULT_DB), rating)

    if cohort.empty:
        return html.Div(f"No checkride data for {rating}.", className="callout")

    sv = lambda col: (
        float(cohort.loc[cohort["student"] == student, col].iloc[0])
        if student and not cohort.loc[cohort["student"] == student].empty
        else None
    )

    # Metric row — cohort norms, plus selected-student deltas if any
    def _delta(actual, target, prefix="", fmt=".1f", inv=True):
        if actual is None or target is None:
            return None, "neu"
        d = actual - target
        sign = "+" if d > 0 else ""
        kind = ("inv-pos" if d > 0 else "inv-neg") if inv else ("pos" if d > 0 else "neg")
        return f"{sign}{prefix}{d:{fmt}} vs median", kind

    h_delta, h_kind = _delta(sv("hours"), norm.get("median_hours"), fmt=".1f")
    c_delta, c_kind = _delta(sv("cost"),  norm.get("median_cost"),  prefix="$", fmt=",.0f")
    d_delta, d_kind = _delta(sv("days"),  norm.get("median_days"),  fmt=".0f")

    metrics = metric_grid([
        metric_card("Alumni (n)", str(norm.get("n_raw", 0)),
                    sub=("⚠ Low sample (n<10)" if norm.get("low_sample_flag") else "Sufficient sample")),
        metric_card("Median hours", f"{norm.get('median_hours', 0):.1f}",
                    sub=f"P25–P75: {norm.get('p25_hours', 0):.1f} – {norm.get('p75_hours', 0):.1f}",
                    delta=h_delta, delta_kind=h_kind),
        metric_card("Median cost", f"${norm.get('median_cost', 0):,.0f}",
                    sub=f"P25–P75: ${norm.get('p25_cost', 0):,.0f} – ${norm.get('p75_cost', 0):,.0f}",
                    delta=c_delta, delta_kind=c_kind),
        metric_card("Median days", f"{int(norm.get('median_days', 0))}",
                    sub=f"P25–P75: {norm.get('p25_days', 0)} – {norm.get('p75_days', 0)}",
                    delta=d_delta, delta_kind=d_kind),
    ])

    # Three distribution charts side-by-side
    charts = html.Div(
        className="chart-grid-3",
        children=[
            html.Div(className="card", children=[
                html.Div(f"{data.RATING_DISPLAY.get(rating, rating)} — flight hours",
                         className="section-title", style={"marginBottom": "8px"}),
                dcc.Graph(figure=_strip_with_band(
                    cohort["hours"].tolist(),
                    norm.get("p25_hours", 0), norm.get("median_hours", 0), norm.get("p75_hours", 0),
                    sv("hours"), student, "Hours", ".1f",
                ), config={"displayModeBar": False}),
            ]),
            html.Div(className="card", children=[
                html.Div("Total cost", className="section-title", style={"marginBottom": "8px"}),
                dcc.Graph(figure=_strip_with_band(
                    cohort["cost"].tolist(),
                    norm.get("p25_cost", 0), norm.get("median_cost", 0), norm.get("p75_cost", 0),
                    sv("cost"), student, "USD", ",.0f", prefix="$",
                ), config={"displayModeBar": False}),
            ]),
            html.Div(className="card", children=[
                html.Div("Calendar days", className="section-title", style={"marginBottom": "8px"}),
                dcc.Graph(figure=_strip_with_band(
                    cohort["days"].tolist(),
                    norm.get("p25_days", 0), norm.get("median_days", 0), norm.get("p75_days", 0),
                    sv("days"), student, "Days", ".0f",
                ), config={"displayModeBar": False}),
            ]),
        ],
    )

    # Cohort table
    cols = [
        {"key": "s",  "label": "Student"},
        {"key": "h",  "label": "Hours", "num": True},
        {"key": "c",  "label": "Cost",  "num": True},
        {"key": "d",  "label": "Days",  "num": True},
        {"key": "f",  "label": "Flights", "num": True},
        {"key": "dt", "label": "Checkride", "class": "muted"},
    ]
    rows = []
    for _, r in cohort.iterrows():
        highlight = (student and r["student"] == student)
        s_cell = (html.Strong(r["student"]) if highlight else r["student"])
        rows.append([
            s_cell,
            f"{r['hours']:.1f}",
            f"${r['cost']:,.0f}",
            f"{int(r['days'])}",
            f"{int(r['flights'])}",
            r["milestone_date"],
        ])
    cohort_table = table(cols, rows)

    return html.Div([
        metrics,
        section(
            "Distribution vs " + (f"{student}" if student else "cohort"),
            charts,
            sub="Indigo band = P25–P75. Dotted line = median.",
        ),
        section("Cohort", cohort_table),
    ])
