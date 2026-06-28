"""Per-rating cohort norms (ROADMAP Phase 6).

Methodology — locked here, change with care:
    - Central measure: median
    - Spread:          P25 and P75
    - Outlier rule:    Tukey fence (1.5× IQR), applied per-metric within rating
    - Min sample:      n < 10 → low_sample_flag = True (norm published but flagged)
    - Cohort:          all alumni with a checkride milestone for the rating

Transfer-in / partial-completion handling is deferred to a boss decision
(ROADMAP Open Questions). Today, every alum with a checkride is included.
"""
from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass, asdict

LOW_SAMPLE_THRESHOLD = 10


@dataclass
class RatingNorm:
    rating: str
    n_raw: int
    n_after_outlier: int
    p25_hours: float
    median_hours: float
    p75_hours: float
    p25_cost: float
    median_cost: float
    p75_cost: float
    p25_days: int
    median_days: int
    p75_days: int
    median_flights: int
    low_sample_flag: bool


def _tukey_filter(vals: list[float]) -> list[float]:
    """Return vals with points outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR] removed."""
    if len(vals) < 4:
        return list(vals)
    s = sorted(vals)
    q1, _, q3 = statistics.quantiles(s, n=4)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return [v for v in vals if lo <= v <= hi]


def _quartiles(vals: list[float]) -> tuple[float, float, float]:
    """Return (P25, median, P75). For n<4, falls back to (min, median, max)."""
    s = sorted(vals)
    med = statistics.median(s)
    if len(s) >= 4:
        q1, _, q3 = statistics.quantiles(s, n=4)
        return q1, med, q3
    return min(s), med, max(s)


def compute_rating_norms(
    conn: sqlite3.Connection, consented_only: bool = False
) -> list[RatingNorm]:
    """Return one RatingNorm per rating that has at least one checkride milestone.

    When ``consented_only`` is True, restrict to students who opted in to the
    public/marketing use of their data (``students.consent_marketing = 1``).
    Used for the public transparency view. The flag only toggles fixed SQL —
    no user input is interpolated.
    """
    consent_join = "JOIN students s USING (student_id)" if consented_only else ""
    consent_where = "AND s.consent_marketing = 1" if consented_only else ""
    rows = list(conn.execute(
        f"""SELECT r.code AS rating,
                  m.cumulative_flights AS flights,
                  m.cumulative_hours   AS hours,
                  m.cumulative_cost    AS cost,
                  m.days_from_rating_start AS days
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN ratings     r USING (rating_id)
           {consent_join}
           WHERE m.milestone_name = 'checkride' {consent_where}"""
    ))

    by_rating: dict[str, dict[str, list]] = {}
    for r in rows:
        d = by_rating.setdefault(r["rating"], {"hours": [], "cost": [], "days": [], "flights": []})
        d["hours"].append(r["hours"])
        d["cost"].append(r["cost"])
        d["days"].append(r["days"])
        d["flights"].append(r["flights"])

    results: list[RatingNorm] = []
    for rating in ["PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"]:
        if rating not in by_rating:
            continue
        d = by_rating[rating]
        n_raw = len(d["hours"])

        # Apply Tukey fence per-metric; use intersection-based n_after via hours as the anchor
        hours_clean = _tukey_filter(d["hours"])
        cost_clean = _tukey_filter(d["cost"])
        days_clean = _tukey_filter(d["days"])

        p25h, medh, p75h = _quartiles(hours_clean)
        p25c, medc, p75c = _quartiles(cost_clean)
        p25d, medd, p75d = _quartiles(days_clean)
        medf = statistics.median(d["flights"])

        results.append(RatingNorm(
            rating=rating,
            n_raw=n_raw,
            n_after_outlier=len(hours_clean),
            p25_hours=round(p25h, 1),
            median_hours=round(medh, 1),
            p75_hours=round(p75h, 1),
            p25_cost=round(p25c, 2),
            median_cost=round(medc, 2),
            p75_cost=round(p75c, 2),
            p25_days=int(p25d),
            median_days=int(medd),
            p75_days=int(p75d),
            median_flights=int(medf),
            low_sample_flag=n_raw < LOW_SAMPLE_THRESHOLD,
        ))
    return results


def norms_to_dicts(norms: list[RatingNorm]) -> list[dict]:
    return [asdict(n) for n in norms]
