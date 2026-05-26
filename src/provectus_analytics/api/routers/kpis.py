from fastapi import APIRouter, Query

from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["kpis"])


@router.get("/kpis", response_model=list[schemas.Kpi])
def get_kpis(range: schemas.RangeKey = Query("12mo")) -> list[schemas.Kpi]:
    return adapters.kpis(range)
