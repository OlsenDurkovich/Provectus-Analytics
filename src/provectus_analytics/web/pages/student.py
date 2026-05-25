"""Student drill-down — the Strava-analogue flagship page.

Timeline of ratings + milestones, per-rating cards showing delta-vs-cohort-median,
and milestone tables. The closest thing this app has to Strava's activity-detail view.
"""
from __future__ import annotations

import dash
import pandas as pd
from dash import Input, Output, dcc, html

from provectus_analytics.web import data
from provectus_analytics.web.components import (
    metric_card, metric_grid, page_header, section, methodology, table,
)
from provectus_analytics.web.theme import COLORS

dash.register_page(__name__, path="/student", name="Student", order=2)


def _timeline(traj: pd.DataFrame) -> html.Div:
    """
    Per-rating horizontal bars with milestone dots — Strava-style activity bar
    but stacked vertically by rating.
    """
    if traj.empty:
        return html.Div("No milestones recorded.", className="prose")

    # Establish a global date axis across all the student's ratings
    traj = traj.copy()
    traj["date"] = pd.to_datetime(traj["milestone_date"])
    global_min = traj["date"].min()
    global_max = traj["date"].max()
    total_span = max((global_max - global_min).days, 1)

    rows = []
    for rating, group in traj.groupby("rating", sort=False):
        group = group.sort_values("date")
        r_start = group["date"].min()
        r_end = group["date"].max()
        # left edge & width as % of global span
        left_pct = (r_start - global_min).days / total_span * 100
        width_pct = max((r_end - r_start).days / total_span * 100, 1.5)

        # Dots within the rating bar
        dots = []
        for _, m in group.iterrows():
            pos_pct = (m["date"] - global_min).days / total_span * 100
            classes = "timeline-dot" + (" checkride" if m["milestone"] == "checkride" else "")
            label = data.MILESTONE_LABELS.get(m["milestone"], m["milestone"])
            dots.append(html.Div(
                className=classes,
                style={"left": f"{pos_pct}%"},
                title=f"{label} — {m['milestone_date']}",
            ))

        # Total per-rating duration & cost — shown as right-side caption
        end_row = group.iloc[-1]
        sub = f"{int(end_row['days'])}d · {end_row['hours']:.1f}h · ${end_row['cost']:,.0f}"

        rows.append(html.Div(
            className="timeline-rating",
            children=[
                html.Div(className="rating-tag", children=[
                    rating,
                    html.Span(data.RATING_DISPLAY.get(rating, ""), className="sub"),
                ]),
                html.Div(className="timeline-bar", children=[
                    html.Div(className="timeline-fill",
                             style={"left": f"{left_pct}%", "width": f"{width_pct}%"}),
                    *dots,
                    html.Div(sub, style={
                        "position": "absolute",
                        "top": "-22px",
                        "right": "0",
                        "fontSize": "11px",
                        "color": COLORS["text_muted"],
                        "fontVariantNumeric": "tabular-nums",
                    }),
                ]),
            ],
        ))

    # X-axis labels (start / end)
    axis = html.Div(
        style={
            "display": "grid", "gridTemplateColumns": "130px 1fr", "gap": "16px",
            "fontSize": "11px", "color": COLORS["text_muted"], "marginTop": "12px",
            "fontVariantNumeric": "tabular-nums",
        },
        children=[
            html.Div(""),
            html.Div(style={"display": "flex", "justifyContent": "space-between"},
                     children=[
                         html.Span(global_min.strftime("%b %Y")),
                         html.Span(global_max.strftime("%b %Y")),
                     ]),
        ],
    )

    return html.Div([html.Div(rows, className="timeline"), axis])


def layout():
    students = data.all_students(str(data.DEFAULT_DB))
    if not students:
        return html.Div([
            page_header("Drill-down", "Student"),
            html.Div("No student data found.", className="callout"),
        ])

    controls = html.Div(
        className="page-actions",
        children=[
            html.Div(className="select-wrap", children=[
                html.Div("Student", className="select-label"),
                dcc.Dropdown(
                    id="st-student",
                    options=[{"label": s, "value": s} for s in students],
                    value=students[0], clearable=False,
                    style={"width": "260px"},
                ),
            ]),
        ],
    )

    return html.Div([
        page_header("Drill-down", "Student",
                    "Per-student journey across all ratings, with cohort-comparison deltas.",
                    actions=[controls]),
        html.Div(id="st-content"),
    ])


