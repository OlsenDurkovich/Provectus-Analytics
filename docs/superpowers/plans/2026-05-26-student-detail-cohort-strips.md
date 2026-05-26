# Student Detail — Cohort Distribution Strips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add mini scatter-strip charts inside each per-rating block on the Student Detail page, showing where the viewed student sits in the cohort distribution for hours / cost / days. Reuses the `ScatterStrip` component shipped last session with a new `size="mini"` variant; backend unchanged.

**Architecture:** Extend `ScatterStrip` with `size` and `highlightInProgress` props (defaults preserve Rating Detail behavior). Add a `useRatingCohorts(codes)` hook that fans out via React Query `useQueries` so each rating's cohort is cached individually. `Student.tsx` calls the hook with the student's rating codes, passes each cohort query result down to its `RatingBlock`, and the block renders three mini strips. If the student is not in the cohort (still in progress), inject a synthetic point with an in-progress visual marker.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, React Testing Library, React Query 5, React Router 6. Existing CSS variables (`--accent`, `--warn`, `--bg-elev-2`, etc.) — no new CSS files.

**Spec:** `docs/superpowers/specs/2026-05-26-student-detail-cohort-distribution-design.md`

**Branch:** `feat/student-detail-cohort-strips` (already cut)

---

## File map

- Modify: `frontend/src/components/charts/ScatterStrip.tsx` — add `size` and `highlightInProgress` props
- Create: `frontend/src/components/charts/ScatterStrip.test.tsx` — unit tests for the new variant
- Modify: `frontend/src/data/queries.ts` — add `useRatingCohorts(codes)` hook
- Modify: `frontend/src/routes/Student.tsx` — fetch cohorts, pass to `RatingBlock`, render strips
- Modify: `frontend/src/routes/Student.test.tsx` — integration tests for cohort-driven strips

---

## Task 1: Add `size` prop to ScatterStrip (mini variant)

**Files:**
- Modify: `frontend/src/components/charts/ScatterStrip.tsx` (lines 8-26 props + body)
- Create: `frontend/src/components/charts/ScatterStrip.test.tsx`

- [ ] **Step 1.1: Write the failing test**

Create `frontend/src/components/charts/ScatterStrip.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { test, expect } from 'vitest';
import { ScatterStrip } from './ScatterStrip';

const POINTS = [
  { student: 'Alice', value: 60 },
  { student: 'Bob', value: 65 },
];
const BAND = { low: 58, high: 66 };
const MEDIAN = 62;

test('renders full variant by default', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const svg = container.querySelector('svg');
  expect(svg).toBeTruthy();
  expect(svg!.getAttribute('height')).toBe('280');
});

test('mini variant renders at smaller height', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      size="mini"
    />,
  );
  const svg = container.querySelector('svg');
  expect(svg).toBeTruthy();
  expect(Number(svg!.getAttribute('height'))).toBeLessThan(80);
});

test('mini variant hides Y-axis label', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      size="mini"
    />,
  );
  const yLabel = Array.from(container.querySelectorAll('text')).find(
    (t) => t.textContent === 'Hours',
  );
  expect(yLabel).toBeUndefined();
});

test('full variant shows Y-axis label', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const yLabel = Array.from(container.querySelectorAll('text')).find(
    (t) => t.textContent === 'Hours',
  );
  expect(yLabel).toBeTruthy();
});

test('mini variant renders 2 y-axis ticks instead of 5', () => {
  const { container: fullC } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const { container: miniC } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      size="mini"
    />,
  );
  // Each tick is rendered as a horizontal grid line (line elements with stroke="var(--grid)").
  const fullGridLines = fullC.querySelectorAll('line[stroke="var(--grid)"]');
  const miniGridLines = miniC.querySelectorAll('line[stroke="var(--grid)"]');
  expect(fullGridLines.length).toBe(5);
  expect(miniGridLines.length).toBe(2);
});
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/charts/ScatterStrip.test.tsx`
Expected: 3 of 5 tests fail. `renders full variant by default` passes (height 280 already matches), `full variant shows Y-axis label` passes. The three mini tests fail because `size` prop is not accepted (TypeScript error).

- [ ] **Step 1.3: Add `size` prop to ScatterStrip**

In `frontend/src/components/charts/ScatterStrip.tsx`, update the `Props` interface and component to accept `size`:

