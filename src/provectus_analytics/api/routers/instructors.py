from fastapi import APIRouter, HTTPException

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["instructors"])


@router.get("/instructors", response_model=list[schemas.InstructorSummary])
def list_instructors():
    return adapters.instructors_list()


@router.get("/instructors/{instructor_id}", response_model=schemas.InstructorDetail)
def get_instructor(instructor_id: str):
    try:
        return adapters.instructor_detail(instructor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
