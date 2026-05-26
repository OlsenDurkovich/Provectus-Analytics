# Rating Detail page — flesh out

**Date:** 2026-05-26

## Goal

The Rating Detail page currently shows 4 KPI cards and nothing else, despite its subtitle promising "cohort distribution with P25-P75 band — compare an individual to the band." This spec describes the additions to deliver on that promise.

## What changes

### 1. Backend — new cohort endpoint

`GET /api/ratings/{code}/cohort` → `list[RatingCohortMember]`

Query: all checkride milestones for the given rating, joined to students. Returns one row per alum:

```python
class RatingCohortMember(BaseModel):
    studentId: str
    name: str
    hours: float
    cost: float
    days: int
```

Source query (mirrors `norms.py` but adds student identity):
```sql
SELECT e.student_id, s.fsp_display_name,
       m.cumulative_hours, m.cumulative_cost, m.days_from_rating_start
FROM milestones m
JOIN enrollments e USING (enrollment_id)
JOIN ratings r USING (rating_id)
JOIN students s USING (student_id)
WHERE m.milestone_name = 'checkride' AND r.code = ?
ORDER BY m.cumulative_hours
```

Router: added to `routers/ratings.py` as `GET /api/ratings/{code}/cohort`.

### 2. Frontend — new type + hook

`types.ts` gains:
```ts
export interface RatingCohortMember {
  studentId: string;
  name: string;
  hours: number;
  cost: number;
  days: number;
}
```

`queries.ts` gains:
```ts
export const useRatingCohort = (code: RatingCode) => useQuery(...)
```
with query key `['ratingCohort', code]`.

`client.ts` gains `getRatingCohort(code)` calling `/api/ratings/{code}/cohort`.

### 3. `BigKpi` — overlay prop

New optional prop: `overlay?: { label: string; value: string }`. When present renders a right-side inset inside the card: student name in small caps (accent color) above the student value in large accent text. Works alongside the existing `deltaNode` prop.

### 4. New component — `ScatterStrip`

File: `frontend/src/components/charts/ScatterStrip.tsx`

Props:
```ts
interface Props {
  points: { student: string; value: number }[];
  band: { low: number; high: number };
  median: number;
  highlightName: string | null;
  yLabel: string;
  fmt: (v: number) => string;
  height?: number; // default 280
}
```

Renders an SVG scatter strip chart:
- Y-axis: metric value with 5 grid lines and labels (Geist Mono)
- X-axis: evenly spaced by index, no labels
- Shaded rect: P25-P75 band in accent color at low opacity
- Dashed horizontal line: median
- Gray dots: all cohort members, tooltip on hover showing name + value
- Larger accent dot: the point whose `student === highlightName`
- Uses `ResizeObserver` for responsive width (same pattern as `RatingBars`)

### 5. `RatingDetail.tsx` — overhaul

**Page head:**
- `h1` becomes static `"Rating detail"` (was dynamic rating name)
- Two selectors side by side: Rating (existing) + Overlay Student (new, clearable)
- Overlay Student options populated from cohort data (`useRatingCohort`); selector is disabled and shows placeholder `"No alumni yet"` when cohort is empty

**KPI grid:**
- Alumni (n) card: unchanged
- Median hours, Median cost, Median days: each receives `overlay` + `deltaNode` when a student is selected. `deltaNode` uses existing `DeltaText` component with `betterWhenLower`.

**Distribution section:**
- `section-head` with title `"Distribution"` (or `"Distribution vs [name]"` when overlay active, name in accent color) plus a legend row (`band = P25–P75` / `dotted = median`)
- Three stacked full-width cards (flex-column wrapper, not scatter-row grid), each containing a `ScatterStrip`:
  1. `{rating.name} — flight hours` / subtitle `{n} cohort members`
  2. `Total cost` / subtitle `Per-rating spend, USD`
  3. `Calendar days` / subtitle `Days from start to checkride`

**Cohort table:**
- `section-head` with title `"Cohort"`
- `card table-card` with `table-wrap` (max-height 360, scrollable)
- Columns: Student | Hours | Cost | Days
- Sort: overlay student pinned first, then ascending hours
- Overlay row: `row-highlight` CSS class + `overlay-pin` chip next to name
- Hours cell: value + muted delta vs median (e.g. `63.3 -0.9`)

### 6. CSS additions (`styles.css`)

- `.legend-swatch.band` — small rect swatch in accent at low opacity
- `.legend-swatch.med` — short dashed line swatch
- `.overlay-pin` — small pill chip (accent border, small text, icon)
- `.row-highlight` — table row with accent left border + subtle background tint

## Out of scope

- Overlay selector does not include active/current students (only completed alumni in the cohort)
- No drill-through from cohort table rows (clicking a name does not navigate; that's the Student page's job)
- No time-series trend charts (backend doesn't have per-month cohort data at this granularity)