```tsx
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
  size?: 'full' | 'mini';
}

export function ScatterStrip({
  points,
  band,
  median,
  highlightName,
  yLabel,
  fmt,
  height,
  size = 'full',
}: Props) {
  const mini = size === 'mini';
  const resolvedHeight = height ?? (mini ? 64 : 280);

  const ref = useRef<HTMLDivElement | null>(null);
  const [w, setW] = useState(800);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const padL = mini ? 36 : 56;
  const padR = mini ? 8 : 16;
  const padT = mini ? 8 : 18;
  const padB = mini ? 8 : 16;
  const innerW = Math.max(10, w - padL - padR);
  const innerH = resolvedHeight - padT - padB;
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

  const tickCount = mini ? 2 : 5;
  const ticks = Array.from({ length: tickCount }, (_, i) =>
    tickCount === 1 ? yMin : yMin + (ySpan * i) / (tickCount - 1),
  );

  const dotR = mini ? 3 : 5;
  const dotRHighlight = mini ? 4 : 7;
  const tickFont = mini ? 9 : 10.5;

  return (
    <div ref={ref} className="timechart">
      <svg
        width={w}
        height={resolvedHeight}
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
              x={padL - 6}
              y={yAt(t) + 3}
              textAnchor="end"
              fontSize={tickFont}
              fill="var(--fg-dim)"
              fontFamily="'Geist Mono', monospace"
            >
              {fmt(t)}
            </text>
          </g>
        ))}

        {/* Y-axis label (full only) */}
        {!mini && (
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
        )}

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
                r={isHighlighted ? dotRHighlight : dotR}
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
            const tipW = mini ? 124 : 152;
            const tipH = mini ? 36 : 44;
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
                  y={ty + (mini ? 14 : 17)}
                  fontSize={mini ? 10 : 11}
                  fill="var(--fg)"
                  fontWeight="500"
                >
                  {p.student}
                </text>
                <text
                  x={tx + 10}
                  y={ty + (mini ? 27 : 33)}
                  fontSize={mini ? 10 : 11}
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

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/charts/ScatterStrip.test.tsx`
Expected: All 5 tests pass.

- [ ] **Step 1.5: Run Rating Detail tests to verify no regression**

Run: `cd frontend && npx vitest run src/routes/RatingDetail.test.tsx`
Expected: All existing Rating Detail tests still pass (size defaults to "full").

- [ ] **Step 1.6: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/components/charts/ScatterStrip.tsx frontend/src/components/charts/ScatterStrip.test.tsx
git commit -m "$(cat <<'EOF'
feat(scatter-strip): add mini size variant

Adds size="full" | "mini" prop (default full, preserves Rating Detail).
Mini variant renders at 64px height with 2 axis ticks, no Y-axis label,
smaller dots and tooltips for use inside per-rating blocks.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add `highlightInProgress` prop to ScatterStrip

**Files:**
- Modify: `frontend/src/components/charts/ScatterStrip.tsx`
- Modify: `frontend/src/components/charts/ScatterStrip.test.tsx`

- [ ] **Step 2.1: Add the failing tests**

Append to `frontend/src/components/charts/ScatterStrip.test.tsx`:

```tsx
import { fireEvent } from '@testing-library/react';

test('highlighted dot uses accent color by default', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName="Alice"
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const accentCircle = Array.from(container.querySelectorAll('circle')).find(
    (c) => c.getAttribute('fill') === 'var(--accent)',
  );
  expect(accentCircle).toBeTruthy();
});

test('highlightInProgress swaps highlighted dot fill to warn color', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName="Alice"
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      highlightInProgress
    />,
  );
  const warnCircle = Array.from(container.querySelectorAll('circle')).find(
    (c) => c.getAttribute('fill') === 'var(--warn)',
  );
  expect(warnCircle).toBeTruthy();
  // No accent-filled circle should remain for highlighted dot.
  const accentCircle = Array.from(container.querySelectorAll('circle')).find(
    (c) =>
      c.getAttribute('fill') === 'var(--accent)' &&
      c.getAttribute('r') === '7',
  );
  expect(accentCircle).toBeFalsy();
});

test('tooltip on in-progress highlighted dot suffixes "(in progress)"', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName="Alice"
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      highlightInProgress
    />,
  );
  const aliceGroup = Array.from(container.querySelectorAll('g')).find((g) =>
    Array.from(g.querySelectorAll('circle')).some(
      (c) => c.getAttribute('fill') === 'var(--warn)',
    ),
  );
  expect(aliceGroup).toBeTruthy();
  fireEvent.mouseEnter(aliceGroup!);
  const tooltipText = Array.from(container.querySelectorAll('text')).find((t) =>
    (t.textContent ?? '').includes('(in progress)'),
  );
  expect(tooltipText).toBeTruthy();
});
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/charts/ScatterStrip.test.tsx`
Expected: 2 of 3 new tests fail (the default-accent test passes already). The two `highlightInProgress` tests fail because the prop is not accepted.

- [ ] **Step 2.3: Add `highlightInProgress` prop**

In `frontend/src/components/charts/ScatterStrip.tsx`:

Add to the `Props` interface (after `size`):

```tsx
  size?: 'full' | 'mini';
  highlightInProgress?: boolean;
```

Add to the destructured props (after `size = 'full'`):

```tsx
  size = 'full',
  highlightInProgress = false,
```

Update the dot fill / stroke logic inside the points loop:

```tsx
        {/* Dots */}
        {points.map((p, i) => {
          const isHighlighted = p.student === highlightName;
          const inProgress = isHighlighted && highlightInProgress;
          const cx = xAt(i);
          const cy = yAt(p.value);
          return (
            <g key={i} onMouseEnter={() => setHovered(i)}>
              <circle
                cx={cx}
                cy={cy}
                r={isHighlighted ? dotRHighlight : dotR}
                fill={
                  inProgress
                    ? 'var(--warn)'
                    : isHighlighted
                      ? 'var(--accent)'
                      : 'var(--fg-dim)'
                }
                fillOpacity={isHighlighted ? 1 : 0.5}
                stroke={isHighlighted ? 'var(--bg)' : 'none'}
                strokeWidth="1.5"
              />
            </g>
          );
        })}
```