@dash.callback(
    Output("st-content", "children"),
    Input("st-student", "value"),
)
def _update(student: str):
    if not student:
        return html.Div()

    traj = data.student_trajectory(str(data.DEFAULT_DB), student)
    if traj.empty:
        return html.Div(f"No milestone data for {student}.", className="callout")

    norms = data.all_norms(str(data.DEFAULT_DB))
    norm_by_rating = {n["rating"]: n for n in norms}

    cr = traj[traj["milestone"] == "checkride"]

    # Hero: aggregate across all ratings completed
    total_hours = float(cr["hours"].sum())
    total_cost = float(cr["cost"].sum())
    total_days = int(cr["days"].sum())
    ratings_done = cr["rating"].tolist()

    hero = metric_grid([
        metric_card("Ratings completed", str(len(ratings_done)),
                    sub=", ".join(ratings_done) if ratings_done else "—"),
        metric_card("Total flight hours", f"{total_hours:.1f}",
                    sub="Sum across ratings"),
        metric_card("Total cost", f"${total_cost:,.0f}",
                    sub="Sum across ratings"),
        metric_card("Training days", f"{total_days}",
                    sub="Sum of per-rating durations"),
    ])

    # Timeline
    tl = html.Div(className="card", children=_timeline(traj))

    # Per-rating cards (one row of 3 metrics each)
    per_rating_blocks = []
    for r in ratings_done:
        row = cr[cr["rating"] == r].iloc[0]
        norm = norm_by_rating.get(r, {})

        def delta(actual, target, prefix="", fmt=".1f"):
            if target is None:
                return None, "neu"
            d = actual - target
            sign = "+" if d > 0 else ""
            # lower is better for hours/cost/days
            kind = "inv-pos" if d > 0 else "inv-neg"
            return f"{sign}{prefix}{d:{fmt}} vs median", kind

        h_d, h_k = delta(row["hours"], norm.get("median_hours"), fmt=".1f")
        c_d, c_k = delta(row["cost"],  norm.get("median_cost"),  prefix="$", fmt=",.0f")
        d_d, d_k = delta(row["days"],  norm.get("median_days"),  fmt=".0f")

        flag = "warn" if norm.get("low_sample_flag") else ""
        flag_text = f"n={norm.get('n_raw', '?')}" + (" · low sample" if flag else "")

        cards = metric_grid([
            metric_card("Hours", f"{row['hours']:.1f}",
                        delta=h_d, delta_kind=h_k,
                        sub=f"Cohort median: {norm.get('median_hours', 0):.1f}"),
            metric_card("Cost", f"${row['cost']:,.0f}",
                        delta=c_d, delta_kind=c_k,
                        sub=f"Cohort median: ${norm.get('median_cost', 0):,.0f}"),
            metric_card("Days", f"{int(row['days'])}",
                        delta=d_d, delta_kind=d_k,
                        sub=f"Cohort median: {int(norm.get('median_days', 0))}"),
            metric_card("Flights", f"{int(row['flights'])}",
                        sub=f"Cohort median: {int(norm.get('median_flights', 0))}"),
        ])

        # Milestone table for this rating
        r_traj = traj[traj["rating"] == r].copy()
        cols = [
            {"key": "m",  "label": "Milestone"},
            {"key": "dt", "label": "Date", "class": "muted"},
            {"key": "d",  "label": "Days from start", "num": True},
            {"key": "fl", "label": "Flights", "num": True},
            {"key": "h",  "label": "Hours", "num": True},
            {"key": "c",  "label": "Cost",  "num": True},
        ]
        rows_t = [
            [data.MILESTONE_LABELS.get(m["milestone"], m["milestone"]),
             m["milestone_date"], int(m["days"]),
             int(m["flights"]), f"{m['hours']:.1f}", f"${m['cost']:,.0f}"]
            for _, m in r_traj.iterrows()
        ]

        per_rating_blocks.append(html.Div(
            className="section",
            children=[
                html.Div(className="section-head", children=[
                    html.Div([
                        html.Span(r, className="section-title"),
                        html.Span(f"  {data.RATING_DISPLAY.get(r, r)}",
                                  style={"color": COLORS["text_muted"],
                                         "marginLeft": "10px", "fontSize": "13px"}),
                    ]),
                    html.Span(flag_text, className=f"pill {flag}".strip()),
                ]),
                cards,
                html.Div(style={"marginTop": "12px"}, children=table(cols, rows_t)),
            ],
        ))

    return html.Div([
        hero,
        section("Training journey", tl,
                sub="Each row is a rating. Dots are milestones. Right caption = duration · hours · cost."),
        *per_rating_blocks,
        methodology([
            "Delta vs median uses the cohort's median for that rating.",
            "Red = above median (less efficient); green = below median.",
            "For ratings with n < 10 alumni, the comparison is flagged as low sample.",
        ]),
    ])
