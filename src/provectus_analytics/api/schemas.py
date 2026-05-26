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
    medianHrs: float
    medianCost: float
    medianDays: float


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
