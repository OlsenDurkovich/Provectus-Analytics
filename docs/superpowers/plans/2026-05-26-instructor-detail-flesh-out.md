# Instructor Detail — Flesh Out + vs-Cohort Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Instructor Detail's broken "Efficiency vs cohort" table with per-rating blocks that show a correct numeric comparison (instructor avg vs cohort median, with delta) and 3 mini scatter strips per rating with the instructor's completed students multi-highlighted in the cohort distribution.

**Architecture:** Backend renames the mislabeled `median*` fields on `InstructorPerRating` to `avg*` (they were always averages) and adds `studentIds: list[str]`. Frontend extends `ScatterStrip` from `highlightName: string | null` to `highlightNames: string[]` with atomic migration of all current call sites (Rating Detail, Student Detail). `Instructor.tsx` gains a new `InstructorRatingBlock` subcomponent that fetches cohort data via `useRatingCohorts` (the hook shipped in PR #1), computes cohort medians client-side, and renders 3 mini strips with the instructor's students highlighted.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, SQLite (synthetic test DB). React 19, TypeScript, Vite, Vitest, React Testing Library, React Query 5.

**Spec:** `docs/superpowers/specs/2026-05-26-instructor-detail-flesh-out-design.md`

**Branch:** `feat/instructor-detail-flesh-out` (already cut, rebased on main with PR #1 merged)

---

## File map

- Modify: `src/provectus_analytics/api/schemas.py` — rename + add field on `InstructorPerRating`
- Modify: `src/provectus_analytics/api/adapters.py` — update SQL + construction in `instructor_detail`
- Modify: `tests/test_api/test_instructors.py` — assert new field shape and contents
- Modify: `frontend/src/data/types.ts` — update `InstructorPerRating` interface
- Modify: `frontend/src/components/charts/ScatterStrip.tsx` — `highlightName` → `highlightNames: string[]`
- Modify: `frontend/src/components/charts/ScatterStrip.test.tsx` — update existing tests + add multi-highlight test
- Modify: `frontend/src/routes/RatingDetail.tsx` — migrate 3 call sites
- Modify: `frontend/src/routes/Student.tsx` — migrate 3 call sites in `RatingBlockStrips`
- Modify: `frontend/src/routes/Instructor.tsx` — replace table with per-rating blocks, add `InstructorRatingBlock`
- Modify: `frontend/src/routes/Instructor.test.tsx` — extend mock for cohort endpoint + `studentIds`; add new assertions

No new files. No new CSS (reuses existing `.rating-block*` classes from `frontend/src/styles/styles.css:1415-1449`).

---

## Task 1: Backend — rename `median*` → `avg*` and add `studentIds`

**Files:**
- Modify: `src/provectus_analytics/api/schemas.py:137-142`
- Modify: `src/provectus_analytics/api/adapters.py:676-738`
- Modify: `tests/test_api/test_instructors.py`

- [ ] **Step 1.1: Write the failing test**

In `tests/test_api/test_instructors.py`, add the following test at the end of the file:

```python
def test_instructor_detail_per_rating_shape(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    rows = c.get("/api/instructors").json()
    if not rows:
        return
    # Find an instructor whose detail has at least one perRating entry.
    target = None
    for row in rows:
        body = c.get(f"/api/instructors/{row['id']}").json()
        if body.get("perRating"):
            target = body
            break
    if target is None:
        return  # synthetic data may not produce any completed-rating instructors
    pr = target["perRating"][0]
    # New field names exist, old field names are gone.
    assert {"rating", "n", "avgHrs", "avgCost", "avgDays", "studentIds"} <= pr.keys()
    assert "medianHrs" not in pr
    assert "medianCost" not in pr
    assert "medianDays" not in pr
    # studentIds is a list of stringified student ids; length matches n.
    assert isinstance(pr["studentIds"], list)
    assert all(isinstance(s, str) for s in pr["studentIds"])
    assert len(pr["studentIds"]) == pr["n"]
```

- [ ] **Step 1.2: Run test to verify it fails**

Run: `cd "/Users/olsend/Documents/Provectus Analytics" && python -m pytest tests/test_api/test_instructors.py::test_instructor_detail_per_rating_shape -v`
Expected: FAIL (current schema has `medianHrs/medianCost/medianDays`, not `avgHrs/avgCost/avgDays`; no `studentIds`).

- [ ] **Step 1.3: Update `InstructorPerRating` schema**

In `src/provectus_analytics/api/schemas.py`, replace lines 137-142 with:

```python
class InstructorPerRating(BaseModel):
    rating: RatingCode
    n: int
    avgHrs: float
    avgCost: float
    avgDays: float
    studentIds: list[str]
```

- [ ] **Step 1.4: Update SQL and construction in `instructor_detail`**

In `src/provectus_analytics/api/adapters.py`, replace the `per_rating_rows = conn.execute(...)` block (currently lines 676-692) with:

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
```

Then in the same file, replace the `per_rating = [...]` list-comprehension block (currently around lines 729-738) with:

```python
    per_rating = [
        schemas.InstructorPerRating(
            rating=row["rating"],
            n=int(row["n"] or 0),
            avgHrs=float(row["avg_hours"] or 0),
            avgCost=float(row["avg_cost"] or 0),
            avgDays=float(row["avg_days"] or 0),
            studentIds=(
                row["student_ids"].split(",") if row["student_ids"] else []
            ),
        )
        for row in per_rating_rows
    ]
```

- [ ] **Step 1.5: Run the new test to verify it passes**

Run: `cd "/Users/olsend/Documents/Provectus Analytics" && python -m pytest tests/test_api/test_instructors.py -v`
Expected: All 4 tests pass (3 existing + 1 new).

- [ ] **Step 1.6: Run full backend test suite**

Run: `cd "/Users/olsend/Documents/Provectus Analytics" && python -m pytest tests`
Expected: All backend tests pass. If anything else relied on the old field names, fix it (there shouldn't be — the schema is only consumed by the frontend).

- [ ] **Step 1.7: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add src/provectus_analytics/api/schemas.py src/provectus_analytics/api/adapters.py tests/test_api/test_instructors.py
git commit -m "$(cat <<'EOF'
fix(api): rename InstructorPerRating median* to avg*, add studentIds

The fields previously labeled medianHrs/medianCost/medianDays were
always populated from AVG() SQL aggregates — they were never medians.
Renaming reflects the actual semantics. The new studentIds field lets
the Instructor Detail page identify which cohort members the
instructor taught.

Breaking change to /api/instructors/{id} response shape; only the
frontend consumes it.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Frontend — update `InstructorPerRating` interface

**Files:**
- Modify: `frontend/src/data/types.ts:127-134`

This is a small follow-up to keep the frontend type aligned with the new backend shape. No tests yet — the visible behavior change is in Task 4.

- [ ] **Step 2.1: Update the interface**

In `frontend/src/data/types.ts`, find the existing `InstructorPerRating` interface (around line 127) and replace it with:

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

- [ ] **Step 2.2: TypeScript check**

Run: `cd frontend && npx tsc -b 2>&1 | head -40`
Expected: One or more errors in `frontend/src/routes/Instructor.tsx` referring to the old field names (`p.medianHrs`, `p.medianCost`, `p.medianDays`). This is expected — Task 4 rewrites those references.

If there are TS errors in any OTHER file, stop and report — they may indicate a hidden consumer of the old shape.

- [ ] **Step 2.3: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/data/types.ts
git commit -m "$(cat <<'EOF'
chore(types): align InstructorPerRating with new backend shape

Renames median* → avg* and adds studentIds: string[]. Instructor.tsx
still references the old names; Task 4 rewrites that consumer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Migrate `ScatterStrip` to `highlightNames: string[]`

**Files:**
- Modify: `frontend/src/components/charts/ScatterStrip.tsx`
- Modify: `frontend/src/components/charts/ScatterStrip.test.tsx`
- Modify: `frontend/src/routes/RatingDetail.tsx`
- Modify: `frontend/src/routes/Student.tsx`

This is a single atomic change because the breaking prop rename touches the component and three call sites.

- [ ] **Step 3.1: Update existing tests in `ScatterStrip.test.tsx`**

In `frontend/src/components/charts/ScatterStrip.test.tsx`, find every occurrence of `highlightName={null}` and replace with `highlightNames={[]}`. Find every occurrence of `highlightName="Alice"` and replace with `highlightNames={["Alice"]}`. Use a multi-replace if your editor supports it, or do them one at a time. Verify there are no remaining `highlightName=` references.

- [ ] **Step 3.2: Add a new failing test for multi-highlight**

Append the following test to `frontend/src/components/charts/ScatterStrip.test.tsx`:

```tsx
test('multi-highlight renders multiple dots in accent color', () => {
  const POINTS_3 = [
    { student: 'Alice', value: 60 },
    { student: 'Bob', value: 65 },
    { student: 'Carol', value: 70 },
  ];
  const { container } = render(
    <ScatterStrip
      points={POINTS_3}
      band={BAND}
      median={MEDIAN}
      highlightNames={['Alice', 'Carol']}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const accentCircles = Array.from(container.querySelectorAll('circle')).filter(
    (c) => c.getAttribute('fill') === 'var(--accent)',
  );
  expect(accentCircles.length).toBe(2);
  // Bob is not highlighted; he should NOT be in accent color.
  const allCircles = Array.from(container.querySelectorAll('circle'));
  expect(allCircles.length).toBe(3);
});

test('empty highlightNames array renders no highlighted dots', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightNames={[]}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const accentCircles = Array.from(container.querySelectorAll('circle')).filter(
    (c) => c.getAttribute('fill') === 'var(--accent)',
  );
  expect(accentCircles.length).toBe(0);
});
```

- [ ] **Step 3.3: Run tests to verify the new ones fail (and existing fail-to-compile)**

Run: `cd frontend && npx vitest run src/components/charts/ScatterStrip.test.tsx 2>&1 | tail -20`
Expected: Compilation errors because `ScatterStrip` still uses `highlightName: string | null`. The TypeScript transpilation will likely flag the new prop name.

- [ ] **Step 3.4: Update `ScatterStrip.tsx`**

In `frontend/src/components/charts/ScatterStrip.tsx`:

Replace line 12 `highlightName: string | null;` with:

```tsx
  highlightNames: string[];
```

Replace line 24 `highlightName,` in the destructure with:

```tsx
  highlightNames,
```

Replace line 143 `const isHighlighted = p.student === highlightName;` with:

```tsx
          const isHighlighted = highlightNames.includes(p.student);
```

Replace line 197 (the tooltip name conditional) `{p.student === highlightName && highlightInProgress` with:

```tsx
                  {highlightNames.includes(p.student) && highlightInProgress
```

- [ ] **Step 3.5: Migrate `RatingDetail.tsx` call sites**

In `frontend/src/routes/RatingDetail.tsx`, find the 3 `highlightName={overlayName}` references (around lines 227, 246, 265). Replace each with:

```tsx
            highlightNames={overlayName ? [overlayName] : []}
```

- [ ] **Step 3.6: Migrate `Student.tsx` call sites**

In `frontend/src/routes/Student.tsx`, find the 3 `highlightName={studentName}` references in `RatingBlockStrips` (around lines 351, 363, 375). Replace each with:

```tsx
          highlightNames={[studentName]}
```

- [ ] **Step 3.7: Run all affected tests**

Run: `cd frontend && npx vitest run src/components/charts/ScatterStrip.test.tsx src/routes/RatingDetail.test.tsx src/routes/Student.test.tsx 2>&1 | tail -10`
Expected: All tests pass. Specifically: 10 ScatterStrip tests (8 existing + 2 new), 7 RatingDetail tests, 7 Student tests.

- [ ] **Step 3.8: TypeScript check**

Run: `cd frontend && npx tsc -b`
Expected: One remaining error in `Instructor.tsx` (from Task 2, references to `p.medianHrs`/etc.). No errors anywhere else.

- [ ] **Step 3.9: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/components/charts/ScatterStrip.tsx frontend/src/components/charts/ScatterStrip.test.tsx frontend/src/routes/RatingDetail.tsx frontend/src/routes/Student.tsx
git commit -m "$(cat <<'EOF'
refactor(scatter-strip): highlightName → highlightNames: string[]

Supports multi-dot highlighting needed by Instructor Detail (where
an instructor's multiple students all need accent color in the cohort
strip). Atomic migration: RatingDetail and Student Detail call sites
updated to pass single-element arrays.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Implement Instructor Detail per-rating blocks

**Files:**
- Modify: `frontend/src/routes/Instructor.tsx`
- Modify: `frontend/src/routes/Instructor.test.tsx`

This is the main feature task. Replaces the broken "Efficiency vs cohort" table with per-rating blocks (`InstructorRatingBlock`), each containing a numeric vs-cohort row and 3 mini scatter strips.

- [ ] **Step 4.1: Update test mocks and add a failing test**

In `frontend/src/routes/Instructor.test.tsx`, replace the `beforeEach` block (lines 9-30) with:

```tsx
beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/ratings/PPL/cohort')) {
      body = [
        { studentId: 's1', name: 'Alex Martinez', hours: 62, cost: 14500, days: 158 },
        { studentId: 's2', name: 'Other A', hours: 65, cost: 15500, days: 170 },
        { studentId: 's3', name: 'Other B', hours: 70, cost: 16500, days: 180 },
      ];
    } else if (url.match(/\/api\/instructors\/[^?]+/)) {
      body = {
        id: 'Doug Hayes',
        name: 'Doug Hayes',
        students: [
          { id: 's1', name: 'Alex Martinez', rating: 'PPL', progressPct: 0.95, hoursToDate: 62, daysEnrolled: 160, status: 'Completed', costToDate: 14500, instructor: 'Doug Hayes', sparkline: [4, 6, 8, 7, 5, 4, 3, 2] },
        ],
        perRating: [
          { rating: 'PPL', n: 1, avgHrs: 62, avgCost: 14500, avgDays: 158, studentIds: ['s1'] },
        ],
      };
    } else if (url.includes('/api/instructors')) {
      body = [
        { id: 'Doug Hayes', name: 'Doug Hayes', hours: 412, students: 6, passRate: 0.9 },
      ];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
});
```

Add the following new test below the existing `shows instructor detail after selecting one` test:

```tsx
test('renders per-rating block with 3 scatter strips and correct highlight', async () => {
  const { container } = render(wrap('/instructors/Doug%20Hayes'));
  await waitFor(() => expect(screen.getByText('Per rating vs cohort')).toBeTruthy());
  // The PPL rating chip should appear in the block head
  const ppl = Array.from(container.querySelectorAll('.rating-chip')).find(
    (el) => el.textContent === 'PPL',
  );
  expect(ppl).toBeTruthy();
  // 3 SVGs (mini scatter strips) inside the rating block
  await waitFor(() => {
    const svgs = container.querySelectorAll('.rating-block svg');
    expect(svgs.length).toBe(3);
  });
  // Exactly 1 student is highlighted (s1 — Alex Martinez)
  const accentCircles = Array.from(
    container.querySelectorAll('.rating-block circle[fill="var(--accent)"]'),
  );
  // 3 strips × 1 highlighted student per strip = 3 accent circles
  expect(accentCircles.length).toBe(3);
});
```

- [ ] **Step 4.2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/routes/Instructor.test.tsx 2>&1 | tail -10`
Expected: The new test fails ("Per rating vs cohort" heading doesn't exist yet, and no scatter strips render).

- [ ] **Step 4.3: Rewrite `Instructor.tsx`**

Replace the entire contents of `frontend/src/routes/Instructor.tsx` with:

```tsx
import { useNavigate, useParams } from 'react-router-dom';
import type { UseQueryResult } from '@tanstack/react-query';
import { BigKpi, DeltaText, MiniKpi, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import { ScatterStrip } from '../components/charts/ScatterStrip';
import { useInstructor, useInstructors, useRatingCohorts } from '../data/queries';
import type {
  InstructorDetail,
  InstructorPerRating,
  RatingCohortMember,
} from '../data/types';

function fmtCost(v: number): string {
  return `$${Math.round(v).toLocaleString()}`;
}

function median(vals: number[]): number {
  if (vals.length === 0) return 0;
  const sorted = [...vals].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
}

export default function Instructor() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const listQ = useInstructors();
  const detailQ = useInstructor(id);

  const opts = (listQ.data ?? []).map((i) => ({ value: i.id, label: i.name }));

  return (
    <div className="instructor-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">People</div>
          <h1 className="page-title">Instructor</h1>
          <div className="page-sub">Efficiency relative to cohort medians, per rating.</div>
        </div>
        <div className="page-head-tools">
          <Select<string>
            label="Instructor"
            value={id ?? ''}
            onChange={(v) => v && navigate(`/instructors/${encodeURIComponent(v)}`)}
            options={opts}
            width={220}
          />
        </div>
      </div>

      {!id ? (
        <div className="card">
          <div className="empty">
            <div className="empty-title">Pick an instructor</div>
            <div className="empty-sub">Use the selector above to drill in.</div>
          </div>
        </div>
      ) : detailQ.isLoading ? (
        <Skel h={240} />
      ) : detailQ.data ? (
        <InstructorBody detail={detailQ.data} />
      ) : (
        <div className="card">
          <div className="empty">
            <div className="empty-title">Instructor not found</div>
            <div className="empty-sub">{id}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function InstructorBody({ detail }: { detail: InstructorDetail }) {
  const totalHours = detail.students.reduce((s, c) => s + c.hoursToDate, 0);
  const studentsAtCheckride = detail.students.filter((s) => s.status === 'Completed').length;
  const cohortCodes = detail.perRating.map((p) => p.rating);
  const cohorts = useRatingCohorts(cohortCodes);

  return (
    <>
      <div className="kpi-grid kpi-grid-2">
        <BigKpi
          label="Ratings taught"
          value={String(detail.perRating.length)}
          sub={detail.perRating.map((p) => p.rating).join(', ') || '—'}
        />
        <BigKpi
          label="Students at checkride"
          value={String(studentsAtCheckride)}
          sub={`Total hours flown: ${totalHours.toFixed(1)}`}
        />
      </div>

      <div className="section-head">
        <h2 className="section-title">Per rating vs cohort</h2>
      </div>
      {detail.perRating.length === 0 && (
        <div className="card">
          <div className="empty">
            <div className="empty-title">No completed ratings yet</div>
            <div className="empty-sub">
              Students under this instructor haven't reached checkride.
            </div>
          </div>
        </div>
      )}
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
      <div className="card table-card">
        <div className="table-wrap" style={{ maxHeight: 480 }}>
          <table className="dt">
            <thead>
              <tr>
                <th>Student</th>
                <th>Rating</th>
                <th className="num">Hours</th>
                <th className="num">Days enrolled</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.students.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <div className="empty">
                      <div className="empty-title">No students assigned</div>
                    </div>
                  </td>
                </tr>
              )}
              {detail.students.map((row) => (
                <tr key={`${row.id}-${row.rating}`}>
                  <td>{row.name}</td>
                  <td>
                    <span className="rating-chip">{row.rating}</span>
                  </td>
                  <td className="num">{row.hoursToDate.toFixed(1)}</td>
                  <td className="num">{row.daysEnrolled}</td>
                  <td>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function InstructorRatingBlock({
  r,
  cohortQuery,
}: {
  r: InstructorPerRating;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
}) {
  const cohort = cohortQuery?.data ?? [];
  const cohortMedHrs = median(cohort.map((m) => m.hours));
  const cohortMedCost = median(cohort.map((m) => m.cost));
  const cohortMedDays = median(cohort.map((m) => m.days));

  const highlightNames = cohort
    .filter((m) => r.studentIds.includes(m.studentId))
    .map((m) => m.name);

  return (
    <div className="rating-block">
      <div className="rating-block-head">
        <div className="rating-block-title">
          <span className="rating-chip">{r.rating}</span>
          <span className="rating-block-name">
            {r.n} student{r.n === 1 ? '' : 's'}
          </span>
        </div>
        <div className="rating-block-n">n={r.n}</div>
      </div>

      <div className="minikpi-grid">
        <MiniKpi
          label="Avg hours"
          value={r.avgHrs.toFixed(1)}
          deltaNode={
            <DeltaText
              value={cohortMedHrs ? +(r.avgHrs - cohortMedHrs).toFixed(1) : 0}
              betterWhenLower
              fmt={(v) => v.toFixed(1)}
            />
          }
          sub={cohortMedHrs ? `Cohort median: ${cohortMedHrs.toFixed(1)}` : 'No cohort data'}
        />
        <MiniKpi
          label="Avg cost"
          value={fmtCost(r.avgCost)}
          deltaNode={
            <DeltaText
              value={cohortMedCost ? r.avgCost - cohortMedCost : 0}
              betterWhenLower
              fmt={(v) => fmtCost(v)}
            />
          }
          sub={cohortMedCost ? `Cohort median: ${fmtCost(cohortMedCost)}` : 'No cohort data'}
        />
        <MiniKpi
          label="Avg days"
          value={Math.round(r.avgDays).toLocaleString()}
          deltaNode={
            <DeltaText
              value={cohortMedDays ? r.avgDays - cohortMedDays : 0}
              betterWhenLower
              fmt={(v) => Math.round(v).toLocaleString()}
            />
          }
          sub={cohortMedDays ? `Cohort median: ${Math.round(cohortMedDays)}` : 'No cohort data'}
        />
        <MiniKpi label="Students (n)" value={String(r.n)} />
      </div>

      <InstructorStrips
        r={r}
        cohortQuery={cohortQuery}
        highlightNames={highlightNames}
      />
    </div>
  );
}

function InstructorStrips({
  r,
  cohortQuery,
  highlightNames,
}: {
  r: InstructorPerRating;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
  highlightNames: string[];
}) {
  if (cohortQuery?.isLoading) {
    return (
      <div className="rating-block-strips">
        <div className="strip-cell">
          <Skel h={60} />
        </div>
        <div className="strip-cell">
          <Skel h={60} />
        </div>
        <div className="strip-cell">
          <Skel h={60} />
        </div>
      </div>
    );
  }

  if (cohortQuery?.isError || !cohortQuery?.data || cohortQuery.data.length === 0) {
    return null;
  }

  const cohort = cohortQuery.data;

  const stripPoints = (selector: (m: RatingCohortMember) => number) =>
    cohort.map((m) => ({ student: m.name, value: selector(m) }));

  // Derive P25/P75 band client-side from cohort points (consistent with Student Detail).
  const range = (selector: (m: RatingCohortMember) => number) => {
    if (cohort.length === 0) return { low: 0, high: 0 };
    const vals = cohort.map(selector).sort((a, b) => a - b);
    const q = (p: number) => vals[Math.min(vals.length - 1, Math.floor(p * (vals.length - 1)))];
    return { low: q(0.25), high: q(0.75) };
  };

  const medianHrs = median(cohort.map((m) => m.hours));
  const medianCost = median(cohort.map((m) => m.cost));
  const medianDays = median(cohort.map((m) => m.days));
  void r; // r is unused here but kept in the signature for future per-rating tweaks

  return (
    <div className="rating-block-strips">
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.hours)}
          band={range((m) => m.hours)}
          median={medianHrs}
          highlightNames={highlightNames}
          yLabel="Hours"
          fmt={(v) => v.toFixed(1)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.cost)}
          band={range((m) => m.cost)}
          median={medianCost}
          highlightNames={highlightNames}
          yLabel="Cost"
          fmt={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Math.round(v)}`)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.days)}
          band={range((m) => m.days)}
          median={medianDays}
          highlightNames={highlightNames}
          yLabel="Days"
          fmt={(v) => Math.round(v).toLocaleString()}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 4.4: Run Instructor tests to verify they pass**

