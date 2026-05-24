"""Cohort-norm tests."""
from __future__ import annotations

from provectus_analytics import norms


def test_norms_for_all_seven_ratings(pipeline_db):
    result = norms.compute_rating_norms(pipeline_db)
    codes = {n.rating for n in result}
    assert codes == {"PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"}


def test_low_sample_flag(pipeline_db):
    """CFII (n=9) and MEI (n=8) should be flagged low-sample (threshold = 10)."""
    result = {n.rating: n for n in norms.compute_rating_norms(pipeline_db)}
    assert result["CFII"].low_sample_flag is True
    assert result["MEI"].low_sample_flag is True
    assert result["PPL"].low_sample_flag is False
    assert result["IFR"].low_sample_flag is False


def test_median_within_realistic_range(pipeline_db):
    """Sanity bounds, not exact values — synthetic data hours-per-rating is intentionally noisy."""
    result = {n.rating: n for n in norms.compute_rating_norms(pipeline_db)}
    assert 50 <= result["PPL"].median_hours <= 75
    assert 35 <= result["IFR"].median_hours <= 60
    assert 8 <= result["AMEL"].median_hours <= 18
