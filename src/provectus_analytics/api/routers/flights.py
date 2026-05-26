from fastapi import APIRouter, Query

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
