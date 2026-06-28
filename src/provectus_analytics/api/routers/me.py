"""Self-service endpoints for the logged-in user.

`/api/me/training` is the ONLY data endpoint a `student`-role account can
reach. It serves the StudentDetail for the student record linked to that
account and nothing else — the linked id comes from the authenticated user,
never from request input, so a student cannot read another person's record.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import adapters, schemas
from ...auth import users
from ...auth.deps import current_student

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
