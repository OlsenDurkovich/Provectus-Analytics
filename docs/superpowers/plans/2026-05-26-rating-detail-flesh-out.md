# Rating Detail Flesh-Out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cohort scatter-strip distribution chart, overlay-student KPI comparison, and alumni cohort table to the Rating Detail page.

**Architecture:** New `GET /api/ratings/{code}/cohort` backend endpoint feeds a `useRatingCohort` hook; `RatingDetail.tsx` is overhauled to add an overlay-student selector, wires overlay data into the existing `BigKpi` overlay prop, and renders three `ScatterStrip` charts plus a cohort table below the KPI grid. All CSS, `BigKpi`, and `Select` infrastructure is already in place — no changes needed to those files.

**Tech Stack:** FastAPI + SQLite (backend), React 18 + React Query v5 + Vite + TypeScript (frontend), Vitest + Testing Library (tests), SVG for charts.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `src/provectus_analytics/api/schemas.py` | Add `RatingCohortMember` model |
| Modify | `src/provectus_analytics/api/adapters.py` | Add `rating_cohort()` function |
| Modify | `src/provectus_analytics/api/routers/ratings.py` | Add `GET /api/ratings/{code}/cohort` route |
| Modify | `tests/test_api/test_rating_detail.py` | Add cohort endpoint tests |
| Modify | `frontend/src/data/types.ts` | Add `RatingCohortMember` interface |
| Modify | `frontend/src/data/client.ts` | Add `getRatingCohort` method |
| Modify | `frontend/src/data/queries.ts` | Add `useRatingCohort` hook + query key |
| Modify | `frontend/src/data/client.test.ts` | Add `getRatingCohort` test |
| **Create** | `frontend/src/components/charts/ScatterStrip.tsx` | New SVG scatter strip chart |
| Modify | `frontend/src/components/charts/charts.test.tsx` | Add `ScatterStrip` render test |
| Modify | `frontend/src/routes/RatingDetail.tsx` | Full page overhaul |
| **Create** | `frontend/src/routes/RatingDetail.test.tsx` | Route-level render tests |

---

## Task 1: Backend — cohort schema, adapter, and route

**Files:**
- Modify: `src/provectus_analytics/api/schemas.py`
- Modify: `src/provectus_analytics/api/adapters.py`
- Modify: `src/provectus_analytics/api/routers/ratings.py`
- Test: `tests/test_api/test_rating_detail.py`

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `tests/test_api/test_rating_detail.py`:

