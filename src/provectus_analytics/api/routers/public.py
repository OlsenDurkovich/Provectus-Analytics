"""Public, unauthenticated transparency endpoint.

Powers the marketing "what does training cost" page. Returns anonymized,
consent-filtered per-rating norms — aggregate stats only (median + P25/P75),
never any student name or PII, and only over alumni who opted in
(``students.consent_marketing = 1``). Mounted WITHOUT an auth dependency.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ... import db as _db, norms
from .. import queries as web_data

router = APIRouter(prefix="/api/public", tags=["public"])


class PublicRatingNorm(BaseModel):
    code: str
    label: str
    n: int           # consented sample size (pre-outlier-filter)
    low_sample: bool # n < 10 — present with a caveat (honesty rule)
    median_cost: float
    p25_cost: float
    p75_cost: float
    median_hours: float
    p25_hours: float
    p75_hours: float
    median_days: int


class PublicTransparency(BaseModel):
    data_mode: str   # 'real' | 'synthetic' — page labels sample data honestly
    ratings: list[PublicRatingNorm]


@router.get("/transparency", response_model=PublicTransparency)
def transparency() -> PublicTransparency:
    conn = _db.connect(web_data.DEFAULT_DB)
    try:
        labels = {
            row["code"]: row["display"]
            for row in conn.execute("SELECT code, display FROM ratings")
        }
        norm_rows = norms.compute_rating_norms(conn, consented_only=True)
    finally:
        conn.close()

    live_count = web_data.is_live_data(web_data.DEFAULT_DB)
    flight, invoice = web_data._has_real_exports()
    is_real = flight is not None and invoice is not None and live_count > 0

    ratings = [
        PublicRatingNorm(
            code=n.rating,
            label=labels.get(n.rating, n.rating),
            n=n.n_raw,
            low_sample=n.low_sample_flag,
            median_cost=n.median_cost,
            p25_cost=n.p25_cost,
            p75_cost=n.p75_cost,
            median_hours=n.median_hours,
            p25_hours=n.p25_hours,
            p75_hours=n.p75_hours,
            median_days=n.median_days,
        )
        for n in norm_rows
    ]
    return PublicTransparency(
        data_mode="real" if is_real else "synthetic",
        ratings=ratings,
    )
