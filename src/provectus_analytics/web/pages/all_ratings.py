"""All Ratings — cohort overview across PPL/IFR/COM/AMEL/CFI/CFII/MEI."""
from __future__ import annotations

import dash
import plotly.graph_objects as go
from dash import html

from provectus_analytics.web import data
from provectus_analytics.web.components import (
    metric_card, metric_grid, page_header, section, methodology, table,
)
from provectus_analytics.web.theme import COLORS, base_layout

dash.register_page(__name__, path="/", name="Overview", order=0)


def _bar(metric_name: str, color: str, value_fmt: str, prefix: str = "") -> go.Figure:
    norms = data.all_norms(str(data.DEFAULT_DB))
    names = [n["rating"] for n in norms]
    med = [n[f"median_{metric_name}"] for n in norms]
    p25 = [n[f"p25_{metric_name}"] for n in norms]
    p75 = [n[f"p75_{metric_name}"] for n in norms]

    fig = go.Figure()
    # P25–P75 band as a thin invisible bar topped by a thin marker
    fig.add_trace(go.Bar(
        x=names, y=med,
        marker=dict(color=color, line=dict(width=0)),
        width=0.55,
        error_y=dict(
            type="data", symmetric=False,
            array=[hi - m for hi, m in zip(p75, med)],
            arrayminus=[m - lo for lo, m in zip(p25, med)],
            color=COLORS["text_faint"], thickness=1.2, width=4,
        ),
        hovertemplate=(
            "<b>%{x}</b><br>"
            f"Median: {prefix}%{{y:{value_fmt}}}<br>"
            "<extra></extra>"
        ),
    ))
    layout = base_layout(height=260, yaxis=dict(rangemode="tozero"))
    if prefix == "$":
        layout["yaxis"] = dict(rangemode="tozero", tickprefix="$", showgrid=True,
                               gridcolor=COLORS["divider"])
    fig.update_layout(**layout)
    return fig


def layout():
    norms = data.all_norms(str(data.DEFAULT_DB))
    if not norms:
        return html.Div([
            page_header("Cohort", "All Ratings"),
            html.Div("No milestone data found. Rebuild the DB from the sidebar.",
                     className="callout"),
        ])

    # Aggregate roll-ups across all ratings — Stripe-style hero metrics
    total_students = sum(n["n_raw"] for n in norms)
    total_ratings = len(norms)
    low_sample = sum(1 for n in norms if n["low_sample_flag"])

    hero = metric_grid([
        metric_card("Ratings tracked", str(total_ratings),
                    sub=f"{', '.join(n['rating'] for n in norms)}"),
        metric_card("Checkrides in dataset", f"{total_students}",
                    sub="Sum of cohort sizes across ratings"),
        metric_card("Low-sample ratings", f"{low_sample}",
                    sub=f"n < 10 ({'OK' if low_sample == 0 else 'norms are indicative only'})"),
    ])

    # Summary table — rating x medians
    cols = [
        {"key": "rating", "label": "Rating"},
        {"key": "n",      "label": "n", "num": True},
        {"key": "h",      "label": "Median hrs", "num": True},
        {"key": "hr",     "label": "P25–P75 hrs", "num": True, "class": "muted"},
        {"key": "c",      "label": "Median cost", "num": True},
        {"key": "cr",     "label": "P25–P75 cost", "num": True, "class": "muted"},
        {"key": "d",      "label": "Median days", "num": True},
        {"key": "flag",   "label": ""},
    ]
    rows = []
    for n in norms:
        rows.append([
            html.Span([
                html.Strong(n["rating"]),
                html.Span(f"  {data.RATING_DISPLAY.get(n['rating'], '')}",
                          style={"color": COLORS["text_muted"], "marginLeft": "8px",
                                 "fontSize": "12px"}),
            ]),
            str(n["n_raw"]),
            f"{n['median_hours']:.1f}",
            f"{n['p25_hours']:.1f} – {n['p75_hours']:.1f}",
            f"${n['median_cost']:,.0f}",
            f"${n['p25_cost']:,.0f} – ${n['p75_cost']:,.0f}",
            str(int(n["median_days"])),
            (html.Span("low sample", className="pill warn")
             if n["low_sample_flag"] else ""),
        ])
    summary_table = table(cols, rows)

    return html.Div([
        page_header(
            "Cohort overview",
            "All ratings",
            "Median + P25–P75 to checkride for each rating. Built from alumni-reported boundary dates and FSP flight data.",
        ),
        hero,
        section("Cohort norms", summary_table),
        section(
            "Median flight hours to checkride",
            html.Div(
                dash.dcc.Graph(figure=_bar("hours", COLORS["accent"], ".1f"),
                               config={"displayModeBar": False}),
                className="card",
            ),
            sub="Whiskers show P25–P75 band",
        ),
        section(
            "Median cost to checkride",
            html.Div(
                dash.dcc.Graph(figure=_bar("cost", COLORS["success"], ",.0f", prefix="$"),
                               config={"displayModeBar": False}),
                className="card",
            ),
            sub="Whiskers show P25–P75 band",
        ),
        section(
            "Median calendar days to checkride",
            html.Div(
                dash.dcc.Graph(figure=_bar("days", COLORS["warning"], ".0f"),
                               config={"displayModeBar": False}),
                className="card",
            ),
            sub="Whiskers show P25–P75 band",
        ),
        methodology([
            "Norms: median + P25/P75 per rating. Tukey 1.5×IQR fence applied per metric.",
            "Low-sample flag at n < 10 (ROADMAP Phase 6).",
            "Source: synthetic CSVs unless live FSP data has been ingested.",
            "Milestones: PPL → first_solo, xc_solos_complete, checkride. IFR → xc_pic_complete, checkride. Others → checkride only.",
        ]),
    ])