```python
def test_rating_cohort_returns_list(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/ratings/PPL/cohort")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) > 0
    first = body[0]
    assert "studentId" in first
    assert "name" in first
    assert "hours" in first
    assert "cost" in first
    assert "days" in first
    assert first["hours"] > 0


def test_rating_cohort_sorted_ascending_hours(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/ratings/PPL/cohort")
    body = r.json()
    hours = [m["hours"] for m in body]
    assert hours == sorted(hours)


def test_rating_cohort_invalid_code_returns_422(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/ratings/XYZ/cohort")
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
python -m pytest tests/test_api/test_rating_detail.py::test_rating_cohort_returns_list -v
```
Expected: `FAILED` — 404 or 422 (route doesn't exist yet).

- [ ] **Step 3: Add `RatingCohortMember` to schemas.py**

In `src/provectus_analytics/api/schemas.py`, add after the `Rating` class (after line 51):

```python
class RatingCohortMember(BaseModel):
    studentId: str
    name: str
    hours: float
    cost: float
    days: int
```

- [ ] **Step 4: Add `rating_cohort` to adapters.py**

In `src/provectus_analytics/api/adapters.py`, add after the `rating_detail` function (after line 318):

```python
def rating_cohort(code: schemas.RatingCode) -> list[schemas.RatingCohortMember]:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT e.student_id, s.fsp_display_name,
                      m.cumulative_hours, m.cumulative_cost, m.days_from_rating_start
               FROM milestones m
               JOIN enrollments e USING (enrollment_id)
               JOIN ratings r USING (rating_id)
               JOIN students s USING (student_id)
               WHERE m.milestone_name = 'checkride' AND r.code = ?
               ORDER BY m.cumulative_hours""",
            (code,),
        ).fetchall()
    finally:
        conn.close()
    return [
        schemas.RatingCohortMember(
            studentId=str(row["student_id"]),
            name=row["fsp_display_name"] or "Unknown",
            hours=float(row["cumulative_hours"] or 0),
            cost=float(row["cumulative_cost"] or 0),
            days=int(row["days_from_rating_start"] or 0),
        )
        for row in rows
    ]
```

- [ ] **Step 5: Add the route to routers/ratings.py**

In `src/provectus_analytics/api/routers/ratings.py`, add after the existing `get_rating` route (after line 28):

```python
@router.get("/ratings/{code}/cohort", response_model=list[schemas.RatingCohortMember])
def get_rating_cohort(code: schemas.RatingCode):
    return adapters.rating_cohort(code)
```

- [ ] **Step 6: Run all three new tests**

```bash
python -m pytest tests/test_api/test_rating_detail.py -v
```
Expected: all 5 tests pass (3 existing + 2 new cohort tests; the 422 test may show as `xpass` depending on the invalid code — that's fine).

- [ ] **Step 7: Run the full Python test suite**

```bash
python -m pytest tests/ -q
```
Expected: all green, no regressions.

- [ ] **Step 8: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add src/provectus_analytics/api/schemas.py \
        src/provectus_analytics/api/adapters.py \
        src/provectus_analytics/api/routers/ratings.py \
        tests/test_api/test_rating_detail.py
git commit -m "feat: add GET /api/ratings/{code}/cohort endpoint"
```

---

## Task 2: Frontend data layer — type, client method, query hook

**Files:**
- Modify: `frontend/src/data/types.ts`
- Modify: `frontend/src/data/client.ts`
- Modify: `frontend/src/data/queries.ts`
- Modify: `frontend/src/data/client.test.ts`

- [ ] **Step 1: Write the failing client test**

Add to `frontend/src/data/client.test.ts` inside the `describe('client', ...)` block (before the closing `}`):

```typescript
  test('getRatingCohort calls /api/ratings/PPL/cohort', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => [
        { studentId: '1', name: 'Alice', hours: 60.0, cost: 15000, days: 400 },
      ],
    });
    const result = await client.getRatingCohort('PPL');
    expect(result).toHaveLength(1);
    expect(result[0].studentId).toBe('1');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/ratings/PPL/cohort',
      expect.anything(),
    );
  });
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend"
npx vitest run src/data/client.test.ts
```
Expected: `FAILED` — `client.getRatingCohort is not a function`.

- [ ] **Step 3: Add `RatingCohortMember` to types.ts**

In `frontend/src/data/types.ts`, add after the `Rating` interface (after line 44):

```typescript
export interface RatingCohortMember {
  studentId: string;
  name: string;
  hours: number;
  cost: number;
  days: number;
}
```

- [ ] **Step 4: Add `getRatingCohort` to client.ts**

In `frontend/src/data/client.ts`, add `RatingCohortMember` to the import (line 1):

```typescript
import type {
  Meta,
  Kpi,
  RatingBarPoint,
  RatingsCompletedRow,
  Heatmap,
  ClientRow,
  StudentDetail,
  InstructorSummary,
  InstructorDetail,
  FlightRow,
  FlightUpdate,
  RangeKey,
  MetricKey,
  RatingCode,
  Rating,
  RatingCohortMember,
} from './types';
```

Then add to the `client` object after `getRating` (after the `getRating` line):

```typescript
  getRatingCohort: (code: RatingCode) =>
    get<RatingCohortMember[]>(`/api/ratings/${code}/cohort`),
```

- [ ] **Step 5: Add `useRatingCohort` to queries.ts**

In `frontend/src/data/queries.ts`, add `ratingCohort` to `queryKeys` (after the `rating` key):

```typescript
  ratingCohort: (code: RatingCode) => ['ratingCohort', code] as const,
```

Then add the hook after `useRating`:

```typescript
export const useRatingCohort = (code: RatingCode) =>
  useQuery({
    queryKey: queryKeys.ratingCohort(code),
    queryFn: () => client.getRatingCohort(code),
  });
