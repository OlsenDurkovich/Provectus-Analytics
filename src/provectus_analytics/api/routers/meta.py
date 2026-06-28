from fastapi import APIRouter, Depends, Query

from ... import import_exports
from ...auth.deps import current_admin_user
from .. import adapters, schemas
from .. import queries as web_data

router = APIRouter(prefix="/api", tags=["meta"])

# Rebuilding / importing replaces analytics data for everyone — admin-only.
# GET /meta stays open (the app shell needs it for every authenticated user).
_admin = [Depends(current_admin_user)]


@router.get("/meta", response_model=schemas.Meta)
def get_meta() -> schemas.Meta:
    return adapters.meta()


@router.post("/import-fsp", dependencies=_admin)
def import_fsp():
    """Pull newest FSP exports from Downloads + rebuild DB. Admin-only."""
    results = import_exports.import_latest(exports_dir=web_data.FSP_EXPORTS_DIR)
    web_data.clear_caches()
    built = web_data.build_db(web_data.DEFAULT_DB)
    return {"imported": import_exports.summarize(results), "built": built}


@router.post("/rebuild", dependencies=_admin)
def rebuild(synthetic: bool = Query(False)):
    """Rebuild DB from current FSP Exports/ (or synthetic data). Admin-only."""
    web_data.clear_caches()
    built = web_data.build_db(web_data.DEFAULT_DB, force_synthetic=synthetic)
    return {"built": built}
