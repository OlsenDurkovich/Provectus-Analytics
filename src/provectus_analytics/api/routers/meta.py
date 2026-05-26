from fastapi import APIRouter, Query

from ... import import_exports
from .. import adapters, schemas
from ...web import data as web_data

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta", response_model=schemas.Meta)
def get_meta() -> schemas.Meta:
    return adapters.meta()


@router.post("/import-fsp")
def import_fsp():
    """Pull newest FSP exports from Downloads + rebuild DB."""
    results = import_exports.import_latest(exports_dir=web_data.FSP_EXPORTS_DIR)
    web_data.clear_caches()
    built = web_data.build_db(web_data.DEFAULT_DB)
    return {"imported": import_exports.summarize(results), "built": built}


@router.post("/rebuild")
def rebuild(synthetic: bool = Query(False)):
    """Rebuild DB from current FSP Exports/ (or synthetic data)."""
    web_data.clear_caches()
    built = web_data.build_db(web_data.DEFAULT_DB, force_synthetic=synthetic)
    return {"built": built}