```

- [ ] **Step 6: Run the client test**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend"
npx vitest run src/data/client.test.ts
```
Expected: all 4 tests pass.

- [ ] **Step 7: TypeScript check**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend"
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/data/types.ts \
        frontend/src/data/client.ts \
        frontend/src/data/queries.ts \
        frontend/src/data/client.test.ts
git commit -m "feat: add RatingCohortMember type and useRatingCohort hook"
```

---

## Task 3: ScatterStrip component

**Files:**
- Create: `frontend/src/components/charts/ScatterStrip.tsx`
- Modify: `frontend/src/components/charts/charts.test.tsx`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/components/charts/charts.test.tsx`:

```typescript
import { ScatterStrip } from './ScatterStrip';

test('ScatterStrip renders an SVG with dots for each point', () => {
  const points = [
    { student: 'Alice', value: 60 },
    { student: 'Bob', value: 70 },
    { student: 'Carol', value: 55 },
  ];
  const { container } = render(
    <ScatterStrip
      points={points}
      band={{ low: 58, high: 72 }}
      median={65}
      highlightName="Bob"
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  expect(container.querySelector('svg')).toBeTruthy();
  // 3 dots rendered as circles
  expect(container.querySelectorAll('circle').length).toBe(3);
});

test('ScatterStrip renders without highlighted point', () => {
  const { container } = render(
    <ScatterStrip
      points={[{ student: 'Alice', value: 60 }]}
      band={{ low: 55, high: 65 }}
      median={60}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  expect(container.querySelector('svg')).toBeTruthy();
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend"
npx vitest run src/components/charts/charts.test.tsx
```
Expected: `FAILED` — `ScatterStrip` module not found.

- [ ] **Step 3: Create ScatterStrip.tsx**

Create `frontend/src/components/charts/ScatterStrip.tsx`:

```typescript
import { useEffect, useRef, useState } from 'react';

interface Point {
  student: string;
  value: number;
}

interface Props {
  points: Point[];
  band: { low: number; high: number };
  median: number;
  highlightName: string | null;
  yLabel: string;
  fmt: (v: number) => string;
  height?: number;
}

export function ScatterStrip({
  points,
  band,
  median,
  highlightName,
  yLabel,
  fmt,
  height = 280,
}: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [w, setW] = useState(800);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const padL = 56, padR = 16, padT = 18, padB = 16;
  const innerW = Math.max(10, w - padL - padR);
  const innerH = height - padT - padB;
  const n = Math.max(1, points.length);

  const allVals = [...points.map((p) => p.value), band.low, band.high, median];
  const minV = Math.min(...allVals);
  const maxV = Math.max(...allVals);
  const span = Math.max(1, maxV - minV);
  const yMin = minV - span * 0.12;
  const yMax = maxV + span * 0.12;
  const ySpan = Math.max(1, yMax - yMin);

  const yAt = (v: number) => padT + innerH - ((v - yMin) / ySpan) * innerH;
  const xAt = (i: number) => padL + ((i + 1) / (n + 1)) * innerW;

  const ticks = Array.from({ length: 5 }, (_, i) => yMin + (ySpan * i) / 4);

  return (
    <div ref={ref} className="timechart">
      <svg
        width={w}
        height={height}
        onMouseLeave={() => setHovered(null)}
        style={{ cursor: 'default' }}
      >
        {/* Grid lines + y-axis labels */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={padL}
              x2={w - padR}
              y1={yAt(t)}
              y2={yAt(t)}
              stroke="var(--grid)"
              strokeWidth="1"
            />
            <text
              x={padL - 8}
              y={yAt(t) + 3}
              textAnchor="end"
              fontSize="10.5"
              fill="var(--fg-dim)"
              fontFamily="'Geist Mono', monospace"
            >
              {fmt(t)}
            </text>
          </g>
        ))}

        {/* Y-axis label */}
        <text
          x={10}
          y={padT + innerH / 2}
          textAnchor="middle"
          fontSize="10"
          fill="var(--fg-dim)"
          transform={`rotate(-90, 10, ${padT + innerH / 2})`}
        >
          {yLabel}
        </text>

        {/* P25-P75 band */}
        <rect
          x={padL}
          y={yAt(band.high)}
          width={innerW}
          height={Math.max(0, yAt(band.low) - yAt(band.high))}
          fill="color-mix(in oklab, var(--accent) 14%, transparent)"
        />

        {/* Median dashed line */}
        <line
          x1={padL}
          x2={w - padR}
          y1={yAt(median)}
          y2={yAt(median)}
          stroke="var(--accent)"
          strokeWidth="1.2"
          strokeDasharray="4 3"
          opacity="0.7"
        />

        {/* Dots */}
        {points.map((p, i) => {
          const isHighlighted = p.student === highlightName;
          const cx = xAt(i);
          const cy = yAt(p.value);
          return (
            <g key={i} onMouseEnter={() => setHovered(i)}>
              <circle
                cx={cx}
                cy={cy}
                r={isHighlighted ? 7 : 5}
                fill={isHighlighted ? 'var(--accent)' : 'var(--fg-dim)'}
                fillOpacity={isHighlighted ? 1 : 0.5}
                stroke={isHighlighted ? 'var(--bg)' : 'none'}
                strokeWidth="1.5"
              />
            </g>
          );
        })}

        {/* Hover tooltip */}
        {hovered !== null &&
          points[hovered] &&
          (() => {
            const p = points[hovered];
            const cx = xAt(hovered);
            const cy = yAt(p.value);
            const tipW = 152, tipH = 44;
            const tx = Math.min(Math.max(cx - tipW / 2, padL), w - padR - tipW);
            const ty = Math.max(padT + 4, cy - tipH - 10);
            return (
              <g pointerEvents="none">
                <rect
                  x={tx}
                  y={ty}
                  width={tipW}
                  height={tipH}
                  rx="6"
                  fill="var(--bg-elev-2)"
                  stroke="var(--border-strong)"
                />
                <text
                  x={tx + 10}
                  y={ty + 17}
                  fontSize="11"
                  fill="var(--fg)"
                  fontWeight="500"
                >
                  {p.student}
                </text>
                <text
                  x={tx + 10}
                  y={ty + 33}
                  fontSize="11"
                  fill="var(--fg-dim)"
                  fontFamily="'Geist Mono', monospace"
                >
                  {fmt(p.value)}
                </text>
              </g>
            );
          })()}
      </svg>
    </div>
  );
}
```