Update the tooltip name text to append "(in progress)" when applicable. Replace the existing tooltip name `<text>` element with:

```tsx
                <text
                  x={tx + 10}
                  y={ty + (mini ? 14 : 17)}
                  fontSize={mini ? 10 : 11}
                  fill="var(--fg)"
                  fontWeight="500"
                >
                  {p.student === highlightName && highlightInProgress
                    ? `${p.student} (in progress)`
                    : p.student}
                </text>
```

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/charts/ScatterStrip.test.tsx`
Expected: All 8 tests pass.

- [ ] **Step 2.5: Run Rating Detail tests to confirm no regression**

Run: `cd frontend && npx vitest run src/routes/RatingDetail.test.tsx`
Expected: All Rating Detail tests still pass (`highlightInProgress` defaults to `false`).

- [ ] **Step 2.6: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/components/charts/ScatterStrip.tsx frontend/src/components/charts/ScatterStrip.test.tsx
git commit -m "$(cat <<'EOF'
feat(scatter-strip): add highlightInProgress prop

When true, the highlighted dot renders with var(--warn) fill and the
tooltip suffixes "(in progress)". Defaults to false so Rating Detail
behavior is unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add `useRatingCohorts` hook

**Files:**
- Modify: `frontend/src/data/queries.ts`

- [ ] **Step 3.1: Add the failing test**

Create `frontend/src/data/queries.test.tsx`:

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, beforeEach, afterEach } from 'vitest';
import { useRatingCohorts } from './queries';
import type { RatingCode } from './types';

const origFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/api/ratings/PPL/cohort')) {
      return Promise.resolve({
        ok: true,
        json: async () => [
          { studentId: '1', name: 'Alice', hours: 60, cost: 15000, days: 380 },
        ],
      });
    }
    if (url.includes('/api/ratings/IFR/cohort')) {
      return Promise.resolve({
        ok: true,
        json: async () => [
          { studentId: '2', name: 'Bob', hours: 50, cost: 12000, days: 300 },
        ],
      });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
});

afterEach(() => {
  globalThis.fetch = origFetch;
});

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

test('useRatingCohorts fans out to one query per code', async () => {
  const codes: RatingCode[] = ['PPL', 'IFR'];
  const { result } = renderHook(() => useRatingCohorts(codes), { wrapper: wrapper() });

  await waitFor(() => {
    expect(result.current.get('PPL')?.data).toBeTruthy();
    expect(result.current.get('IFR')?.data).toBeTruthy();
  });
  expect(result.current.get('PPL')!.data!.length).toBe(1);
  expect(result.current.get('PPL')!.data![0].name).toBe('Alice');
  expect(result.current.get('IFR')!.data![0].name).toBe('Bob');
});

test('useRatingCohorts returns empty map for empty codes', () => {
  const { result } = renderHook(() => useRatingCohorts([]), { wrapper: wrapper() });
  expect(result.current.size).toBe(0);
});
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/data/queries.test.tsx`
Expected: Both tests fail because `useRatingCohorts` is not exported.

- [ ] **Step 3.3: Add the hook**

In `frontend/src/data/queries.ts`, change the React Query import and add the hook.

Replace line 1:

```tsx
import { useQueries, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryResult } from '@tanstack/react-query';
```

Also update the type-only import line for types. The file already imports `RatingCode`; add `RatingCohortMember` to the import:

```tsx
import { client } from './client';
import type {
  RangeKey,
  MetricKey,
  RatingCode,
  RatingCohortMember,
  FlightUpdate,
} from './types';
```

Add the new hook below `useRatingCohort` (around line 45):

```tsx
export const useRatingCohorts = (
  codes: RatingCode[],
): Map<RatingCode, UseQueryResult<RatingCohortMember[]>> => {
  const queries = useQueries({
    queries: codes.map((code) => ({
      queryKey: queryKeys.ratingCohort(code),
      queryFn: () => client.getRatingCohort(code),
    })),
  });
  const map = new Map<RatingCode, UseQueryResult<RatingCohortMember[]>>();
  codes.forEach((code, i) => {
    map.set(code, queries[i] as UseQueryResult<RatingCohortMember[]>);
  });
  return map;
};
```

