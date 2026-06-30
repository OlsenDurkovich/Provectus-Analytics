from fastapi import APIRouter

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["trends"])


@router.get("/trends", response_model=schemas.Trends)
def get_trends():
    """Period-over-period momentum (YoY / 6-over-6 / 3-over-3) for the headline
    metrics, plus all-time totals."""
    return adapters.trends()