- [ ] **Step 4: Run the chart tests**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend"
npx vitest run src/components/charts/charts.test.tsx
```
Expected: all 5 tests pass (3 existing + 2 new).

- [ ] **Step 5: TypeScript check**

```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/components/charts/ScatterStrip.tsx \
        frontend/src/components/charts/charts.test.tsx
git commit -m "feat: add ScatterStrip chart component"
```

---

## Task 4: RatingDetail page overhaul

**Files:**
- Modify: `frontend/src/routes/RatingDetail.tsx`
- Create: `frontend/src/routes/RatingDetail.test.tsx`

- [ ] **Step 1: Write the failing route tests**

Create `frontend/src/routes/RatingDetail.test.tsx`:

```typescript
import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import RatingDetail from './RatingDetail';

const origFetch = globalThis.fetch;

const RATING_BODY = {
  code: 'PPL',
  name: 'Private Pilot',
  n: 12,
  medianHrs: 64.2,
  p25Hrs: 59.8,
  p75Hrs: 65.6,
  medianCost: 16569,
  p25Cost: 15695,
  p75Cost: 17771,
  medianDays: 407,
  p25Days: 374,
  p75Days: 455,
  lowSample: false,
};

const COHORT_BODY = [
  { studentId: '1', name: 'Alice', hours: 60.0, cost: 15000, days: 380 },
  { studentId: '2', name: 'Bob', hours: 64.2, cost: 16569, days: 407 },
];

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/cohort')) {
      return Promise.resolve({ ok: true, json: async () => COHORT_BODY });
    }
    if (url.includes('/api/ratings/PPL')) {
      return Promise.resolve({ ok: true, json: async () => RATING_BODY });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
});

afterEach(() => {
  globalThis.fetch = origFetch;
});

