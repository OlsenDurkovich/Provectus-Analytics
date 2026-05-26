from datetime import date

from provectus_analytics.api import adapters


def test_range_cutoff_30d_returns_30_days_ago():
    cutoff = adapters.range_cutoff("30d", today=date(2026, 1, 31))
    assert cutoff == date(2026, 1, 1)


def test_range_cutoff_12mo():
    cutoff = adapters.range_cutoff("12mo", today=date(2026, 1, 31))
    assert cutoff == date(2025, 1, 31)


def test_range_cutoff_all_returns_none():
    assert adapters.range_cutoff("all") is None


def test_range_cutoff_ytd_returns_jan_1():
    assert adapters.range_cutoff("ytd", today=date(2026, 5, 25)) == date(2026, 1, 1)


def test_range_cutoff_unknown_raises():
    import pytest

    with pytest.raises(ValueError):
        adapters.range_cutoff("foo")  # type: ignore[arg-type]
