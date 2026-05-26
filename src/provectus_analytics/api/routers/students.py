from fastapi import APIRouter, HTTPException, Query

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["students"])


@router.get("/students", response_model=list[schemas.ClientRow])
def get_clients(
    range: schemas.RangeKey = Query("12mo"),
    rating: schemas.RatingCode | None = Query(None),
):
    return adapters.clients(range, rating)


@router.get("/students/{student_id}", response_model=schemas.StudentDetail)
def get_student(student_id: str):
    try:
        return adapters.student_detail(student_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