- [ ] **Step 3.4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/data/queries.test.tsx`
Expected: Both tests pass.

- [ ] **Step 3.5: Run full test suite to confirm no regression**

Run: `cd frontend && npx vitest run`
Expected: All frontend tests pass.

- [ ] **Step 3.6: TypeScript check**

Run: `cd frontend && npx tsc -b`
Expected: No errors.

- [ ] **Step 3.7: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/data/queries.ts frontend/src/data/queries.test.tsx
git commit -m "$(cat <<'EOF'
feat(queries): add useRatingCohorts hook

Fans out to one cohort fetch per rating code via useQueries. Returns
Map<RatingCode, UseQueryResult<RatingCohortMember[]>> so each entry
exposes isLoading / isError / data independently. Each rating reuses
the existing useRatingCohort cache key, so navigating between Student
Detail and Rating Detail shares cache.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Wire mini strips into Student RatingBlock — base case

**Files:**
- Modify: `frontend/src/routes/Student.tsx`
- Modify: `frontend/src/routes/Student.test.tsx`

This task covers the happy path: cohort loads, student is in the cohort (completed rating), strips render.

- [ ] **Step 4.1: Add the failing test**

In `frontend/src/routes/Student.test.tsx`, update the `beforeEach` mock to also handle the cohort endpoint, and add a test for strip rendering.

Replace the existing `beforeEach` block (lines 9-49) with:

```tsx
beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/ratings/PPL/cohort')) {
      body = [
        { studentId: 'student-1', name: 'Alex Martinez', hours: 65, cost: 15000, days: 165 },
        { studentId: 'other-1', name: 'Other A', hours: 60, cost: 14500, days: 155 },
        { studentId: 'other-2', name: 'Other B', hours: 70, cost: 16000, days: 175 },
      ];
    } else if (url.includes('/api/students/')) {
      body = {
        id: 'student-1',
        name: 'Alex Martinez',
        timeline: [
          {
            rating: 'PPL',
            start: '2024-01-01',
            end: '2024-06-15',
            milestones: [
              { name: 'first_solo', date: '2024-03-01' },
              { name: 'checkride', date: '2024-06-15' },
            ],
          },
        ],
        perRating: [
          {
            rating: 'PPL',
            name: 'Private Pilot',
            n: 12,
            hours: 65,
            cost: 15000,
            days: 165,
            medianHrs: 60,
            medianCost: 14000,
            medianDays: 150,
            lowSample: false,
          },
        ],
      };
    } else if (url.includes('/api/students')) {
      body = [
        { id: 'student-1', name: 'Alex Martinez', rating: 'PPL', progressPct: 0.9, hoursToDate: 65, daysEnrolled: 160, status: 'Completed', costToDate: 14500, instructor: 'Doug Hayes', sparkline: [2, 3, 5, 6, 8, 7, 6, 5] },
      ];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
});
```

Add a new test below the existing `shows student detail after selecting one` test:

```tsx
test('renders 3 mini scatter strips per rating block', async () => {
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Private Pilot')).toBeTruthy());
  // Wait for cohort fetch to complete (Other A appears via tooltip data — verify SVG count instead).
  await waitFor(() => {
    const svgs = container.querySelectorAll('.rating-block svg');
    expect(svgs.length).toBe(3);
  });
});
```

- [ ] **Step 4.2: Run tests to verify the new one fails**

Run: `cd frontend && npx vitest run src/routes/Student.test.tsx`
Expected: The new `renders 3 mini scatter strips per rating block` test fails (no strips yet); other tests still pass.

- [ ] **Step 4.3: Update Student.tsx — fetch cohorts and pass into RatingBlock**

In `frontend/src/routes/Student.tsx`:

Update imports at top of file:

```tsx
import { useNavigate, useParams } from 'react-router-dom';
import type { UseQueryResult } from '@tanstack/react-query';
import { BigKpi, DeltaText, MiniKpi, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import { ScatterStrip } from '../components/charts/ScatterStrip';
import { useClients, useRatingCohorts, useStudent } from '../data/queries';
import type {
  RatingCohortMember,
  StudentDetail,
  StudentPerRating,
  StudentTimelinePoint,
} from '../data/types';
```

Update `StudentBody` to fetch cohorts and pass them down:

```tsx
function StudentBody({ detail }: { detail: StudentDetail }) {
  const totals = detail.perRating.reduce(
    (acc, r) => ({
      hours: acc.hours + (r.hours ?? 0),
      cost: acc.cost + (r.cost ?? 0),
      days: acc.days + (r.days ?? 0),
    }),
    { hours: 0, cost: 0, days: 0 },
  );
  const codes = detail.timeline.map((t) => t.rating).join(', ') || '—';
  const cohortCodes = detail.perRating.map((r) => r.rating);
  const cohorts = useRatingCohorts(cohortCodes);

  return (
    <>
      <h2 className="visually-hidden">{detail.name}</h2>
      <div className="kpi-grid">
        <BigKpi label="Ratings completed" value={String(detail.timeline.length)} sub={codes} />
        <BigKpi label="Total flight hours" value={totals.hours.toFixed(1)} sub="Sum across ratings" />
        <BigKpi label="Total cost" value={fmtCost(totals.cost)} sub="Sum across ratings" />
        <BigKpi
          label="Training days"
          value={totals.days.toLocaleString()}
          sub="Sum of per-rating durations"
        />
      </div>

      {detail.timeline.length > 0 && <JourneyTimeline timeline={detail.timeline} />}

      {detail.perRating.map((r) => (
        <RatingBlock
          key={r.rating}
          r={r}
          studentId={detail.id}
          studentName={detail.name}
          cohortQuery={cohorts.get(r.rating)}
        />
      ))}
    </>
  );
}
```

Update `RatingBlock` to accept the new props and render strips. Replace the entire `RatingBlock` function (currently lines 179-239) with:

```tsx
function RatingBlock({
  r,
  studentId,
  studentName,
  cohortQuery,
}: {
  r: StudentPerRating;
  studentId: string;
  studentName: string;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
}) {
  const hours = r.hours ?? 0;
  const cost = r.cost ?? 0;
  const days = r.days ?? 0;
  const cohortHours = r.medianHrs ?? 0;
  const cohortCost = r.medianCost ?? 0;
  const cohortDays = r.medianDays ?? 0;

  return (
    <div className="rating-block">
      <div className="rating-block-head">
        <div className="rating-block-title">
          <span className="rating-chip">{r.rating}</span>
          <span className="rating-block-name">{r.name}</span>
        </div>
        <div className={`rating-block-n${r.lowSample ? ' low' : ''}`}>
          {r.lowSample ? `n=${r.n} · low sample` : `n=${r.n}`}
        </div>
      </div>
      <div className="minikpi-grid">
        <MiniKpi
          label="Hours"
          value={hours.toFixed(1)}
          deltaNode={
            <DeltaText
              value={cohortHours ? +(hours - cohortHours).toFixed(1) : 0}
              betterWhenLower
              fmt={(v) => v.toFixed(1)}
            />
          }
          sub={cohortHours ? `Cohort median: ${cohortHours.toFixed(1)}` : 'No cohort data'}
        />
        <MiniKpi
          label="Cost"
          value={fmtCost(cost)}
          deltaNode={
            <DeltaText
              value={cohortCost ? cost - cohortCost : 0}
              betterWhenLower
              fmt={(v) => fmtCost(v)}
            />
          }
          sub={cohortCost ? `Cohort median: ${fmtCost(cohortCost)}` : 'No cohort data'}
        />
        <MiniKpi
          label="Days"
          value={days.toLocaleString()}
          deltaNode={
            <DeltaText
              value={cohortDays ? days - cohortDays : 0}
              betterWhenLower
              fmt={(v) => Math.round(v).toLocaleString()}
            />
          }
          sub={cohortDays ? `Cohort median: ${Math.round(cohortDays)}` : 'No cohort data'}
        />
        <MiniKpi label="Alumni (n)" value={String(r.n)} />
      </div>
      <RatingBlockStrips
        r={r}
        studentId={studentId}
        studentName={studentName}
        cohortQuery={cohortQuery}
      />
    </div>
  );
}

function RatingBlockStrips({
  r,
  studentId,
  studentName,
  cohortQuery,
}: {
  r: StudentPerRating;
  studentId: string;
  studentName: string;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
}) {
  const cohort = cohortQuery?.data ?? [];
  const points = cohort;
  const inCohort = points.some((m) => m.studentId === studentId);

  const stripPoints = (selector: (m: RatingCohortMember) => number) =>
    points.map((m) => ({ student: m.name, value: selector(m) }));

  // Bands: derive from r.medianHrs/p25/p75 — Student API only exposes medians, not percentiles.
  // For now use min/max of cohort as a substitute band; future Task 6 may extend the API.
  const range = (selector: (m: RatingCohortMember) => number) => {
    if (points.length === 0) return { low: 0, high: 0 };
    const vals = points.map(selector).sort((a, b) => a - b);
    const q = (p: number) => vals[Math.min(vals.length - 1, Math.floor(p * (vals.length - 1)))];
    return { low: q(0.25), high: q(0.75) };
  };

  return (
    <div className="rating-block-strips">
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.hours)}
          band={range((m) => m.hours)}
          median={r.medianHrs ?? 0}
          highlightName={studentName}
          highlightInProgress={!inCohort && r.hours != null}
          yLabel="Hours"
          fmt={(v) => v.toFixed(1)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.cost)}
          band={range((m) => m.cost)}
          median={r.medianCost ?? 0}
          highlightName={studentName}
          highlightInProgress={!inCohort && r.cost != null}
          yLabel="Cost"
          fmt={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Math.round(v)}`)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.days)}
          band={range((m) => m.days)}
          median={r.medianDays ?? 0}
          highlightName={studentName}
          highlightInProgress={!inCohort && r.days != null}
          yLabel="Days"
          fmt={(v) => Math.round(v).toLocaleString()}
        />
      </div>
    </div>
  );
}
```

