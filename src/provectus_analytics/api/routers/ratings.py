from fastapi import APIRouter, Depends, Query

from .. import adapters, schemas
from ...auth.deps import require_page

router = APIRouter(prefix="/api", tags=["ratings"])

# Per-endpoint page gating: bars/completed/heatmap power the Overview page;
# the per-rating detail + cohort power the Rating-detail page.
_overview = [Depends(require_page("overview", "ratings"))]
_overview_only = [Depends(require_page("overview"))]
_rating_detail = [Depends(require_page("ratings"))]


@router.get("/ratings", response_model=list[schemas.RatingBarPoint], dependencies=_overview)
def get_rating_bars(
    metric: schemas.MetricKey = Query("hours"),
    range: schemas.RangeKey = Query("12mo"),
):
    return adapters.rating_bars(metric, range)


@router.get(
    "/ratings/completed",
    response_model=list[schemas.RatingsCompletedRow],
    dependencies=_overview_only,
)
def get_ratings_completed(range: schemas.RangeKey = Query("12mo")):
    return adapters.ratings_completed(range)


@router.get("/heatmap", response_model=schemas.Heatmap, dependencies=_overview_only)
def get_heatmap(range: schemas.RangeKey = Query("12mo")):
    return adapters.heatmap(range)


@router.get("/ratings/{code}", response_model=schemas.Rating, dependencies=_rating_detail)
def get_rating(code: schemas.RatingCode, range: schemas.RangeKey = Query("12mo")):  # noqa: ARG001
    return adapters.rating_detail(code)


@router.get(
    "/ratings/{code}/cohort",
    response_model=list[schemas.RatingCohortMember],
    dependencies=_rating_detail,
)
def get_rating_cohort(code: schemas.RatingCode):
    return adapters.rating_cohort(code)
