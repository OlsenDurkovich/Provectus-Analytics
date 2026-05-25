"""Reusable UI components — keep these pure (no DB access)."""
from __future__ import annotations

from dash import html


def page_header(eyebrow: str, title: str, sub: str | None = None,
                actions=None) -> html.Div:
    """Standard page header: eyebrow / title / subtitle, optional right-side actions."""
    left = [
        html.Div(eyebrow, className="page-eyebrow"),
        html.H1(title, className="page-title"),
    ]
    if sub:
        left.append(html.Div(sub, className="page-sub"))
    return html.Div(
        className="page-header",
        children=[
            html.Div(left),
            html.Div(actions or [], className="page-actions"),
        ],
    )


def metric_card(label: str, value: str, sub: str | None = None,
                delta: str | None = None, delta_kind: str = "neu") -> html.Div:
    """
    Stripe-style metric card.

    delta_kind: "pos" | "neg" | "neu" | "inv-pos" | "inv-neg"
        Use "inv-*" for metrics where lower is better (cost, hours, days) so
        a positive delta renders red, a negative renders green.
    """
    children = [
        html.Div(label, className="metric-label"),
        html.Div(value, className="metric-value"),
    ]
    if delta is not None:
        children.append(html.Div(delta, className=f"metric-delta {delta_kind}"))
    if sub is not None:
        children.append(html.Div(sub, className="metric-sub"))
    return html.Div(children, className="metric-card")


def metric_grid(cards) -> html.Div:
    return html.Div(cards, className="metric-grid")


def section(title: str, body, sub: str | None = None) -> html.Div:
    head_children = [html.Div(title, className="section-title")]
    if sub:
        head_children.append(html.Div(sub, className="section-sub"))
    return html.Div(
        className="section",
        children=[
            html.Div(head_children, className="section-head"),
            body,
        ],
    )


def card(children, tight: bool = False) -> html.Div:
    return html.Div(children, className=f"card{' tight' if tight else ''}")


def pill(text: str, kind: str = "") -> html.Span:
    cls = f"pill {kind}".strip()
    return html.Span(text, className=cls)


def table(columns: list[dict], rows: list[list]) -> html.Div:
    """
    Lightweight Stripe-style table.

    columns: [{"key": "...", "label": "...", "num": bool, "class": str}, ...]
    rows:    parallel list of cells. Each cell can be a string OR a dict like
             {"text": "...", "class": "delta-pos"} for per-cell styling.
    """
    thead = html.Thead(html.Tr([
        html.Th(c["label"], className=("num" if c.get("num") else ""))
        for c in columns
    ]))
    body_rows = []
    for row in rows:
        cells = []
        for cell, col in zip(row, columns):
            cls_parts = []
            if col.get("num"): cls_parts.append("num")
            if col.get("class"): cls_parts.append(col["class"])
            if isinstance(cell, dict):
                if cell.get("class"): cls_parts.append(cell["class"])
                text = cell.get("text", "")
            else:
                text = cell
            cells.append(html.Td(text, className=" ".join(cls_parts)))
        body_rows.append(html.Tr(cells))
    return html.Div(
        className="tbl-wrap",
        children=html.Table([thead, html.Tbody(body_rows)], className="tbl"),
    )


def callout(text: str) -> html.Div:
    return html.Div(text, className="callout")


def methodology(items: list[str]) -> html.Details:
    return html.Details(
        className="method",
        children=[
            html.Summary("Methodology"),
            html.Ul([html.Li(i) for i in items]),
        ],
    )