Note: the spec calls for percentile bands from the API, but `StudentPerRating` (`frontend/src/data/types.ts:30-40`) only exposes median fields. We derive P25/P75 client-side from the cohort points for now; this matches what the Rating Detail page exposes via the `/api/ratings/{code}` endpoint, but Student Detail does not call that endpoint. If we later want true API-sourced percentiles for Student Detail, we can either (a) call `useRating(code)` per code as well, or (b) extend `StudentPerRating` to include p25/p75 fields. For this plan, client-side percentile derivation from the cohort is acceptable and consistent with the rest of the page.

Add minimal CSS for the strip row. Append to `frontend/src/assets/styles.css` (or wherever the dashboard CSS lives — check first):

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
grep -n "rating-block" frontend/src/styles/styles.css 2>/dev/null || grep -rn "rating-block" frontend/src --include="*.css" 2>/dev/null | head -5
```

Edit the file that already defines `.rating-block` and add:

```css
.rating-block-strips {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 12px;
  padding: 0 4px;
}

.strip-cell {
  min-width: 0;
}
```

- [ ] **Step 4.4: Run Student tests to verify they pass**

Run: `cd frontend && npx vitest run src/routes/Student.test.tsx`
Expected: All 3 tests pass (existing 2 + new strip count test).

- [ ] **Step 4.5: TypeScript check**

Run: `cd frontend && npx tsc -b`
Expected: No errors.

- [ ] **Step 4.6: Visual verification in dev server**

Start the dev server and verify the strips render correctly.

Run: `cd frontend && npx vite` (or use the project's preview tooling)

Open the Student Detail page for a student with completed PPL data. Verify:
- 3 mini strips appear below the MiniKpi grid in each rating block
- The student's dot is highlighted in accent color (completed case)
- Hovering other dots shows tooltips
- Strips are aligned in a 3-column grid

- [ ] **Step 4.7: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/routes/Student.tsx frontend/src/routes/Student.test.tsx frontend/src/styles/styles.css
git commit -m "$(cat <<'EOF'
feat(student-detail): render mini scatter strips per rating block

Adds 3 mini ScatterStrip charts (hours / cost / days) below each rating
block's MiniKpi grid, showing where the student sits in the cohort
distribution. Cohorts are fetched in parallel via useRatingCohorts so
each rating's data is cached independently and reused when navigating
to Rating Detail.

P25/P75 band is derived client-side from cohort points (Student API
exposes medians only).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: In-progress student dot injection

**Files:**
- Modify: `frontend/src/routes/Student.tsx`
- Modify: `frontend/src/routes/Student.test.tsx`

When the viewed student isn't in the cohort (still working toward checkride) but has numeric data, inject them as a synthetic point and apply `highlightInProgress`.

- [ ] **Step 5.1: Add the failing test**

Append to `frontend/src/routes/Student.test.tsx`:

```tsx
test('injects student as in-progress dot when not in cohort', async () => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/ratings/IFR/cohort')) {
      body = [
        { studentId: 'other-1', name: 'Other A', hours: 45, cost: 11000, days: 120 },
        { studentId: 'other-2', name: 'Other B', hours: 55, cost: 13000, days: 140 },
      ];
    } else if (url.includes('/api/students/')) {
      body = {
        id: 'student-1',
        name: 'Alex Martinez',
        timeline: [],
        perRating: [
          {
            rating: 'IFR',
            name: 'Instrument Rating',
            n: 8,
            hours: 32, // student has hours but no checkride
            cost: 9000,
            days: 90,
            medianHrs: 50,
            medianCost: 12000,
            medianDays: 130,
            lowSample: false,
          },
        ],
      };
    } else {
      body = [];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Instrument Rating')).toBeTruthy());
  await waitFor(() => {
    const warnDot = container.querySelector('.rating-block circle[fill="var(--warn)"]');
    expect(warnDot).toBeTruthy();
  });
});

