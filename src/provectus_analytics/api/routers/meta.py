from fastapi import APIRouter

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta", response_model=schemas.Meta)
def get_meta() -> schemas.Meta:
    return adapters.meta()
