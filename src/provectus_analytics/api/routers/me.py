"""Self-service endpoints for the logged-in user.

These are the only data endpoints the scoped roles can reach:
  - `/api/me/training`  — a `student` account's own training record.
  - `/api/me/students`  — an `instructor` account's own roster (no cost/billing).

In both cases the linked id/name comes from the authenticated user, never from
request input, so a scoped account cannot read anyone else's data.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import adapters, schemas
from ...auth import users
from ...auth.deps import current_instructor, current_student

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/training", response_model=schemas.StudentDetail)
def my_training(user: users.User = Depends(current_student)) -> schemas.StudentDetail:
    try:
        return adapters.student_detail(str(user.student_id))
    except LookupError as exc:
        # The account is linked to an id that no longer exists in the data.
        raise HTTPException(
            status_code=404,
            detail="Your training record could not be found. Ask an admin to relink your account.",
        ) from exc


# --- instructor: my students (cost intentionally omitted) ------------------

class MyStudentRow(BaseModel):
    """A student on the instructor's roster — progress only, no cost/billing."""
    id: str
    name: str
    rating: schemas.RatingCode
    progressPct: float
    hoursToDate: float
    daysEnrolled: int
    status: schemas.FlightStatus


class MyInstructorPerRating(BaseModel):
    """Per-rating aggregate for the instructor — no avg cost."""
    rating: schemas.RatingCode
    n: int
    avgHrs: float
    avgDays: float
    studentIds: list[str]


class MyStudentsView(BaseModel):
    instructor_name: str
    students: list[MyStudentRow]
    perRating: list[MyInstructorPerRating]


@router.get("/students", response_model=MyStudentsView)
def my_students(user: users.User = Depends(current_instructor)) -> MyStudentsView:
    try:
        detail = adapters.instructor_detail(user.instructor_name)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail="No students found for your instructor record. Ask an admin to relink your account.",
        ) from exc
    # Re-shape into the cost-free view: drop costToDate (students) and avgCost
    # (per-rating). Cost never leaves the server for an instructor account.
    return MyStudentsView(
        instructor_name=user.instructor_name,
        students=[
            MyStudentRow(
                id=s.id, name=s.name, rating=s.rating, progressPct=s.progressPct,
                hoursToDate=s.hoursToDate, daysEnrolled=s.daysEnrolled, status=s.status,
            )
            for s in detail.students
        ],
        perRating=[
            MyInstructorPerRating(
                rating=r.rating, n=r.n, avgHrs=r.avgHrs, avgDays=r.avgDays,
                studentIds=r.studentIds,
            )
            for r in detail.perRating
        ],
    )
