"""Pydantic schemas — the wire contract for /api/*.

Mirrors frontend/src/data/types.ts. Any change here MUST be reflected there.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

RatingCode = Literal["PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"]
RangeKey = Literal["30d", "90d", "6mo", "12mo", "ytd", "all"]
MetricKey = Literal["hours", "cost", "days"]
FlightStatus = Literal["Active", "On checkride", "Completed"]
BillingKind = Literal["Hobbs", "Tach", "Block", "—"]
AcClass = Literal["SE_BASIC", "SE_COMPLEX", "ME_BASIC", "HP_COMPLEX"]
GroundFlag = Literal["Flight (0)", "Ground (1)"]
OverridableField = Literal[
    "is_ground_lesson",
    "billing_category",
    "aircraft_class",
    "reservation_type",
]


class Kpi(BaseModel):
    key: str
    label: str
    value: str
    sub: str
    delta: float
    positive: bool
    spark: list[float]
    color: str


class Rating(BaseModel):
    code: RatingCode
    name: str
    n: int
    medianHrs: float
    p25Hrs: float
    p75Hrs: float
    medianCost: float
    p25Cost: float
    p75Cost: float
    medianDays: float
    p25Days: float
    p75Days: float
    lowSample: bool = False


class RatingCohortMember(BaseModel):
    studentId: str
    name: str
    hours: float
    cost: float
    days: int


class RatingBarPoint(BaseModel):
    code: RatingCode
    name: str
    n: int
    median: float
    p25: float
    p75: float


class RatingsCompletedRow(BaseModel):
    rating: RatingCode
    count: int


class Heatmap(BaseModel):
    rows: list[list[float]]
    buckets: list[str]


class ClientRow(BaseModel):
    id: str
    name: str
    rating: RatingCode
    progressPct: float
    hoursToDate: float
    daysEnrolled: int
    status: FlightStatus
    # Phase 11.5: restore Dash-era columns. costToDate is the invoice total for
    # this student's flights in this rating; instructor is the primary instructor
    # (most hours) for that enrollment; sparkline is 8 trailing monthly hour totals
    # (oldest → newest), used by the tiny inline chart on the Clients table.
    costToDate: float = 0.0
    instructor: str = ""
    sparkline: list[float] = []


class StudentTimelineMilestone(BaseModel):
    name: str
    date: str


class StudentTimelinePoint(BaseModel):
    rating: RatingCode
    start: str
    end: str | None = None
    milestones: list[StudentTimelineMilestone]


class StudentPerRating(BaseModel):
    rating: RatingCode
    name: str
    n: int
    hours: float | None = None
    cost: float | None = None
    days: int | None = None
    medianHrs: float | None = None
    medianCost: float | None = None
    medianDays: float | None = None
    lowSample: bool = False


class StudentDetail(BaseModel):
    id: str
    name: str
    timeline: list[StudentTimelinePoint]
    perRating: list[StudentPerRating]


class InstructorSummary(BaseModel):
    id: str
    name: str
    hours: float
    students: int
    passRate: float


class InstructorPerRating(BaseModel):
    rating: RatingCode
    n: int
    avgHrs: float
    avgCost: float
    avgDays: float
    studentIds: list[str]


class InstructorDetail(BaseModel):
    id: str
    name: str
    students: list[ClientRow]
    perRating: list[InstructorPerRating]


class FlightRow(BaseModel):
    id: str
    date: str
    client: str
    instructor: str
    type: str
    billing: BillingKind
    acClass: AcClass
    ground: GroundFlag
    hours: float
    cost: float


class FlightUpdate(BaseModel):
    field: OverridableField
    value: str | bool | None


class DataState(BaseModel):
    flights: int
    invoices: int
    students: int
    surveys: int
    overrides: int


class Meta(BaseModel):
    mode: Literal["real", "synthetic"]
    liveClientCount: int
    dataState: DataState


# ── Insights tab ──────────────────────────────────────────────────────────────
class AtRiskRow(BaseModel):
    """A student running materially over the cohort median for a rating."""
    studentId: str
    name: str
    rating: RatingCode
    hours: float
    medianHours: float
    pctOverHours: float          # 0.30 == 30% over median hours
    cost: float
    medianCost: float
    pctOverCost: float
    days: int
    worstPct: float              # max(pctOverHours, pctOverCost) — sort key
    status: FlightStatus


class InstructorRatingStat(BaseModel):
    """One instructor's track record for a single rating, vs the OTHER
    instructors' students in that rating (leave-one-out — excludes their own
    students, so an instructor who dominates a rating isn't compared to a
    baseline they themselves define)."""
    instructor: str
    rating: RatingCode
    n: int                       # students they took to checkride in this rating
    avgHours: float
    avgCost: float
    avgDays: float
    vsRestHoursPct: float        # -0.12 == their students averaged 12% fewer hours than everyone else's (better)
    vsRestCostPct: float
    comparable: bool             # False if they taught every student in the rating (no "rest")
    lowSample: bool
    rank: int                    # 1 = best (lowest avg hours) for this rating


class RatingStrength(BaseModel):
    rating: RatingCode
    medianHours: float
    medianCost: float
    instructors: list[InstructorRatingStat]   # best-first


class InstructorEfficiency(BaseModel):
    """One instructor's overall efficiency vs every OTHER instructor's students,
    averaged across the ratings they teach (leave-one-out per rating)."""
    instructor: str
    students: int                # comparable enrollments (ratings with a "rest" to compare to)
    ratings: int                 # distinct comparable ratings taught
    avgHoursVsRestPct: float     # n-weighted mean of per-rating vs-rest hours deviation
    avgCostVsRestPct: float
    score: float                 # blended hours+cost deviation; lower = better
    rank: int
    lowSample: bool


class Insights(BaseModel):
    atRiskThresholdPct: float
    atRisk: list[AtRiskRow]
    strengths: list[RatingStrength]
    efficiency: list[InstructorEfficiency]
