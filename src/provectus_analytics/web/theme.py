"""Plotly theme + color tokens — keep in sync with assets/styles.css."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# Mirror of CSS tokens so charts and DOM agree.
COLORS = {
    # Charts use neutral mid-tones so figures render acceptably in both light
    # and dark mode without regenerating them on theme switch.
    "text":        "#71717a",                       # neutral gray reads on both
    "text_muted":  "#8b8d92",
    "text_faint":  "#9c9ca3",
    "border":      "rgba(127,127,127,0.22)",
    "divider":     "rgba(127,127,127,0.18)",
    "bg":          "rgba(0,0,0,0)",
    "bg_subtle":   "rgba(127,127,127,0.06)",
    "accent":      "#6f7ad8",                       # tuned for both modes
    "accent_band": "rgba(111, 122, 216, 0.18)",
    "accent_line": "rgba(111, 122, 216, 0.55)",
    "success":     "#10b981",
    "danger":      "#ef4444",
    "warning":     "#f59e0b",
}

FONT_FAMILY = (
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Roboto, Oxygen, Ubuntu, sans-serif"
)

# A single restrained Plotly template — used as default for all figures.
_TEMPLATE = go.layout.Template()
_TEMPLATE.layout = dict(
    font=dict(family=FONT_FAMILY, size=12, color=COLORS["text"]),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=8, r=8, t=8, b=8),
    colorway=[COLORS["accent"], COLORS["success"], COLORS["warning"], COLORS["danger"]],
    xaxis=dict(
        showgrid=False,
        showline=False,
        ticks="",
        zeroline=False,
        color=COLORS["text_muted"],
        title=dict(font=dict(size=11, color=COLORS["text_muted"])),
        tickfont=dict(size=11, color=COLORS["text_muted"]),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor=COLORS["divider"],
        gridwidth=1,
        showline=False,
        ticks="",
        zeroline=False,
        color=COLORS["text_muted"],
        title=dict(font=dict(size=11, color=COLORS["text_muted"])),
        tickfont=dict(size=11, color=COLORS["text_muted"]),
    ),
    hoverlabel=dict(
        bgcolor="#1f2024",
        bordercolor="#1f2024",
        font=dict(family=FONT_FAMILY, size=12, color="#fff"),
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        font=dict(size=11, color=COLORS["text_muted"]),
        bgcolor="rgba(0,0,0,0)",
    ),
)

pio.templates["provectus"] = _TEMPLATE
pio.templates.default = "provectus"


def base_layout(height: int = 280, **overrides) -> dict:
    """Common layout kwargs for compact, low-chrome charts."""
    layout = dict(
        height=height,
        margin=dict(l=8, r=8, t=8, b=24),
        showlegend=False,
    )
    layout.update(overrides)
    return layout
