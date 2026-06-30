from fastapi import APIRouter, Query

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=schemas.Insights)
def get_insights(
    threshold: float = Query(0.25, ge=0.0, le=2.0),
):
    """At-risk students, instructor↔rating strengths, and efficiency ranking.

    `threshold` is the fraction over the cohort median at which a student is
    flagged at-risk (0.25 == 25% over).
    """
    return adapters.insights(threshold)