test('renders without warn dot when student is in cohort', async () => {
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Private Pilot')).toBeTruthy());
  await waitFor(() => {
    const svgs = container.querySelectorAll('.rating-block svg');
    expect(svgs.length).toBe(3);
  });
  const warnDot = container.querySelector('.rating-block circle[fill="var(--warn)"]');
  expect(warnDot).toBeNull();
});
```

- [ ] **Step 5.2: Run tests to verify the new ones fail or partially fail**

Run: `cd frontend && npx vitest run src/routes/Student.test.tsx`
Expected: The "injects student as in-progress dot" test fails because the cohort doesn't currently include the student.

- [ ] **Step 5.3: Update RatingBlockStrips to inject the student**

In `frontend/src/routes/Student.tsx`, modify the `RatingBlockStrips` function. Replace it with:

```tsx
function RatingBlockStrips({
  r,
  studentId,
  studentName,
  cohortQuery,
}: {
  r: StudentPerRating;
  studentId: string;
  studentName: string;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
}) {
  const rawCohort = cohortQuery?.data ?? [];
  const inCohort = rawCohort.some((m) => m.studentId === studentId);
  const hasStudentData = r.hours != null || r.cost != null || r.days != null;

  // Inject the student as a synthetic point if they aren't in the cohort.
  const cohort: RatingCohortMember[] = inCohort || !hasStudentData
    ? rawCohort
    : [
        ...rawCohort,
        {
          studentId,
          name: studentName,
          hours: r.hours ?? 0,
          cost: r.cost ?? 0,
          days: r.days ?? 0,
        },
      ];

  const highlightInProgress = !inCohort && hasStudentData;

  const stripPoints = (selector: (m: RatingCohortMember) => number) =>
    cohort.map((m) => ({ student: m.name, value: selector(m) }));

  const range = (selector: (m: RatingCohortMember) => number) => {
    if (cohort.length === 0) return { low: 0, high: 0 };
    const vals = cohort.map(selector).sort((a, b) => a - b);
    const q = (p: number) => vals[Math.min(vals.length - 1, Math.floor(p * (vals.length - 1)))];
    return { low: q(0.25), high: q(0.75) };
  };

  return (
    <div className="rating-block-strips">
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.hours)}
          band={range((m) => m.hours)}
          median={r.medianHrs ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Hours"
          fmt={(v) => v.toFixed(1)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.cost)}
          band={range((m) => m.cost)}
          median={r.medianCost ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Cost"
          fmt={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Math.round(v)}`)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.days)}
          band={range((m) => m.days)}
          median={r.medianDays ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Days"
          fmt={(v) => Math.round(v).toLocaleString()}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 5.4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/routes/Student.test.tsx`
Expected: All Student tests pass.

- [ ] **Step 5.5: TypeScript check**

Run: `cd frontend && npx tsc -b`
Expected: No errors.

- [ ] **Step 5.6: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/routes/Student.tsx frontend/src/routes/Student.test.tsx
git commit -m "$(cat <<'EOF'
feat(student-detail): inject in-progress student dot

When the viewed student is not in the cohort (no checkride milestone
yet) but has numeric per-rating data, inject a synthetic cohort point
with their hours/cost/days and apply highlightInProgress so the dot
renders in warn color with an "(in progress)" tooltip suffix.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Handle loading / error / low-sample edge cases

**Files:**
- Modify: `frontend/src/routes/Student.tsx`
- Modify: `frontend/src/routes/Student.test.tsx`

- [ ] **Step 6.1: Add the failing tests**

Append to `frontend/src/routes/Student.test.tsx`:

```tsx
test('renders fallback note when lowSample is true', async () => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/students/')) {
      body = {
        id: 'student-1',
        name: 'Alex Martinez',
        timeline: [],
        perRating: [
          {
            rating: 'MEI',
            name: 'Multi-Engine Instructor',
            n: 2,
            hours: 10,
            cost: 3000,
            days: 30,
            medianHrs: 12,
            medianCost: 3200,
            medianDays: 35,
            lowSample: true,
          },
        ],
      };
    } else {
      body = [];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() =>
    expect(screen.getByText('Multi-Engine Instructor')).toBeTruthy(),
  );
  expect(screen.getByText('Distribution hidden — low sample')).toBeTruthy();
  const stripSvgs = container.querySelectorAll('.rating-block-strips svg');
  expect(stripSvgs.length).toBe(0);
});

test('renders nothing in strip slot when cohort fetch errors', async () => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/cohort')) {
      return Promise.resolve({ ok: false, json: async () => ({}) });
    }
    let body: unknown = [];
    if (url.includes('/api/students/')) {
      body = {
        id: 'student-1',
        name: 'Alex Martinez',
        timeline: [],
        perRating: [
          {
            rating: 'PPL',
            name: 'Private Pilot',
            n: 12,
            hours: 65,
            cost: 15000,
            days: 165,
            medianHrs: 60,
            medianCost: 14000,
            medianDays: 150,
            lowSample: false,
          },
        ],
      };
    } else {
      body = [];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Private Pilot')).toBeTruthy());
  // Numeric MiniKpis still render
  expect(screen.getByText('Hours')).toBeTruthy();
  // Strips should be absent (error path hides strips, no skeleton lingering)
  await waitFor(() => {
    const stripSvgs = container.querySelectorAll('.rating-block-strips svg');
    expect(stripSvgs.length).toBe(0);
  });
});
```

- [ ] **Step 6.2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/routes/Student.test.tsx`
Expected: Both new tests fail (currently strips render unconditionally with empty `points` when cohort is empty/errored, and low-sample is not handled).

- [ ] **Step 6.3: Add edge-case handling to RatingBlockStrips**

In `frontend/src/routes/Student.tsx`, replace `RatingBlockStrips` with:

```tsx
function RatingBlockStrips({
  r,
  studentId,
  studentName,
  cohortQuery,
}: {
  r: StudentPerRating;
  studentId: string;
  studentName: string;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
}) {
  if (r.lowSample) {
    return (
      <div className="rating-block-strips rating-block-strips-empty muted tiny">
        Distribution hidden — low sample
      </div>
    );
  }

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
    // Silently hide strips; numeric MiniKpis above still convey value.
    return null;
  }

  const rawCohort = cohortQuery.data;
  const inCohort = rawCohort.some((m) => m.studentId === studentId);
  const hasStudentData = r.hours != null || r.cost != null || r.days != null;

  const cohort: RatingCohortMember[] = inCohort || !hasStudentData
    ? rawCohort
    : [
        ...rawCohort,
        {
          studentId,
          name: studentName,
          hours: r.hours ?? 0,
          cost: r.cost ?? 0,
          days: r.days ?? 0,
        },
      ];

  const highlightInProgress = !inCohort && hasStudentData;

  const stripPoints = (selector: (m: RatingCohortMember) => number) =>
    cohort.map((m) => ({ student: m.name, value: selector(m) }));

  const range = (selector: (m: RatingCohortMember) => number) => {
    if (cohort.length === 0) return { low: 0, high: 0 };
    const vals = cohort.map(selector).sort((a, b) => a - b);
    const q = (p: number) => vals[Math.min(vals.length - 1, Math.floor(p * (vals.length - 1)))];
    return { low: q(0.25), high: q(0.75) };
  };

  return (
    <div className="rating-block-strips">
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.hours)}
          band={range((m) => m.hours)}
          median={r.medianHrs ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Hours"
          fmt={(v) => v.toFixed(1)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.cost)}
          band={range((m) => m.cost)}
          median={r.medianCost ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Cost"
          fmt={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Math.round(v)}`)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.days)}
          band={range((m) => m.days)}
          median={r.medianDays ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Days"
          fmt={(v) => Math.round(v).toLocaleString()}
        />
      </div>
    </div>
  );
}
```

Add styling for the empty state in the same CSS file as `.rating-block-strips`:

```css
.rating-block-strips-empty {
  display: block;
  text-align: center;
  padding: 14px 8px;
  border-top: 1px dashed var(--border);
  color: var(--fg-dim);
}
```

- [ ] **Step 6.4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/routes/Student.test.tsx`
Expected: All Student tests pass.

- [ ] **Step 6.5: Run full test suite**

Run: `cd frontend && npx vitest run`
Expected: All frontend tests pass. Backend Python tests are unaffected but run them too if desired: `cd "/Users/olsend/Documents/Provectus Analytics" && python -m pytest tests`.

- [ ] **Step 6.6: TypeScript build check**

Run: `cd frontend && npx tsc -b`
Expected: No errors.

- [ ] **Step 6.7: Visual verification**

Run dev server: `cd frontend && npx vite`

Spot-check on Student Detail:
- Completed rating: 3 strips, student dot in accent color.
- In-progress rating: 3 strips, student dot in warn color, tooltip shows "(in progress)".
- Low-sample rating: "Distribution hidden — low sample" note instead of strips.
- (Force a network error or temporarily block the cohort endpoint to confirm the strips slot disappears cleanly.)

- [ ] **Step 6.8: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/routes/Student.tsx frontend/src/routes/Student.test.tsx frontend/src/styles/styles.css
git commit -m "$(cat <<'EOF'
feat(student-detail): handle loading, error, and low-sample states

- lowSample → "Distribution hidden — low sample" note
- isLoading → 3 skeleton bars in the strips slot
- isError or empty cohort → strips silently hidden (numeric MiniKpis remain)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Final verification and PR prep

**Files:** none

- [ ] **Step 7.1: Run full test suite (frontend + backend)**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend" && npx vitest run
cd "/Users/olsend/Documents/Provectus Analytics" && python -m pytest tests
```

Expected: All tests pass.

- [ ] **Step 7.2: TypeScript build**

Run: `cd frontend && npx tsc -b`
Expected: Clean.

- [ ] **Step 7.3: Lint**

Run: `cd frontend && npx eslint .`
Expected: No new errors (pre-existing warnings ok).

- [ ] **Step 7.4: Confirm Rating Detail still works visually**

Run dev server and click through to a few rating codes on Rating Detail. Verify scatter strips still render at full size, axis label visible, no in-progress dots (default behavior preserved).

- [ ] **Step 7.5: Push branch and open PR (only after user confirms)**

GitHub pushes are manual — ask the user before pushing. When approved:

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git push -u origin feat/student-detail-cohort-strips
gh pr create --title "Student Detail: cohort distribution strips" --body "$(cat <<'EOF'
## Summary
- 3 mini scatter strips per rating block on Student Detail (hours / cost / days)
- New `size="mini"` and `highlightInProgress` props on ScatterStrip; Rating Detail unchanged
- New `useRatingCohorts(codes)` hook fans out via React Query useQueries, cache-shared with Rating Detail
- In-progress student dot injection (warn color, tooltip suffix)
- Loading skeleton, low-sample fallback, error fallback all handled

Spec: docs/superpowers/specs/2026-05-26-student-detail-cohort-distribution-design.md
Plan: docs/superpowers/plans/2026-05-26-student-detail-cohort-strips.md

## Test plan
- [x] ScatterStrip unit tests (8 tests, mini + highlightInProgress)
- [x] useRatingCohorts hook test (2 tests)
- [x] Student integration tests (5 tests, base / in-progress / low-sample / error)
- [x] Rating Detail tests still green
- [x] TypeScript build clean
- [x] Visual spot-check on dev server

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-review notes

**Spec coverage:**

- Mini ScatterStrip variant → Task 1 ✓
- In-progress visual marker → Task 2 + Task 5 ✓
- `useRatingCohorts` hook → Task 3 ✓
- Strips inside RatingBlock → Task 4 ✓
- In-progress student injection → Task 5 ✓
- Edge cases (loading skeleton, lowSample, error) → Task 6 ✓
- Tests at unit/hook/integration levels → distributed across all tasks ✓
- Rating Detail regression-tested → Task 1.5, 2.5, 7.4 ✓

**Deviation from spec:** P25/P75 band is derived client-side from cohort points, not from the API. The spec implied the existing `r.p25Hrs` / `r.p75Hrs` fields would be used, but `StudentPerRating` only exposes medians (`r.medianHrs`, etc.). This deviation is called out in Task 4 step 4.3 with two future-extension options. Acceptable for this scope.

**Type consistency:** `UseQueryResult<RatingCohortMember[]>` is used consistently across queries.ts, Student.tsx, and the test mocks. `RatingCohortMember`, `StudentPerRating`, `StudentDetail` all imported from `data/types.ts`.

**No placeholders:** All steps contain executable code, exact paths, and expected output.
