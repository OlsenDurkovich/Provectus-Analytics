# Instructor Detail — Flesh Out + Fix vs-Cohort Comparison

**Date:** 2026-05-26
**Branch:** `feat/instructor-detail-flesh-out`
**Status:** Approved, ready for implementation plan
**Depends on:** PR #1 (Student Detail cohort strips) — merged into main

## Problem

The Instructor Detail page has two issues:

1. **Data integrity bug.** The "Efficiency vs cohort" table shows columns labeled `Med hrs / Med cost / Med days`. These values are actually the instructor's own students' `AVG()` (from `src/provectus_analytics/api/adapters.py:676-692`), not cohort medians. There is no actual comparison to the cohort — the table's name is wrong and the data needed for the comparison isn't even fetched.
2. **Thin page below the KPIs.** Only 2 `BigKpi` cards at the top, then the broken table, then a student roster. No visualization of where this instructor's students fall in each rating's cohort distribution. The page tells you who they teach but not how efficient they are relative to peers.

## Scope

Fix the data-integrity bug and add visual comparison to cohort using the primitives just shipped in PR #1.

**In scope:**

- Rename the misnamed backend fields (`medianHrs/medianCost/medianDays` → `avgHrs/avgCost/avgDays`) because they were always averages.
- Add `studentIds: list[str]` to `InstructorPerRating` so the frontend can identify which cohort members this instructor taught.
- Replace the existing "Efficiency vs cohort" table with per-rating blocks. Each block contains a numeric comparison row (instructor avg vs cohort median, with delta) and 3 mini scatter strips (hours / cost / days) showing the cohort distribution with the instructor's students multi-highlighted.
- Extend `ScatterStrip` to accept `highlightNames: string[]` instead of `highlightName: string | null`. Migrate Rating Detail and Student Detail call sites to pass single-element arrays.

**Out of scope:**

- In-progress students (no checkride yet) are not shown in strips. The roster table below already covers them.
- Adding new top-line `BigKpi` cards. The page's "thin top" complaint is addressed by replacing the table with richer per-rating content below; more KPIs can be a separate branch if still needed.
- Phase 10 public transparency view.

## User-visible behavior

Below the existing 2 `BigKpi`s and above the "Student roster" section, render one block per rating the instructor has students who completed:

- Block header: rating chip (e.g. `PPL`) + rating name (e.g. `Private Pilot`) + `n=X` (count of completed students this instructor taught for this rating).
- Numeric row (3 `MiniKpi` cards): "Avg hrs", "Avg cost", "Avg days" — each showing the instructor's value, a delta vs cohort median, and the cohort median as the sub-text. Same layout/styling as Student Detail's `RatingBlock` numeric row.
- 3 mini scatter strips below the MiniKpi grid (hours / cost / days). Each strip shows the full cohort's P25–P75 band, dashed median line, all cohort dots, and **all of this instructor's students multi-highlighted** in accent color. The viewer can scan whether the cluster sits low (efficient instructor) or high (slow) within the cohort.
- The 4 KPI cards at the top and the student roster table below are unchanged.

Edge cases:

- Cohort still loading → 3 skeleton bars (~60px each) where the strips will go.
- Cohort fetch errored or returned empty → strips silently hidden; numeric MiniKpis still render.
- Instructor has no completed students for a rating → that rating simply doesn't appear in `perRating` (already true today).
- `studentIds` empty for some reason (data inconsistency) → strips render with no highlighted dots; numeric MiniKpis still meaningful.

## Architecture

### Backend changes

`src/provectus_analytics/api/schemas.py` — replace the `InstructorPerRating` model:

```python
class InstructorPerRating(BaseModel):
    rating: str
    n: int
    avgHrs: float
    avgCost: float
    avgDays: float
    studentIds: list[str]
```

`src/provectus_analytics/api/adapters.py:676-738` — update the SQL and the construction:

