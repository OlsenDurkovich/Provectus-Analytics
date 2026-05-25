"""Instructor view — Linear-style dense efficiency table + cohort comparison."""
from __future__ import annotations

import dash
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from provectus_analytics.web import data
from provectus_analytics.web.components import (
    awaiting_surveys_callout, metric_card, metric_grid, page_header,
    section, methodology, table,
)
from provectus_analytics.web.theme import COLORS, base_layout

dash.register_page(__name__, path="/instructor", name="Instructor", order=3)


def _cohort_compare(cohort_hours: list[float], inst_hours: list[float],
                    instructor: str) -> go.Figure:
    """
    Side-by-side strip + median lines. Simpler than a box plot, easier to read,
    same information. Whoop-ish.
    """
    import random
    random.seed(11)
    fig = go.Figure()

    def jitter(n, center): return [center + (random.random() - 0.5) * 0.32 for _ in range(n)]

    # Cohort points
    fig.add_trace(go.Scatter(
        x=jitter(len(cohort_hours), 0.3), y=cohort_hours, mode="markers",
        marker=dict(color=COLORS["text_faint"], size=8, opacity=0.55),
        hovertemplate="%{y:.1f}h<extra>Cohort</extra>",
        showlegend=False,
    ))
    if cohort_hours:
        import statistics
        med_c = statistics.median(cohort_hours)
        fig.add_shape(type="line", x0=0.15, x1=0.45, y0=med_c, y1=med_c,
                      line=dict(color=COLORS["text_muted"], width=2))
        fig.add_annotation(x=0.3, y=med_c, text=f"cohort med  {med_c:.1f}h",
                           showarrow=False, yshift=14,
                           font=dict(size=10, color=COLORS["text_muted"]))

    # Instructor points
    fig.add_trace(go.Scatter(
        x=jitter(len(inst_hours), 0.75), y=inst_hours, mode="markers",
        marker=dict(color=COLORS["accent"], size=10, opacity=0.85,
                    line=dict(color="#fff", width=1.5)),
        hovertemplate="%{y:.1f}h<extra>" + instructor + "</extra>",
        showlegend=False,
    ))
    if inst_hours:
        import statistics
        med_i = statistics.median(inst_hours)
        fig.add_shape(type="line", x0=0.6, x1=0.9, y0=med_i, y1=med_i,
                      line=dict(color=COLORS["accent"], width=2))
        fig.add_annotation(x=0.75, y=med_i, text=f"{instructor.split()[0]} med  {med_i:.1f}h",
                           showarrow=False, yshift=14,
                           font=dict(size=10, color=COLORS["accent"]))

    fig.update_layout(**base_layout(
        height=340,
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(title="Flight hours to checkride", showgrid=True,
                   gridcolor=COLORS["divider"]),
        margin=dict(l=50, r=12, t=20, b=12),
    ))
    return fig


def layout():
    insts = data.instructors(str(data.DEFAULT_DB))
    if not insts:
        return html.Div([
            page_header("People", "Instructor"),
            html.Div("No instructor data found.", className="callout"),
        ])

    controls = html.Div(
        className="page-actions",
        children=[
            html.Div(className="select-wrap", children=[
                html.Div("Instructor", className="select-label"),
                dcc.Dropdown(
                    id="iv-inst",
                    options=[{"label": i, "value": i} for i in insts],
                    value=insts[0], clearable=False,
                    style={"width": "260px"},
                ),
            ]),
        ],
    )

    return html.Div([
        page_header("People", "Instructor",
                    "Efficiency relative to cohort medians, per rating.",
                    actions=[controls]),
        html.Div(id="iv-content"),
        methodology([
            "Instructor median = median of their students' checkride outcomes for that rating.",
            "Δ vs cohort = instructor median minus the cohort median for that rating.",
            "Negative Δ on hours/cost/days = students completed faster/cheaper than cohort.",
        ]),
    ])


