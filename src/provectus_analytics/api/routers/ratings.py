from fastapi import APIRouter, Query

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["ratings"])


@router.get("/ratings", response_model=list[schemas.RatingBarPoint])
def get_rating_bars(
    metric: schemas.MetricKey = Query("hours"),
    range: schemas.RangeKey = Query("12mo"),
):
    return adapters.rating_bars(metric, range)


@router.get("/ratings/completed", response_model=list[schemas.RatingsCompletedRow])
def get_ratings_completed(range: schemas.RangeKey = Query("12mo")):
    return adapters.ratings_completed(range)


@router.get("/heatmap", response_model=schemas.Heatmap)
def get_heatmap(range: schemas.RangeKey = Query("12mo")):
    return adapters.heatmap(range)


@router.get("/ratings/{code}", response_model=schemas.Rating)
def get_rating(code: schemas.RatingCode, range: schemas.RangeKey = Query("12mo")):  # noqa: ARG001
    return adapters.rating_detail(code)