```python
per_rating_rows = conn.execute(
    """SELECT r.code AS rating, COUNT(*) AS n,
              AVG(m.cumulative_hours) AS avg_hours,
              AVG(m.cumulative_cost) AS avg_cost,
              AVG(m.days_from_rating_start) AS avg_days,
              GROUP_CONCAT(DISTINCT CAST(e.student_id AS TEXT)) AS student_ids
       FROM milestones m
       JOIN enrollments e USING (enrollment_id)
       JOIN ratings r USING (rating_id)
       WHERE m.milestone_name = 'checkride'
         AND e.enrollment_id IN (
             SELECT DISTINCT f.enrollment_id FROM flights f
             WHERE f.instructor = ? AND f.enrollment_id IS NOT NULL
         )
       GROUP BY r.code, r.sort_order
       ORDER BY r.sort_order""",
    (instructor_id,),
).fetchall()

per_rating = [
    schemas.InstructorPerRating(
        rating=row["rating"],
        n=int(row["n"] or 0),
        avgHrs=float(row["avg_hours"] or 0),
        avgCost=float(row["avg_cost"] or 0),
        avgDays=float(row["avg_days"] or 0),
        studentIds=(row["student_ids"].split(",") if row["student_ids"] else []),
    )
    for row in per_rating_rows
]
```

### Frontend type change

`frontend/src/data/types.ts` — update `InstructorPerRating`:

```ts
export interface InstructorPerRating {
  rating: RatingCode;
  n: number;
  avgHrs: number;
  avgCost: number;
  avgDays: number;
  studentIds: string[];
}
```

### ScatterStrip prop migration

`frontend/src/components/charts/ScatterStrip.tsx`:

- Replace prop `highlightName: string | null` with `highlightNames: string[]`.
- Inside the component, `isHighlighted = highlightNames.includes(p.student)`.
- The `highlightInProgress` interaction stays the same — it modifies whichever dots are in `highlightNames`.

Migration of existing call sites:

- `frontend/src/routes/RatingDetail.tsx` (line ~227): `highlightName={overlayName}` → `highlightNames={overlayName ? [overlayName] : []}`. There are three such call sites (one per strip).
- `frontend/src/routes/Student.tsx` (`RatingBlockStrips`, 3 strips): `highlightName={studentName}` → `highlightNames={[studentName]}`.
- `frontend/src/components/charts/ScatterStrip.test.tsx`: tests using `highlightName="Alice"` → `highlightNames={["Alice"]}` (or `[]` for the null case).
- `frontend/src/routes/RatingDetail.test.tsx` and `frontend/src/routes/Student.test.tsx`: no direct uses; integration test fixtures are unaffected.

### Page layout (`frontend/src/routes/Instructor.tsx`)

`InstructorBody` extends to fetch cohorts and render per-rating blocks. Replace the "Efficiency vs cohort" table (lines 81-123) with:

```tsx
function InstructorBody({ detail }: { detail: InstructorDetail }) {
  const totalHours = detail.students.reduce((s, c) => s + c.hoursToDate, 0);
  const studentsAtCheckride = detail.students.filter((s) => s.status === 'Completed').length;
  const cohortCodes = detail.perRating.map((p) => p.rating);
  const cohorts = useRatingCohorts(cohortCodes);

  return (
    <>
      <div className="kpi-grid kpi-grid-2">
        <BigKpi label="Ratings taught" value={String(detail.perRating.length)} sub={...} />
        <BigKpi label="Students at checkride" value={String(studentsAtCheckride)} sub={...} />
      </div>

      <div className="section-head">
        <h2 className="section-title">Per rating vs cohort</h2>
      </div>
      {detail.perRating.map((r) => (
        <InstructorRatingBlock
          key={r.rating}
          r={r}
          cohortQuery={cohorts.get(r.rating)}
        />
      ))}

      <div className="section-head">
        <h2 className="section-title">Student roster</h2>
      </div>
      <RosterTable students={detail.students} />
    </>
  );
}
```