@dash.callback(
    Output("iv-content", "children"),
    Input("iv-inst", "value"),
)
def _update(instructor: str):
    if not instructor:
        return html.Div()

    detail = data.instructor_detail(str(data.DEFAULT_DB), instructor)
    if detail.empty:
        if data.has_flights_no_surveys(data.DEFAULT_DB):
            return awaiting_surveys_callout(f"per-instructor efficiency for {instructor}")
        return html.Div(f"No checkride data for {instructor}.", className="callout")

    norms = data.all_norms(str(data.DEFAULT_DB))
    norm_by_rating = {n["rating"]: n for n in norms}
    ratings_taught = detail.sort_values("sort_order")["rating"].unique().tolist()

    # Hero metrics — kept minimal; the per-rating efficiency table below carries
    # the real signal (cross-rating medians aren't comparable).
    hero = metric_grid([
        metric_card("Ratings taught", str(len(ratings_taught)),
                    sub=", ".join(ratings_taught)),
        metric_card("Students at checkride", str(detail["student"].nunique()),
                    sub="Counted once per rating completed"),
    ])

    # Efficiency table — Linear-dense
    cols = [
        {"key": "r",  "label": "Rating"},
        {"key": "n",  "label": "Students", "num": True},
        {"key": "h",  "label": "Inst. med hrs", "num": True},
        {"key": "dh", "label": "Δ vs cohort", "num": True},
        {"key": "c",  "label": "Inst. med cost", "num": True},
        {"key": "dc", "label": "Δ vs cohort", "num": True},
        {"key": "d",  "label": "Inst. med days", "num": True},
        {"key": "dd", "label": "Δ vs cohort", "num": True},
    ]
    rows = []
    for r in ratings_taught:
        r_rows = detail[detail["rating"] == r]
        norm = norm_by_rating.get(r, {})
        med_h = norm.get("median_hours")
        med_c = norm.get("median_cost")
        med_d = norm.get("median_days")
        ih = r_rows["hours"].median()
        ic = r_rows["cost"].median()
        id_ = r_rows["days"].median()

        def cell(actual, target, fmt: str, prefix: str = "", inv: bool = True):
            if actual is None or target is None:
                return {"text": "—", "class": "delta-neu"}
            d = actual - target
            sign = "+" if d > 0 else ""
            cls = "delta-neu"
            if abs(d) > 0.05:
                pos_is_good = not inv
                cls = "delta-pos" if (d > 0) == pos_is_good else "delta-neg"
            return {"text": f"{sign}{prefix}{d:{fmt}}", "class": cls}

        rows.append([
            html.Span([
                html.Strong(r),
                html.Span(f"  {data.RATING_DISPLAY.get(r, '')}",
                          style={"color": COLORS["text_muted"], "marginLeft": "8px",
                                 "fontSize": "12px"}),
            ]),
            str(len(r_rows)),
            f"{ih:.1f}",
            cell(ih, med_h, ".1f"),
            f"${ic:,.0f}",
            cell(ic, med_c, ",.0f", prefix="$"),
            f"{int(id_)}",
            cell(id_, med_d, ".0f"),
        ])
    eff_table = table(cols, rows)

    # Rating filter for the comparison chart
    chart_controls = html.Div(
        className="page-actions",
        style={"marginBottom": "10px"},
        children=[
            html.Div(className="select-wrap", children=[
                html.Div("Compare on", className="select-label"),
                dcc.Dropdown(
                    id="iv-rating",
                    options=[{"label": r, "value": r} for r in ratings_taught],
                    value=ratings_taught[0], clearable=False,
                    style={"width": "120px"},
                ),
            ]),
        ],
    )

    # Student roster
    s_cols = [
        {"key": "s", "label": "Student"},
        {"key": "r", "label": "Rating"},
        {"key": "h", "label": "Hours",  "num": True},
        {"key": "c", "label": "Cost",   "num": True},
        {"key": "d", "label": "Days",   "num": True},
        {"key": "f", "label": "Flights", "num": True},
        {"key": "dt", "label": "Checkride", "class": "muted"},
    ]
    s_rows = [
        [r["student"], r["rating"], f"{r['hours']:.1f}",
         f"${r['cost']:,.0f}", str(int(r["days"])), str(int(r["flights"])),
         r["milestone_date"]]
        for _, r in detail.iterrows()
    ]
    roster = table(s_cols, s_rows)

    return html.Div([
        hero,
        section("Efficiency vs cohort", eff_table),
        section("Hours-to-checkride comparison",
                html.Div([chart_controls,
                          html.Div(className="card", children=[
                              dcc.Graph(id="iv-chart", config={"displayModeBar": False}),
                          ])]),
                sub="Each dot is one student. Indigo = this instructor's students."),
        section("Student roster", roster),
    ])


@dash.callback(
    Output("iv-chart", "figure"),
    Input("iv-inst", "value"),
    Input("iv-rating", "value"),
)
def _update_chart(instructor: str, rating: str):
    cohort = data.rating_cohort(str(data.DEFAULT_DB), rating)
    detail = data.instructor_detail(str(data.DEFAULT_DB), instructor)
    inst_h = detail[detail["rating"] == rating]["hours"].tolist()
    return _cohort_compare(cohort["hours"].tolist(), inst_h, instructor)