Run: `cd frontend && npx vitest run src/routes/Instructor.test.tsx 2>&1 | tail -10`
Expected: 3 Instructor tests pass (2 existing + 1 new).

- [ ] **Step 4.5: Full TypeScript check**

Run: `cd frontend && npx tsc -b`
Expected: Clean (no errors).

- [ ] **Step 4.6: Full frontend test suite**

Run: `cd frontend && npx vitest run 2>&1 | tail -10`
Expected: All tests pass. Total count: 75 (was 73 after PR #1; +1 ScatterStrip multi-highlight test from Task 3 step 3.2, +1 empty-array test, +1 Instructor strip test from Task 4).

Note: the exact count depends on how many tests Task 3 added. The important thing is that ALL tests pass.

- [ ] **Step 4.7: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/routes/Instructor.tsx frontend/src/routes/Instructor.test.tsx
git commit -m "$(cat <<'EOF'
feat(instructor-detail): per-rating blocks with vs-cohort comparison

Replaces the broken "Efficiency vs cohort" table with per-rating
blocks. Each block shows:
- Rating chip + count
- 3 MiniKpis (avg hrs / cost / days) with delta vs client-side cohort
  median (computed from the cohort endpoint)
- 3 mini scatter strips with the instructor's completed students
  multi-highlighted in accent color

Reuses ScatterStrip (mini variant, multi-highlight) and
useRatingCohorts from the Student Detail PR.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Final verification + PR prep

**Files:** none

- [ ] **Step 5.1: Run full backend test suite**

```bash
cd "/Users/olsend/Documents/Provectus Analytics" && python -m pytest tests
```

Expected: All backend tests pass.

- [ ] **Step 5.2: Run full frontend test suite**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend" && npx vitest run
```

Expected: All frontend tests pass.

- [ ] **Step 5.3: TypeScript build**

Run: `cd frontend && npx tsc -b`
Expected: Clean.

- [ ] **Step 5.4: Lint**

Run: `cd frontend && npx eslint . 2>&1 | tail -10`
Expected: No new errors compared to main (the 5 pre-existing errors from CmdK, Sidebar, Sparkline, RatingDetail's useEffect are unchanged — they were unaffected by this branch).

- [ ] **Step 5.5: Verify Rating Detail and Student Detail still work**

Spot-check: open the dev server (`cd frontend && npx vite`), navigate to Rating Detail and Student Detail, confirm the overlay/highlighted dots still render correctly (they're now passed `highlightNames` arrays instead of single names; visually identical). Then navigate to Instructor Detail and confirm the new per-rating blocks render with the right number of accent-colored dots for the instructor's students.

This step is manual; skip if no easy way to start the dev server, but try at least once to catch any CSS regressions the unit tests don't cover.

- [ ] **Step 5.6: Confirm with user before pushing**

GitHub pushes are manual — ask the user before running `git push -u origin feat/instructor-detail-flesh-out`.

When approved, push:

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git push -u origin feat/instructor-detail-flesh-out
```

- [ ] **Step 5.7: Open PR (only after push succeeds)**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
gh pr create --title "Instructor Detail: flesh out + fix vs-cohort comparison" --body "$(cat <<'EOF'
## Summary
- Replaces the broken "Efficiency vs cohort" table on Instructor Detail with per-rating blocks
- Each block: rating chip + count, 3 MiniKpis (avg hrs/cost/days) with delta vs cohort median, 3 mini scatter strips with the instructor's completed students multi-highlighted
- Fixes the data-integrity bug where `InstructorPerRating.median*` fields were actually averages — renamed to `avgHrs/avgCost/avgDays` and added `studentIds: list[str]`
- Extends `ScatterStrip` to `highlightNames: string[]` (was `highlightName: string | null`); migrated Rating Detail and Student Detail callers atomically

## Why
The "Efficiency vs cohort" table on Instructor Detail was mislabeled and never actually compared to cohort — the columns labeled "Med hrs / Med cost / Med days" were `AVG()` SQL aggregates of the instructor's own students. No comparison to the cohort was ever fetched. This branch fixes the bug, adds the missing comparison, and replaces the table with the same per-rating block pattern shipped on Student Detail in PR #1.

## Reviewer notes
- Breaking API change: `/api/instructors/{id}` response shape changed (field rename + new `studentIds` field). The frontend is the only consumer.
- Breaking ScatterStrip prop change: `highlightName` → `highlightNames: string[]`. All 3 current call sites migrated in this branch.
- No new CSS — reuses `.rating-block*` classes from PR #1.
- Spec: `docs/superpowers/specs/2026-05-26-instructor-detail-flesh-out-design.md`
- Plan: `docs/superpowers/plans/2026-05-26-instructor-detail-flesh-out.md`

## Test plan
- [x] Backend: all instructor API tests pass; new test asserts the new field shape and `studentIds` count matches `n`
- [x] Frontend: ScatterStrip unit tests cover multi-highlight + empty array
- [x] Frontend: Instructor integration test asserts 3 svgs render per block with the right number of accent dots
- [x] Frontend: Rating Detail + Student Detail tests still pass with migrated `highlightNames` prop
- [x] `tsc -b` clean
- [x] No new ESLint issues
- [ ] Visual spot-check on dev server

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-review notes

**Spec coverage:**

- Spec: rename `median*` → `avg*` on `InstructorPerRating` → Task 1 ✓
- Spec: add `studentIds: list[str]` → Task 1 ✓
- Spec: `ScatterStrip` prop migration → Task 3 ✓
- Spec: migrate Rating Detail and Student Detail call sites atomically → Task 3 ✓
- Spec: replace table with per-rating blocks → Task 4 ✓
- Spec: numeric comparison row (instructor avg vs cohort median, delta) → Task 4 ✓
- Spec: 3 mini scatter strips with multi-highlight → Task 4 ✓
- Spec: highlight by intersecting `r.studentIds` with cohort → Task 4 ✓
- Spec: edge cases (loading skeleton, error hide, empty cohort hide) → Task 4 ✓
- Spec: tests at backend + unit + integration levels → distributed across tasks ✓
- Spec: roster table unchanged → Task 4 (preserved in `InstructorBody`) ✓

**Type consistency:**

- `InstructorPerRating` fields used in Task 4 (`r.avgHrs`, `r.avgCost`, `r.avgDays`, `r.studentIds`) match the schema defined in Tasks 1 and 2.
- `ScatterStrip` prop name `highlightNames: string[]` is consistent across Task 3 component update, Task 3 caller migrations, and Task 4 new uses.
- `median()` helper function defined once at the top of `Instructor.tsx` and used in both `InstructorRatingBlock` and `InstructorStrips`.

**Placeholder scan:**

- No "TBD", no "TODO", no "fill in details".
- Every step has either exact code or exact commands.
- The `void r;` line in `InstructorStrips` is intentional (keeps the prop in the signature for future tweaks without TS unused-param warning); not a placeholder.

**Deviation notes:**

- The spec mentioned reusing `.rating-block` styles from Student Detail's PR #1. Task 4 does this without adding new CSS.
- The `median()` helper is implemented client-side rather than as a server addition. This is consistent with Student Detail's pattern (P25/P75 derived client-side).
- The `r` parameter in `InstructorStrips` is currently unused (`void r;`). It's kept for forward compatibility (e.g., if we later want to show per-rating notes inside the strips). If a reviewer objects, drop the prop and pass `highlightNames` only.
