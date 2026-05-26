# Student Detail — Cohort Distribution Strips

**Date:** 2026-05-26
**Branch:** `feat/student-detail-cohort-strips`
**Status:** Approved, ready for implementation plan

## Problem

Student Detail's per-rating blocks show the student's hours/cost/days as numeric `MiniKpi` cards with a delta vs cohort median, but offer no visual sense of where the student sits in the cohort *distribution*. The Rating Detail page just shipped scatter-strip charts (P25–P75 band, median line, all cohort dots) that solve this for the rating-level view. Student Detail should reuse that vocabulary at the per-rating block level.

## Scope

Add mini scatter-strip charts inside each per-rating block on Student Detail, showing where the student sits relative to the cohort distribution for **hours**, **cost**, and **days**.

**Out of scope:**

- Instructor Detail (separate, larger lift — tracked as next branch)
- Backend changes (reuses existing `GET /api/ratings/{code}/cohort`)
- Changes to Rating Detail (must remain visually identical)

## User-visible behavior

For each rating block on Student Detail:

- Below the existing 4-MiniKpi grid, a row of 3 mini scatter strips renders, one each for hours / cost / days, aligned roughly under the matching MiniKpi columns.
- Each mini strip shows: P25–P75 band, dashed median line, all cohort dots, and the viewed student's dot highlighted.
- If the student has **completed** the rating, their dot appears as part of the cohort.
- If the student is **in progress** (no checkride milestone yet), their dot is injected as an extra point with a distinct stroke color and a tooltip indicating "in progress — [N] hrs to date".
- If cohort sample is low (`r.lowSample` from API) or empty, strips are hidden and a small inline note reads "Distribution hidden — low sample".
- While cohort data is loading, a skeleton bar (~60px) reserves the strip slot.
- If cohort fetch errors, strips are silently hidden for that rating; numeric MiniKpis remain.

## Architecture

### File touch list

- `frontend/src/components/charts/ScatterStrip.tsx` — add `size?: "full" | "mini"` prop, default `"full"`. Mini variant adjusts height, dot radius, padding, axis ticks, hides Y-label. No breaking changes.
- `frontend/src/data/queries.ts` — add `useRatingCohorts(codes: RatingCode[])` that fans out one query per rating via React Query's `useQueries`. Returns a `Map<RatingCode, UseQueryResult<RatingCohortMember[]>>` so each entry exposes `isLoading` / `isError` / `data` independently. Each rating's cohort is cached individually so navigating to Rating Detail reuses the cache.
- `frontend/src/routes/Student.tsx` — `RatingBlock` accepts cohort data + the viewed student's point, renders 3 mini strips below the MiniKpi grid. Parent `StudentBody` calls `useRatingCohorts` once with the list of the student's rating codes and passes each cohort down.
- `frontend/src/components/charts/ScatterStrip.test.tsx` — extend with mini variant rendering tests.
- `frontend/src/routes/Student.test.tsx` — add tests for cohort-driven strips, in-progress injection, low-sample fallback.

### Component changes — ScatterStrip mini variant

| Aspect | `size="full"` (current) | `size="mini"` (new) |
|---|---|---|
| Container height | ~200px | ~60px |
| Dot radius | 5px | 3px |
| Card padding | inherits card wrapper | none (inline) |
| Axis ticks | 5 (min, p25, median, p75, max) | 2 (min, max) |
| Y-axis label | shown | hidden |
| Tooltips | yes | yes (smaller font) |
| Highlight stroke | accent | accent |
| In-progress highlight stroke | n/a (Rating Detail uses completed cohort) | `var(--warn)` or similar |

`ScatterStrip` API additions:

```ts
interface ScatterStripProps {
  // existing
  points: Array<{ student: string; value: number }>;
  band: { low: number; high: number };
  median: number;
  highlightName: string | null;
  yLabel: string;
  fmt: (v: number) => string;
  // new
  size?: 'full' | 'mini';            // default 'full'
  highlightInProgress?: boolean;      // if true, highlighted dot uses warn-color stroke + "in progress" tooltip suffix
}
```

