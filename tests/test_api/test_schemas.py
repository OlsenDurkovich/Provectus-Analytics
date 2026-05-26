import pydantic
import pytest

from provectus_analytics.api import schemas


def test_kpi_roundtrip():
    kpi = schemas.Kpi(
        key="ratings_completed",
        label="Ratings completed",
        value="42",
        sub="last 12 months",
        delta=0.12,
        positive=True,
        spark=[1, 2, 3],
        color="#6E56F8",
    )
    assert kpi.model_dump()["positive"] is True


def test_client_row_status_enum():
    row = schemas.ClientRow(
        id="c1",
        name="Alex Doe",
        rating="PPL",
        progressPct=0.5,
        hoursToDate=42.3,
        daysEnrolled=120,
        status="Active",
    )
    assert row.rating == "PPL"


def test_flight_update_rejects_invalid_field():
    with pytest.raises(pydantic.ValidationError):
        schemas.FlightUpdate(field="client_name", value="x")  # type: ignore[arg-type]


def test_flight_row_billing_enum_rejects_invalid():
    with pytest.raises(pydantic.ValidationError):
        schemas.FlightRow(
            id="f1",
            date="2026-01-01",
            client="A",
            instructor="B",
            type="Dual",
            billing="INVALID",  # type: ignore[arg-type]
            acClass="SE_BASIC",
            ground="Flight (0)",
            hours=1,
            cost=100,
        )
