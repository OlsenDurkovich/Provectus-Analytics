from fastapi import APIRouter, Depends, HTTPException, Query

from .. import adapters, schemas
from ...auth.deps import require_page

router = APIRouter(prefix="/api", tags=["students"])

# The clients list also powers the Overview client table; the per-student
# drill-down is the Student page only.
_clients = [Depends(require_page("overview", "students"))]
_student = [Depends(require_page("students"))]


@router.get("/students", response_model=list[schemas.ClientRow], dependencies=_clients)
def get_clients(
    range: schemas.RangeKey = Query("12mo"),
    rating: schemas.RatingCode | None = Query(None),
):
    return adapters.clients(range, rating)


@router.get(
    "/students/{student_id}", response_model=schemas.StudentDetail, dependencies=_student
)
def get_student(student_id: str):
    try:
        return adapters.student_detail(student_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
