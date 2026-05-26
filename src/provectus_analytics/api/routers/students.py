from fastapi import APIRouter, Query

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["students"])


@router.get("/students", response_model=list[schemas.ClientRow])
def get_clients(
    range: schemas.RangeKey = Query("12mo"),
    rating: schemas.RatingCode | None = Query(None),
):
    return adapters.clients(range, rating)
