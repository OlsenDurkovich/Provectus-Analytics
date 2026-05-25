"""Flights page — raw FSP flight rows with per-row override editing.

The primary use case is correcting auto-classifications that the ingest got
wrong (e.g. an "AMEL ground lesson" that the heuristic flagged as a flight
because the aircraft column wasn't blank). Edits are saved to the
flight_overrides table and survive every weekly re-import.

UI:
    - Filter by instructor, client (substring), date range, ground/flight.
    - Edit `is_ground_lesson`, `billing_category`, `aircraft_class`, and
      `reservation_type` inline.
    - "Save changes" computes the diff vs original rows and writes overrides;
      then triggers downstream recompute (partition + milestones).

Honesty:
    - Editing 1900+ row tables in DataTable is fine but not snappy. If this
      becomes a bottleneck, add server-side pagination.
    - The page only writes the four columns listed above. To extend, add the
      new column to _OVERRIDABLE_COLUMNS in ingest.py AND to EDITABLE_COLUMNS
      here.
"""
from __future__ import annotations

import sqlite3

import dash
import pandas as pd
from dash import Input, Output, State, dash_table, dcc, html, no_update

from provectus_analytics import db as _db, ingest, partition, milestones
from provectus_analytics.web import data
from provectus_analytics.web.components import page_header

dash.register_page(__name__, path="/flights", name="Flights", order=4)


# Columns the table exposes. `editable` is the inline-edit allowlist; must be a
# subset of ingest._OVERRIDABLE_COLUMNS to round-trip cleanly.
DISPLAY_COLUMNS = [
    {"id": "flight_id",        "name": "ID",          "editable": False, "type": "numeric"},
    {"id": "flight_date",      "name": "Date",        "editable": False},
    {"id": "client_raw",       "name": "Client",      "editable": False},
    {"id": "instructor",       "name": "Instructor",  "editable": False},
    {"id": "aircraft_tail",    "name": "Tail",        "editable": False},
    {"id": "aircraft_model",   "name": "Model",       "editable": False},
    {"id": "hobbs_hours",      "name": "Hobbs",       "editable": False, "type": "numeric"},
    {"id": "reservation_type", "name": "Type",        "editable": True},
    {"id": "billing_category", "name": "Billing",     "editable": True,
     "presentation": "dropdown"},
    {"id": "aircraft_class",   "name": "AC class",    "editable": True,
     "presentation": "dropdown"},
    {"id": "is_ground_lesson", "name": "Ground?",     "editable": True,
     "presentation": "dropdown", "type": "numeric"},
]

# Dropdown options for the editable columns.
DROPDOWN_OPTIONS = {
    "billing_category": [
        {"label": v, "value": v} for v in
        ["PRIMARY", "AMEL", "MEI", "CFI", "CFII", "MISC", "NONE"]
    ],
    "aircraft_class": [
        {"label": v, "value": v} for v in
        ["SE_BASIC", "SE_COMPLEX", "ME", ""]
    ],
    "is_ground_lesson": [
        {"label": "Flight (0)", "value": 0},
        {"label": "Ground (1)", "value": 1},
    ],
}

EDITABLE_COLUMNS = [c["id"] for c in DISPLAY_COLUMNS if c.get("editable")]


def _load_flights() -> pd.DataFrame:
    conn = sqlite3.connect(data.DEFAULT_DB)
    df = pd.read_sql(
        """SELECT flight_id, flight_date, client_raw, instructor,
                  aircraft_tail, aircraft_model, hobbs_hours,
                  reservation_type, billing_category, aircraft_class,
                  is_ground_lesson
           FROM flights
           ORDER BY flight_date DESC, flight_id DESC""",
        conn,
    )
    conn.close()
    # Normalize None → "" for string columns so DataTable dropdowns work
    for col in ["billing_category", "aircraft_class", "reservation_type",
                "instructor", "aircraft_tail", "aircraft_model", "client_raw"]:
        df[col] = df[col].fillna("")
    return df


