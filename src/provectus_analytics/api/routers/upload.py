"""POST /api/upload/fsp — multipart upload that replaces the ~/Downloads scan.

On Railway (or any hosted environment) there's no user-facing Downloads
folder for `import_exports.import_latest()` to scan. The user uploads the FSP
exports directly through the browser; we validate, write them to the FSP
Exports directory with canonical names, and trigger a rebuild.

Validation:
    - extension must be .xlsx (case-insensitive)
    - content-type must be openxmlformats or octet-stream (some browsers
      send the latter for .xlsx)
    - per-file size cap (50 MB) — FSP exports run ~300 KB so this is generous

Auth: requires any active user. Admin-only restriction can be added later by
swapping the dependency for current_admin_user.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from ...auth.users import User
from ...import_exports import CANONICAL
from .. import queries as web_data

router = APIRouter(prefix="/api/upload", tags=["upload"])

# 50 MB per file — generous; real FSP exports are < 1 MB.
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024

_ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
    "application/x-zip-compressed",  # some browsers report this for .xlsx
}


def _validate_upload(file: UploadFile, label: str) -> None:
    """Validate an uploaded file, raising 422 on failure."""
    name = (file.filename or "").lower()
    if not name.endswith(".xlsx"):
        raise HTTPException(
            status_code=422,
            detail=f"{label}: file must have .xlsx extension (got {file.filename!r})",
        )
    if file.content_type and file.content_type not in _ALLOWED_CONTENT_TYPES:
        # We can't fully trust client content-type but we can sanity-check it.
        raise HTTPException(
            status_code=422,
            detail=f"{label}: unexpected content-type {file.content_type!r}",
        )


def _persist(file: UploadFile, dest: Path) -> int:
    """Stream the uploaded file to disk with a size cap. Returns bytes written."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with dest.open("wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)  # 1 MB
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_UPLOAD_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"file exceeds {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
                )
            out.write(chunk)
    return total


@router.post("/fsp")
def upload_fsp(
    flight_detail: Annotated[UploadFile | None, File()] = None,
    invoice_detail: Annotated[UploadFile | None, File()] = None,
) -> dict:
    """Upload one or both FSP Excel exports, then rebuild the DB.

    Either file is optional, but at least one must be supplied. Files are
    written to the FSP Exports directory using the canonical names that the
    rebuild pipeline already understands.
    """
    if flight_detail is None and invoice_detail is None:
        raise HTTPException(
            status_code=422,
            detail="supply at least one of flight_detail or invoice_detail",
        )

    saved: dict[str, dict[str, int | str]] = {}

    if flight_detail is not None:
        _validate_upload(flight_detail, "flight_detail")
        dest = web_data.FSP_EXPORTS_DIR / CANONICAL["flight_detail"]
        bytes_written = _persist(flight_detail, dest)
        saved["flight_detail"] = {"path": dest.name, "bytes": bytes_written}

    if invoice_detail is not None:
        _validate_upload(invoice_detail, "invoice_detail")
        dest = web_data.FSP_EXPORTS_DIR / CANONICAL["invoice"]
        bytes_written = _persist(invoice_detail, dest)
        saved["invoice_detail"] = {"path": dest.name, "bytes": bytes_written}

    web_data.clear_caches()
    built = web_data.build_db(web_data.DEFAULT_DB)
    return {"saved": saved, "built": built}
