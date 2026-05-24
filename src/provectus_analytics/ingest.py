"""Load CSV exports into the SQLite DB.

After ingest:
    - students table has one row per FSP client (no survey link yet)
    - flights / invoices loaded (student_id still NULL — reconcile.py sets it)
    - surveys raw responses stored

Reconciliation, enrollment building, partitioning, and milestone computation
all happen downstream.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

# Aircraft class derivation by model — matches synthetic fleet.
# Real data: extend this map or derive from FSP categoryClass field once API is live.
AIRCRAFT_CLASS = {
    "172N": "SE_BASIC", "172S": "SE_BASIC", "PA-28-181": "SE_BASIC",
    "182RG": "SE_COMPLEX", "PA-28R-201": "SE_COMPLEX",
    "PA-44-180": "ME",
}


def classify_aircraft(model: str) -> str | None:
    if not model:
        return None
    return AIRCRAFT_CLASS.get(model.strip(), "SE_BASIC")  # default — flag in partition.py


def ingest_clients(conn: sqlite3.Connection, clients_csv: Path) -> int:
    """Load FSP client roster into students table."""
    with open(clients_csv) as f:
        rows = list(csv.DictReader(f))
    conn.executemany(
        """INSERT INTO students (fsp_client_id, fsp_display_name, email, match_status)
           VALUES (?, ?, ?, 'unmatched')""",
        [(r["Client ID"], r["Display Name"], r["Email"]) for r in rows],
    )
    conn.commit()
    return len(rows)


def ingest_reservations(conn: sqlite3.Connection, reservations_csv: Path) -> int:
    """Load FSP reservations into flights table. student_id stays NULL until reconcile runs."""
    with open(reservations_csv) as f:
        rows = list(csv.DictReader(f))
    conn.executemany(
        """INSERT INTO flights (
               fsp_reservation, fsp_flight_num, flight_date, length_hrs,
               reservation_type, status, client_raw, aircraft_tail, aircraft_make,
               aircraft_model, aircraft_class, instructor
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                r["Reservation #"],
                r["Flight #"] or None,
                r["Date"],
                float(r["Length (hrs)"]) if r["Length (hrs)"] else 0.0,
                r["Reservation Type"],
                r["Status"],
                r["Client"] or None,
                r["Aircraft Tail"] or None,
                r["Aircraft Make"] or None,
                r["Aircraft Model"] or None,
                classify_aircraft(r["Aircraft Model"]),
                r["Instructor"] or None,
            )
            for r in rows
        ],
    )
    conn.commit()
    return len(rows)


def ingest_invoices(conn: sqlite3.Connection, invoices_csv: Path) -> int:
    """Load FSP invoice lines. flight_id resolved by reservation number lookup."""
    with open(invoices_csv) as f:
        rows = list(csv.DictReader(f))

    # Build reservation → flight_id map
    res_map = {
        row["fsp_reservation"]: row["flight_id"]
        for row in conn.execute("SELECT flight_id, fsp_reservation FROM flights")
    }
    conn.executemany(
        """INSERT INTO invoices (
               fsp_invoice, invoice_date, flight_id, description, category,
               qty, rate, amount, status
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                r["Invoice #"],
                r["Invoice Date"],
                res_map.get(r["Reservation #"]),
                r["Line Item Description"],
                r["Category"],
                float(r["Quantity (hrs/units)"]) if r["Quantity (hrs/units)"] else None,
                float(r["Rate ($)"]) if r["Rate ($)"] else None,
                float(r["Amount ($)"]),
                r["Status"],
            )
            for r in rows
        ],
    )
    conn.commit()
    return len(rows)


def ingest_survey(conn: sqlite3.Connection, survey_csv: Path) -> int:
    """Store raw survey responses in the surveys table. Linking to students happens in reconcile.py."""
    with open(survey_csv) as f:
        rows = list(csv.DictReader(f))
    conn.executemany(
        """INSERT INTO surveys (student_id, submitted_at, raw_response)
           VALUES (NULL, ?, ?)""",
        [(r.get("Timestamp"), json.dumps(r)) for r in rows],
    )
    conn.commit()
    return len(rows)


def ingest_all(
    conn: sqlite3.Connection,
    clients_csv: Path,
    reservations_csv: Path,
    invoices_csv: Path,
    survey_csv: Path,
) -> dict[str, int]:
    """Convenience: load all four files in the correct order."""
    return {
        "clients": ingest_clients(conn, clients_csv),
        "reservations": ingest_reservations(conn, reservations_csv),
        "invoices": ingest_invoices(conn, invoices_csv),
        "surveys": ingest_survey(conn, survey_csv),
    }