`InstructorRatingBlock` is a new function in `Instructor.tsx`, sibling to `InstructorBody`. It renders the block head, the 3 numeric MiniKpis with delta vs cohort median, and the 3 mini strips. Decision tree (mirrors Student Detail's `RatingBlockStrips`):

```
InstructorRatingBlock
  ├── Always render block head (rating chip, name, n)
  ├── Always render 3 MiniKpi cards (instructor avg, delta vs cohort median, cohort median sub-text)
  └── Strips slot:
      ├── if cohortQuery.isLoading → 3 skeleton bars (~60px each)
      ├── if cohortQuery.isError || cohortQuery.data is empty → render nothing
      └── else → 3 mini ScatterStrip charts with multi-highlight on r.studentIds-mapped names
```

For the highlight: `ScatterStrip` matches highlights by name (`p.student`), but the spec returns `studentIds`. Map ids → names by intersecting `r.studentIds` with the cohort data: `highlightNames = cohort.filter(m => r.studentIds.includes(m.studentId)).map(m => m.name)`.

The cohort median (for the numeric delta) is computed client-side from `cohort.data` so the comparison reflects the same data the strips visualize. A 2-line helper `median(cohort.map(m => m.hours))` etc.

### Data flow summary

```
Instructor.tsx
  └── useInstructor(id)              → InstructorDetail { perRating: InstructorPerRating[] (with studentIds), students }
  └── useRatingCohorts(codes)        → Map<RatingCode, UseQueryResult<RatingCohortMember[]>>

InstructorBody
  ├── render 2 BigKpis (unchanged)
  ├── for each r in detail.perRating:
  │     └── <InstructorRatingBlock r={r} cohortQuery={cohorts.get(r.rating)} />
  └── render student roster table (unchanged)

InstructorRatingBlock
  ├── compute cohort medians client-side from cohortQuery.data
  ├── compute highlightNames from r.studentIds intersected with cohort
  ├── render block head + 3 MiniKpi delta cards
  └── render 3 mini strips (loading / error / data states)
```

### File touch list

- `src/provectus_analytics/api/schemas.py` — rename + add field on `InstructorPerRating`
- `src/provectus_analytics/api/adapters.py` — update SQL + construction in `instructor_detail`
- `tests/test_api_instructors.py` (or wherever instructor_detail is tested) — update fixtures
- `frontend/src/data/types.ts` — rename + add field on `InstructorPerRating` interface
- `frontend/src/components/charts/ScatterStrip.tsx` — `highlightName` → `highlightNames: string[]`
- `frontend/src/components/charts/ScatterStrip.test.tsx` — update existing tests to the new prop shape; add a new test for multi-highlight
- `frontend/src/routes/RatingDetail.tsx` — migrate 3 call sites
- `frontend/src/routes/Student.tsx` — migrate 3 call sites in `RatingBlockStrips`
- `frontend/src/routes/Instructor.tsx` — replace table with per-rating blocks, add `InstructorRatingBlock`
- `frontend/src/routes/Instructor.test.tsx` — extend mock for cohort endpoints and `studentIds`; add new assertions
- `frontend/src/styles/styles.css` — may add a small rule for an "instructor rating block" container (or reuse Student Detail's `.rating-block` styles)

## Testing

### Backend

- `instructor_detail` test: assert `avgHrs`/`avgCost`/`avgDays` fields exist (not `medianHrs`...)
- `instructor_detail` test: assert `studentIds` contains the correct student ids for a known instructor and rating
- Existing instructor list test unchanged (the list endpoint shape is unaffected)

### Frontend unit — `ScatterStrip`

- Multi-name highlight: passing `highlightNames={['Alice', 'Bob']}` highlights both dots in accent color
- Empty array: no highlighted dots
- `highlightInProgress` still works when multiple names are highlighted (all in-progress dots get warn color — though in practice this branch never sets `highlightInProgress` for Instructor Detail)

### Frontend integration — `Instructor`

- Renders per-rating blocks instead of the old table
- Each block shows the rating chip, name, n, and 3 MiniKpis with delta computed against client-side cohort median
- 3 SVGs render per block when cohort loads successfully
- When `studentIds` matches 2 cohort members, exactly 2 dots are drawn in accent color per strip
- Loading state shows skeletons
- Error state hides strips but keeps MiniKpis

### Regression

- Rating Detail tests (7) pass with migrated `highlightNames` array prop
- Student Detail tests (7) pass with migrated `highlightNames` array prop
- ScatterStrip unit tests (8) updated and pass
- Full frontend suite green
- Backend tests green; especially the previously-mislabeled instructor field doesn't break the API

## Open questions

None. All decisions resolved during brainstorming:

- Scope: fix the broken vs-cohort comparison + add scatter strips (option 2 of 3).
- Visualization: multi-dot highlight of the instructor's completed students (option 1 of 3).
- Layout: replace the table with per-rating blocks (option 1 of 3).
- In-progress students: skipped — only completed students highlighted (option 1 of 3).
- Backend field naming: rename `median*` → `avg*` because they were always averages. New `studentIds` field added.
- Highlight key: by name (matching `ScatterStrip`'s existing point shape), computed by mapping `r.studentIds` through the cohort.

## Deviation note

The spec calls for **multi-name highlight** in `ScatterStrip`. This is a breaking API change for `ScatterStrip` (`highlightName` → `highlightNames: string[]`). All three current call sites (Rating Detail, Student Detail, this new Instructor Detail) are migrated atomically in this branch. Backward compat with the single-name prop is not preserved — the codebase is small enough that one rename is cleaner than maintaining two props.