### Data flow

```
Student.tsx
  └── useStudent(id)               → StudentDetail { perRating: StudentPerRating[] }
  └── useRatingCohorts(codes)      → useQueries fan-out, returns Map<RatingCode, UseQueryResult<RatingCohortMember[]>>
       (codes = perRating.map(r => r.rating))

StudentBody
  └── for each r in perRating:
       └── <RatingBlock
              r={r}
              studentId={detail.id}
              studentName={detail.name}
              cohortQuery={cohorts.get(r.rating)}
            />

RatingBlock (decision tree)
  ├── if r.lowSample → render block with strips slot replaced by "Distribution hidden — low sample"
  ├── elif cohortQuery.isLoading → render skeleton bar in strips slot
  ├── elif cohortQuery.isError → render block without strips (numeric MiniKpis still show)
  ├── elif cohortQuery.data.length === 0 → same as low-sample fallback
  └── else:
       ├── inCohort = cohort.some(m => m.studentId === studentId)
       ├── if !inCohort and r.hours != null:
       │      cohort = [...cohort, { studentId, name: studentName, hours: r.hours, cost: r.cost ?? 0, days: r.days ?? 0 }]
       │      highlightInProgress = true
       │   else:
       │      highlightInProgress = false
       └── render 3 <ScatterStrip size="mini" highlightName={studentName} highlightInProgress={...} />
```

### In-progress dot rendering

Inside `ScatterStrip`, when `highlightInProgress === true`:

- The dot matched by `highlightName` is rendered with a different stroke (e.g. `var(--warn)` ~ `#f6b73c`) instead of the default accent color.
- Tooltip text for that dot becomes `"{name} (in progress) — {fmt(value)}"`.
- All other dots render normally.

### Edge cases

| Case | Behavior |
|---|---|
| `cohortQuery.isLoading` | Skeleton bar (~60px height) in strips slot |
| `cohortQuery.isError` | Hide strips, numeric MiniKpis remain |
| `r.lowSample === true` | Hide strips, inline note "Distribution hidden — low sample" |
| Cohort empty (`length === 0`) | Same as low-sample |
| Student in cohort | Highlight by matching `studentId`; no injection |
| Student not in cohort + has numeric data | Inject synthetic point with `inProgress` flag |
| Student not in cohort + no numeric data (e.g. `r.hours == null`) | Render cohort strips with no highlight |

## Testing

### Unit — `ScatterStrip` mini variant

- Mini renders at smaller height
- Mini hides Y-axis label
- Mini keeps tooltips on hover
- `highlightInProgress` swaps the highlighted dot's stroke color
- `highlightInProgress` modifies tooltip text

### Hook — `useRatingCohorts`

- Calling with `['PPL', 'IFR']` returns 2 query results
- Each rating cached independently (verified via React Query devtools or direct cache inspection in test)
- Refetches when input codes change
- Reuses cache when same code is requested again (e.g. after navigating to Rating Detail and back)

### Integration — `Student`

- Renders strips for a rating where student is in cohort (no in-progress styling)
- Renders strips with in-progress styling for an active rating (student not in cohort but has hours)
- Renders fallback note for `lowSample` rating
- Renders skeleton during cohort load
- Renders without strips on cohort error
- Existing Student page tests stay green

### Regression

- Rating Detail tests stay green (ScatterStrip default `size="full"` preserves behavior)

## Open questions

None. All design decisions resolved during brainstorming:

- Placement: mini strips inside each RatingBlock (option 1)
- Strip detail: full distribution miniaturized — band + median + all cohort dots + highlight (option 1)
- Backend: reuse existing `/api/ratings/{code}/cohort`, parallel fetches via `useQueries` (option 1)
- In-progress: inject synthetic point with visual marker (option 1)
