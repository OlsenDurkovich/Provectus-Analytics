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
from .. import import_exports

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "assets"
PAGES_DIR = Path(__file__).parent / "pages"


def _data_state_panel() -> html.Div:
    """Live row counts for the sidebar — surfaces stale-state confusion at a glance."""
    counts = data.row_counts(data.DEFAULT_DB)
    rows = [
        ("Flights",   counts["flights"]),
        ("Invoices",  counts["invoices"]),
        ("Students",  counts["students"]),
        ("Surveys",   counts["surveys"]),
        ("Overrides", counts["flight_overrides"]),
    ]
    return html.Div(
        className="data-state",
        children=[
            html.Div("Data state", className="data-state-title"),
            *[
                html.Div(
                    className="data-state-row",
                    children=[
                        html.Span(label, className="data-state-label"),
                        html.Span(f"{n:,}", className="data-state-value"),
                    ],
                )
                for label, n in rows
            ],
        ],
    )


def _sidebar() -> html.Div:
    n_live = data.is_live_data(data.DEFAULT_DB)
    if n_live > 0:
        badge = html.Span(
            [html.Span(className="pulse"),
             f" Live · {n_live} client{'s' if n_live != 1 else ''}"],
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
                html.Img(src="/assets/Provectus.jpg", className="brand-logo",
                         alt="Provectus Aviation Unlimited"),
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
                html.Button(
                    [html.Span("Theme"), html.Span("Light", id="theme-label",
                                                   className="indicator")],
                    id="theme-toggle", className="theme-toggle", n_clicks=0,
                ),
                html.Button("Import latest FSP exports", id="import-btn",
                            className="rebuild-btn", n_clicks=0,
                            title="Copies the newest FSP report XLSX files from "
                                  "~/Downloads into FSP Exports/ with canonical "
                                  "names, then rebuilds the DB."),
                html.Button("Rebuild DB", id="rebuild-btn", className="rebuild-btn",
                            n_clicks=0),
                html.Div(id="rebuild-status",
                         style={"marginTop": "6px", "fontSize": "11px",
                                "color": "#a1a1aa", "whiteSpace": "pre-wrap"}),
                _data_state_panel(),
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
        external_stylesheets=[],
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

    # Theme toggle — runs entirely client-side, persists to localStorage.
    app.clientside_callback(
        """
        function(n_clicks) {
            var cur = document.documentElement.getAttribute('data-theme') || 'light';
            // On first paint, n_clicks is 0 — just return the current label, don't flip.
            if (!n_clicks) {
                return cur === 'dark' ? 'Dark' : 'Light';
            }
            var next = cur === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            try { localStorage.setItem('theme', next); } catch (e) {}
            return next === 'dark' ? 'Dark' : 'Light';
        }
        """,
        Output("theme-label", "children"),
        Input("theme-toggle", "n_clicks"),
    )

    # Rebuild button + Import-latest-FSP-exports button share a status div.
    @app.callback(
        Output("rebuild-status", "children"),
        Input("rebuild-btn", "n_clicks"),
        Input("import-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _refresh(rebuild_clicks, import_clicks):
        trigger = dash.callback_context.triggered_id
        if trigger == "import-btn":
            results = import_exports.import_latest()
            data.clear_caches()
            data.build_db(data.DEFAULT_DB)
            return import_exports.summarize(results) + "\nRebuilt. Refresh the page."
        if trigger == "rebuild-btn":
            data.clear_caches()
            data.build_db(data.DEFAULT_DB)
            return "Rebuilt. Refresh the page."
        return no_update

    return app


def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=8050, debug=False)


if __name__ == "__main__":
    main()
