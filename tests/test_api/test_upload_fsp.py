"""Tests for the Phase 12 upload endpoint."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient

from provectus_analytics.api import create_app
from provectus_analytics.api import queries as web_data


def _xlsx_bytes(headers: list[str], rows: list[list]) -> bytes:
    """Build a minimal valid .xlsx file in memory."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def synthetic_client(tmp_path, monkeypatch):
    """TestClient with FSP_EXPORTS_DIR pointed at a tmp dir."""
    db = tmp_path / "test.db"
    exports = tmp_path / "FSP Exports"
    exports.mkdir()
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", exports)
    web_data.build_db(db, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app()), exports


def test_upload_rejects_request_with_no_files(synthetic_client):
    client, _ = synthetic_client
    r = client.post("/api/upload/fsp")
    assert r.status_code == 422
    assert "at least one" in r.json()["detail"].lower()


def test_upload_rejects_wrong_extension(synthetic_client):
    client, _ = synthetic_client
    r = client.post(
        "/api/upload/fsp",
        files={"flight_detail": ("bad.csv", b"x,y,z", "text/csv")},
    )
    assert r.status_code == 422
    assert ".xlsx" in r.json()["detail"]


def test_upload_rejects_oversize_file(synthetic_client, monkeypatch):
    """Force the limit down so we don't have to actually upload 50 MB."""
    from provectus_analytics.api.routers import upload as upload_mod
    monkeypatch.setattr(upload_mod, "_MAX_UPLOAD_BYTES", 1024)  # 1 KB
    client, _ = synthetic_client

    payload = b"\x00" * 2048  # 2 KB > 1 KB
    r = client.post(
        "/api/upload/fsp",
        files={"flight_detail": (
            "big.xlsx", payload,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert r.status_code == 413


def test_upload_persists_flight_detail_to_canonical_name(synthetic_client):
    client, exports_dir = synthetic_client
    data = _xlsx_bytes(["Reservation #", "Date"], [["R001", "2024-01-15"]])
    r = client.post(
        "/api/upload/fsp",
        files={"flight_detail": (
            "messy original name.xlsx", data,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["saved"]["flight_detail"]["path"] == "FlightDetail_Report.xlsx"
    assert (exports_dir / "FlightDetail_Report.xlsx").is_file()


def test_upload_can_send_both_files_in_one_request(synthetic_client):
    client, exports_dir = synthetic_client
    flight_data = _xlsx_bytes(
        ["Reservation #", "Date", "Aircraft", "Type", "Status", "Client"],
        [["R001", "2024-01-15", "N512PT Piper PA-28-180",
          "Dual Flight Training", "Completed", "Test Client"]],
    )
    invoice_data = _xlsx_bytes(
        ["Invoice #", "Invoice Date", "Reservation #", "Line Item Name",
         "Line Item Description", "Line Item Type", "Quantity", "Rate",
         "Total Costs", "Total Payment", "Status"],
        [["I001", "2024-01-15", "R001", "CFI Test Instructor",
          "Instruction", "Service", 1.0, 75.0, 75.0, None, "Paid"]],
    )
    r = client.post(
        "/api/upload/fsp",
        files={
            "flight_detail": ("flight.xlsx", flight_data,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "invoice_detail": ("invoice.xlsx", invoice_data,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        },
    )
    assert r.status_code == 200, r.text
    assert (exports_dir / "FlightDetail_Report.xlsx").is_file()
    assert (exports_dir / "Invoice_Report.xlsx").is_file()
    body = r.json()
    assert body["built"]["mode"] == "real"
