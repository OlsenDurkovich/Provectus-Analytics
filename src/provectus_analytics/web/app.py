"""Dash app factory + layout shell.

Run from repo root:
    python app.py
"""
from __future__ import annotations

from pathlib import Path

import dash
from dash import Input, Output, State, dcc, html, no_update

from . import data
# Force-import theme so the Plotly template is registered before pages build figs
from . import theme  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "assets"
PAGES_DIR = Path(__file__).parent / "pages"


def _sidebar() -> html.Div:
    n_live = data.is_live_data(data.DEFAULT_DB)
    if n_live > 0:
        badge = html.Span(
            [html.Span(className="pulse"),
             f" Live · {n_live} student{'s' if n_live != 1 else ''}"],
            className="data-badge live",
        )
    else:
        badge = html.Span(
            [html.Span(className="pulse"), " Synthetic data"],
            className="data-badge",
        )

    return html.Div(
        className="sidebar",
        children=[
            html.Div(className="brand", children=[
                html.Div(className="brand-mark"),
                html.Div("Provectus", className="brand-name"),
            ]),
            html.Div(className="nav", children=[
                html.Div("Analytics", className="nav-section"),
                # nav links built dynamically from registered pages
                *[
                    dcc.Link(
                        html.Div([html.Span(className="dot"), p["name"]],
                                 className="nav-link",
                                 id={"type": "nav-link", "path": p["path"]}),
                        href=p["path"],
                        style={"textDecoration": "none"},
                    )
                    for p in sorted(dash.page_registry.values(),
                                    key=lambda p: p.get("order", 99))
                ],
            ]),
            html.Div(className="sidebar-foot", children=[
                badge,
                html.Div(
                    "Data source: " +
                    ("FSP Reporting Hub exports" if n_live > 0 else "synthetic CSVs"),
                ),
                html.Button("Rebuild DB", id="rebuild-btn", className="rebuild-btn",
                            n_clicks=0),
                html.Div(id="rebuild-status",
                         style={"marginTop": "6px", "fontSize": "11px",
                                "color": "#a1a1aa"}),
            ]),
        ],
    )


def create_app() -> dash.Dash:
    data.ensure_db(data.DEFAULT_DB)

    app = dash.Dash(
        __name__,
        use_pages=True,
        pages_folder=str(PAGES_DIR),
        assets_folder=str(ASSETS_DIR),
        title="Provectus Analytics",
        update_title=None,
        suppress_callback_exceptions=True,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        ],
    )

    app.layout = html.Div(
        className="app",
        children=[
            dcc.Location(id="url"),
            _sidebar(),
            html.Div(className="main", children=[
                dash.page_container,
            ]),
        ],
    )

    # Mark the active nav link based on current URL.
    @app.callback(
        Output({"type": "nav-link", "path": dash.ALL}, "className"),
        Input("url", "pathname"),
    )
    def _highlight(pathname: str):
        results = []
        for p in dash.callback_context.outputs_list:
            path = p["id"]["path"]
            is_active = (pathname == path) or (path == "/" and pathname in (None, "", "/"))
            results.append("nav-link active" if is_active else "nav-link")
        return results

    # Rebuild button
    @app.callback(
        Output("rebuild-status", "children"),
        Input("rebuild-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _rebuild(n_clicks):
        if not n_clicks:
            return no_update
        data.clear_caches()
        data.build_db(data.DEFAULT_DB)
        return "Rebuilt. Refresh the page."

    return app


def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=8050, debug=False)


if __name__ == "__main__":
    main()