function wrap(path = '/ratings/PPL') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/ratings/:code" element={<RatingDetail range="12mo" />} />
          <Route path="/ratings" element={<RatingDetail range="12mo" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test('renders the static page title', () => {
  render(wrap());
  expect(screen.getByText('Rating detail')).toBeTruthy();
});

test('renders KPI cards after data loads', async () => {
  render(wrap());
  await waitFor(() => expect(screen.getByText('64.2')).toBeTruthy());
  expect(screen.getByText('Alumni (n)')).toBeTruthy();
  expect(screen.getByText('12')).toBeTruthy();
});

test('renders cohort table after data loads', async () => {
  render(wrap());
  await waitFor(() => expect(screen.getByText('Alice')).toBeTruthy());
  expect(screen.getByText('Bob')).toBeTruthy();
});

test('renders Distribution section heading', async () => {
  render(wrap());
  await waitFor(() => expect(screen.getByText('Distribution')).toBeTruthy());
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend"
npx vitest run src/routes/RatingDetail.test.tsx
```
Expected: `FAILED` — tests referencing `"Rating detail"` h1 or cohort data will fail against the current implementation.

- [ ] **Step 3: Replace RatingDetail.tsx**

Replace the full contents of `frontend/src/routes/RatingDetail.tsx` with:

```typescript
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { BigKpi, DeltaText, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import { ScatterStrip } from '../components/charts/ScatterStrip';
import { useRating, useRatingCohort } from '../data/queries';
import type { RangeKey, RatingCode, RatingCohortMember } from '../data/types';

const CODES: RatingCode[] = ['PPL', 'IFR', 'COM', 'AMEL', 'CFI', 'CFII', 'MEI'];

function fmtCost(v: number): string {
  return `$${Math.round(v).toLocaleString()}`;
}

type Props = { range: RangeKey };

export default function RatingDetail({ range }: Props) {
  const { code } = useParams<{ code?: string }>();
  const navigate = useNavigate();
  const selected = (CODES.includes(code as RatingCode) ? code : 'PPL') as RatingCode;
  const [overlayId, setOverlayId] = useState<string | null>(null);

  const rating = useRating(selected, range);
  const cohort = useRatingCohort(selected);

  const cohortData = cohort.data ?? [];
  const overlayPt = overlayId
    ? (cohortData.find((m) => m.studentId === overlayId) ?? null)
    : null;

  const studentOpts = cohortData.map((m) => ({ value: m.studentId, label: m.name }));

  return (
    <div className="rating-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">Detail</div>
          <h1 className="page-title">Rating detail</h1>
          <div className="page-sub">
            Cohort distribution with P25–P75 band. Compare an individual to the band.
          </div>
        </div>
        <div className="page-head-tools">
          <Select<RatingCode>
            label="Rating"
            value={selected}
            onChange={(v) => {
              if (v) {
                setOverlayId(null);
                navigate(`/ratings/${v}`);
              }
            }}
            options={CODES.map((c) => ({ value: c, label: c }))}
            width={130}
          />
          <Select<string>
            label="Overlay student"
            value={overlayId}
            onChange={setOverlayId}
            options={studentOpts}
            width={220}
            allowClear
          />
        </div>
      </div>

      {rating.isLoading ? (
        <Skel h={200} />
      ) : rating.data ? (
        <>
          <div className="kpi-grid">
            <BigKpi
              label="Alumni (n)"
              value={String(rating.data.n)}
              sub={
                rating.data.lowSample
                  ? 'Low sample — interpret with care'
                  : 'Sufficient sample'
              }
            />
            <BigKpi
              label="Median hours"
              value={rating.data.medianHrs.toFixed(1)}
              overlay={
                overlayPt
                  ? { label: overlayPt.name, value: overlayPt.hours.toFixed(1) }
                  : undefined
              }
              deltaNode={
                overlayPt ? (
                  <DeltaText
                    value={+(overlayPt.hours - rating.data.medianHrs).toFixed(1)}
                    betterWhenLower
                    fmt={(v) => v.toFixed(1)}
                  />
                ) : undefined
              }
              sub={`P25–P75: ${rating.data.p25Hrs.toFixed(1)} – ${rating.data.p75Hrs.toFixed(1)}`}
            />
            <BigKpi
              label="Median cost"
              value={fmtCost(rating.data.medianCost)}
              overlay={
                overlayPt
                  ? { label: overlayPt.name, value: fmtCost(overlayPt.cost) }
                  : undefined
              }
              deltaNode={
                overlayPt ? (
                  <DeltaText
                    value={Math.round(overlayPt.cost - rating.data.medianCost)}
                    betterWhenLower
                    fmt={(v) => `$${Math.round(v).toLocaleString()}`}
                  />
                ) : undefined
              }
              sub={`P25–P75: ${fmtCost(rating.data.p25Cost)} – ${fmtCost(rating.data.p75Cost)}`}
            />
            <BigKpi
              label="Median days"
              value={Math.round(rating.data.medianDays).toLocaleString()}
              overlay={
                overlayPt
                  ? {
                      label: overlayPt.name,
                      value: overlayPt.days.toLocaleString(),
                    }
                  : undefined
              }
              deltaNode={
                overlayPt ? (
                  <DeltaText
                    value={overlayPt.days - Math.round(rating.data.medianDays)}
                    betterWhenLower
                    fmt={(v) => Math.round(Math.abs(v)).toLocaleString()}
                  />
                ) : undefined
              }
              sub={`P25–P75: ${Math.round(rating.data.p25Days)} – ${Math.round(rating.data.p75Days)}`}
            />
          </div>

          {!cohort.isLoading && cohortData.length > 0 && (
            <DistributionSection
              ratingName={rating.data.name}
              cohort={cohortData}
              band={{
                hrs: [rating.data.p25Hrs, rating.data.p75Hrs],
                cost: [rating.data.p25Cost, rating.data.p75Cost],
                days: [rating.data.p25Days, rating.data.p75Days],
              }}
              median={{
                hrs: rating.data.medianHrs,
                cost: rating.data.medianCost,
                days: rating.data.medianDays,
              }}
              overlayName={overlayPt?.name ?? null}
            />
          )}
        </>
      ) : (
        <div className="card">
          <div className="empty">
            <div className="empty-title">No data for {selected}</div>
            <div className="empty-sub">No checkride milestones recorded yet.</div>
          </div>
        </div>
      )}
    </div>
  );
}

function DistributionSection({
  ratingName,
  cohort,
  band,
  median,
  overlayName,
}: {
  ratingName: string;
  cohort: RatingCohortMember[];
  band: { hrs: [number, number]; cost: [number, number]; days: [number, number] };
  median: { hrs: number; cost: number; days: number };
  overlayName: string | null;
}) {
  return (
    <>
      <div className="section-head">
        <h2 className="section-title">
          Distribution
          {overlayName && (
            <>
              {' '}
              vs{' '}
              <span style={{ color: 'var(--accent-strong)' }}>{overlayName}</span>
            </>
          )}
        </h2>
        <div className="muted tiny">
          <span className="legend-swatch band" />
          band = P25–P75
          <span className="legend-swatch med" />
          dotted = median
        </div>
      </div>

      <div className="card chart-card">
        <div className="card-head">
          <div>
            <div className="card-title">{ratingName} — flight hours</div>
            <div className="card-sub">{cohort.length} cohort members</div>
          </div>
        </div>
        <div className="card-body">
          <ScatterStrip
            points={cohort.map((p) => ({ student: p.name, value: p.hours }))}
            band={{ low: band.hrs[0], high: band.hrs[1] }}
            median={median.hrs}
            highlightName={overlayName}
            yLabel="Hours"
            fmt={(v) => v.toFixed(1)}
          />
        </div>
      </div>

      <div className="card chart-card">
        <div className="card-head">
          <div>
            <div className="card-title">Total cost</div>
            <div className="card-sub">Per-rating spend, USD</div>
          </div>
        </div>
        <div className="card-body">
          <ScatterStrip
            points={cohort.map((p) => ({ student: p.name, value: p.cost }))}
            band={{ low: band.cost[0], high: band.cost[1] }}
            median={median.cost}
            highlightName={overlayName}
            yLabel="USD"
            fmt={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Math.round(v)}`)}
          />
        </div>
      </div>

      <div className="card chart-card">
        <div className="card-head">
          <div>
            <div className="card-title">Calendar days</div>
            <div className="card-sub">Days from start to checkride</div>
          </div>
        </div>
        <div className="card-body">
          <ScatterStrip
            points={cohort.map((p) => ({ student: p.name, value: p.days }))}
            band={{ low: band.days[0], high: band.days[1] }}
            median={median.days}
            highlightName={overlayName}
            yLabel="Days"
            fmt={(v) => Math.round(v).toLocaleString()}
          />
        </div>
      </div>

      <CohortTable cohort={cohort} median={median} overlayName={overlayName} />
    </>
  );
}

function CohortTable({
  cohort,
  median,
  overlayName,
}: {
  cohort: RatingCohortMember[];
  median: { hrs: number; cost: number; days: number };
  overlayName: string | null;
}) {
  const sorted = [...cohort].sort((a, b) => {
    if (a.name === overlayName) return -1;
    if (b.name === overlayName) return 1;
    return a.hours - b.hours;
  });

  return (
    <>
      <div className="section-head">
        <h2 className="section-title">Cohort</h2>
      </div>
      <div className="card table-card">
        <div className="table-wrap" style={{ maxHeight: 360 }}>
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: '32%' }}>Student</th>
                <th className="num" style={{ width: '20%' }}>
                  Hours
                </th>
                <th className="num" style={{ width: '24%' }}>
                  Cost
                </th>
                <th className="num" style={{ width: '24%' }}>
                  Days
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((p) => {
                const isOverlay = p.name === overlayName;
                const hrsDelta = +(p.hours - median.hrs).toFixed(1);
                return (
                  <tr key={p.studentId} className={isOverlay ? 'row-highlight' : ''}>
                    <td>
                      <div className="path-cell">
                        <span className="client-avatar">
                          {p.name
                            .split(' ')
                            .map((s) => s[0])
                            .slice(0, 2)
                            .join('')}
                        </span>
                        <span>{p.name}</span>
                        {isOverlay && (
                          <span className="overlay-pin">overlay</span>
                        )}
                      </div>
                    </td>
                    <td className="num">
                      {p.hours.toFixed(1)}
                      <span className="muted tiny" style={{ marginLeft: 6 }}>
                        {hrsDelta > 0 ? '+' : ''}
                        {hrsDelta}
                      </span>
                    </td>
                    <td className="num">{fmtCost(p.cost)}</td>
                    <td className="num">{p.days}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 4: Run the route tests**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend"
npx vitest run src/routes/RatingDetail.test.tsx
```
Expected: all 4 tests pass.

- [ ] **Step 5: Run the full vitest suite**

```bash
npx vitest run
```
Expected: all green. Pay attention to any existing tests that reference `"Private Pilot"` as the h1 — if any exist they will need updating to `"Rating detail"`.

- [ ] **Step 6: TypeScript check**

```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 7: Build**

```bash
npm run build
```
Expected: clean build, no warnings about missing imports.

- [ ] **Step 8: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/routes/RatingDetail.tsx \
        frontend/src/routes/RatingDetail.test.tsx
git commit -m "feat: flesh out Rating Detail — scatter charts, overlay student, cohort table"
```

---

## Self-Review Checklist

- [x] Backend endpoint returns sorted-by-hours list: covered in Task 1 Step 3 SQL `ORDER BY m.cumulative_hours`
- [x] BigKpi overlay prop: already implemented in `BigKpi.tsx` and CSS — no task needed
- [x] Select `allowClear`: already implemented in `Select.tsx` — no task needed
- [x] CSS classes (`legend-swatch`, `row-highlight`, `overlay-pin`): already in `styles.css` — no task needed
- [x] Empty cohort state: `studentOpts` is empty → Select renders `"—"` placeholder; `cohortData.length > 0` guard hides distribution section
- [x] Rating change clears overlay: handled in `Select onChange` with `setOverlayId(null)`
- [x] `DeltaText` fmt receives `Math.abs` value: confirmed from DeltaText source — it applies sign itself; `fmt` gets `Math.abs(value)`; cost formatter passes `Math.round(v).toLocaleString()` (already absolute)
- [x] Type consistency: `RatingCohortMember` defined once in types.ts, imported in client.ts and RatingDetail.tsx
