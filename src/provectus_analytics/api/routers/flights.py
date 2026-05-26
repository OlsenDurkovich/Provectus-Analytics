from fastapi import APIRouter, HTTPException, Query

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["flights"])


@router.get("/flights", response_model=list[schemas.FlightRow])
def get_flights(
    instructor: str | None = Query(None),
    client: str | None = Query(None),
    ground: str | None = Query(None),
    sort: str | None = Query("-date"),
):
    return adapters.flights(
        {"instructor": instructor, "client": client, "ground": ground, "sort": sort}
    )


@router.patch("/flights/{flight_id}", response_model=schemas.FlightRow)
def update_flight_endpoint(flight_id: str, patch: schemas.FlightUpdate):
    try:
        return adapters.update_flight(flight_id, patch)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