def layout():
    df = _load_flights()
    if df.empty:
        return html.Div([
            page_header("Raw flight rows", "Flights"),
            html.Div("No flights ingested. Import FSP exports from the sidebar.",
                     className="callout"),
        ])

    instructors = sorted([i for i in df["instructor"].unique() if i])

    controls = html.Div(
        className="page-actions",
        style={"display": "flex", "gap": "12px", "alignItems": "flex-end",
               "flexWrap": "wrap"},
        children=[
            html.Div([
                html.Div("Instructor", className="select-label"),
                dcc.Dropdown(
                    id="fl-instructor",
                    options=[{"label": "All", "value": "__all__"}] +
                            [{"label": i, "value": i} for i in instructors],
                    value="__all__", clearable=False,
                    style={"width": "220px"},
                ),
            ]),
            html.Div([
                html.Div("Client contains", className="select-label"),
                dcc.Input(id="fl-client", type="text", value="",
                          style={"width": "200px"}),
            ]),
            html.Div([
                html.Div("Ground/Flight", className="select-label"),
                dcc.Dropdown(
                    id="fl-ground",
                    options=[
                        {"label": "All", "value": "__all__"},
                        {"label": "Ground only", "value": 1},
                        {"label": "Flight only", "value": 0},
                    ],
                    value="__all__", clearable=False,
                    style={"width": "170px"},
                ),
            ]),
            html.Button("Save changes", id="fl-save",
                        className="rebuild-btn",
                        style={"marginLeft": "auto"}),
            html.Div(id="fl-status",
                     style={"fontSize": "12px", "color": "#a1a1aa",
                            "alignSelf": "center"}),
        ],
    )

    # Match the dashboard's theme tokens. Computed once at layout time so
    # initial paint isn't broken before clientside JS sets data-theme.
    table = dash_table.DataTable(
        id="fl-table",
        columns=DISPLAY_COLUMNS,
        data=df.to_dict("records"),
        dropdown={
            col: {"options": opts}
            for col, opts in DROPDOWN_OPTIONS.items()
        },
        editable=True,
        filter_action="none",
        sort_action="native",
        page_size=50,
        style_table={"overflowX": "auto",
                     "border": "1px solid var(--divider)",
                     "borderRadius": "6px"},
        style_cell={
            "fontSize": "13px",
            "padding": "8px 10px",
            "fontFamily": "system-ui, -apple-system, sans-serif",
            "backgroundColor": "var(--bg-card)",
            "color": "var(--text)",
            "border": "none",
            "borderBottom": "1px solid var(--divider)",
        },
        style_header={
            "fontWeight": "600",
            "backgroundColor": "var(--bg-subtle)",
            "color": "var(--text)",
            "borderBottom": "1px solid var(--divider)",
        },
        style_data_conditional=[
            # Editable cells: subtle tint + accent left border so it's
            # obvious which columns accept edits.
            *[
                {
                    "if": {"column_id": col},
                    "backgroundColor": "var(--accent-band)",
                    "borderLeft": "2px solid var(--accent)",
                    "color": "var(--text)",
                }
                for col in EDITABLE_COLUMNS
            ],
        ],
    )

    return html.Div([
        page_header("Raw flight rows", "Flights",
                    "Edit Type, Billing, AC class, or Ground? to override the "
                    "auto-classification. Edits persist across weekly re-imports.",
                    actions=[]),
        controls,
        # dcc.Store keeps the original DB values so the save handler can diff.
        dcc.Store(id="fl-original", data=df.to_dict("records")),
        html.Div(style={"marginTop": "12px"}, children=table),
    ])


# Filter callback — re-renders the table data based on filter controls.
@dash.callback(
    Output("fl-table", "data"),
    Output("fl-original", "data"),
    Input("fl-instructor", "value"),
    Input("fl-client", "value"),
    Input("fl-ground", "value"),
)
def _filter(instructor, client, ground):
    df = _load_flights()
    if instructor and instructor != "__all__":
        df = df[df["instructor"] == instructor]
    if client:
        df = df[df["client_raw"].str.contains(client, case=False, na=False)]
    if ground != "__all__" and ground is not None:
        df = df[df["is_ground_lesson"] == int(ground)]
    rows = df.to_dict("records")
    return rows, rows


# Save callback — compare current rows vs originals, write overrides for changed cells.
@dash.callback(
    Output("fl-status", "children"),
    Input("fl-save", "n_clicks"),
    State("fl-table", "data"),
    State("fl-original", "data"),
    prevent_initial_call=True,
)
def _save(n_clicks, current_rows, original_rows):
    if not n_clicks:
        return no_update

    by_id_orig = {r["flight_id"]: r for r in original_rows}
    changes = []  # list of (flight_id, field, new_value)
    for row in current_rows:
        fid = row["flight_id"]
        orig = by_id_orig.get(fid)
        if orig is None:
            continue
        for field in EDITABLE_COLUMNS:
            new_val = row.get(field)
            old_val = orig.get(field)
            # Normalize empty strings → None for comparison
            if new_val == "":
                new_val = None
            if old_val == "":
                old_val = None
            if new_val != old_val:
                changes.append((fid, field, new_val))

    if not changes:
        return "No changes."

    conn = _db.open_or_create(data.DEFAULT_DB)
    for fid, field, val in changes:
        if val is None or val == "":
            ingest.clear_flight_override(conn, fid, field)
            conn.execute(
                f"UPDATE flights SET {field} = NULL WHERE flight_id = ?", (fid,))
        else:
            ingest.set_flight_override(conn, fid, field, val,
                                       note="Edited via Flights page")
            # Apply immediately to the live row
            cast = ingest._OVERRIDABLE_COLUMNS[field](val)
            conn.execute(
                f"UPDATE flights SET {field} = ? WHERE flight_id = ?",
                (cast, fid))
    conn.commit()

    # Re-run downstream so milestones reflect the new ground/flight split.
    partition.partition_flights(conn)
    milestones.compute_milestones(conn)
    conn.close()

    data.clear_caches()
    return f"Saved {len(changes)} change{'s' if len(changes) != 1 else ''}."
