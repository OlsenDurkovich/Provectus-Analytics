# Dash → React + FastAPI Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Dash app at `app.py` + `src/provectus_analytics/web/` with a Vite+React+TypeScript frontend backed by a FastAPI service that wraps the existing Python data pipeline, preserving the boss's `Provectus.command` launcher distribution model.

**Architecture:** FastAPI mounts the prebuilt React `dist/` at `/` and serves JSON at `/api/*`. The existing Python pipeline (`ingest.py`, `partition.py`, `milestones.py`, `norms.py`, etc.) is untouched; `api/adapters.py` is the only seam where pandas DataFrames are reshaped into Pydantic schemas. Dash stays runnable until the new app reaches parity, then is removed in the final phase.

**Tech Stack:** Vite + React 18 + TypeScript + `react-router-dom@6` + `@tanstack/react-query` + Vitest + React Testing Library on the frontend. FastAPI + Pydantic v2 + uvicorn + httpx + pytest on the backend. Plain CSS with custom properties (no Tailwind). Hand-rolled SVG charts (no chart library).

**Spec:** [docs/superpowers/specs/2026-05-25-dash-to-react-rewrite-design.md](../specs/2026-05-25-dash-to-react-rewrite-design.md)

**Visual source of truth:** `design_handoff_provectus_analytics/design/*.jsx` and `screenshots/`.

---

## Phase 0 — Project scaffolding

### Task 0.1: Scaffold Vite + React + TypeScript project

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`
- Modify: `.gitignore`

- [ ] **Step 1: Create frontend/ via Vite template**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

Expected: directory `frontend/` populated with Vite defaults; `node_modules/` installed.

- [ ] **Step 2: Add runtime + dev dependencies**

```bash
cd frontend
npm install react-router-dom@^6 @tanstack/react-query@^5
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @types/node
```

- [ ] **Step 3: Update .gitignore at repo root**

Append to `/Users/olsend/Documents/Provectus Analytics/.gitignore`:

```
# Frontend
frontend/node_modules/
frontend/dist/
frontend/.vite/
```

- [ ] **Step 4: Configure Vite with /api proxy + Vitest**

Replace `frontend/vite.config.ts`:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8050',
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
});
```

Create `frontend/src/test-setup.ts`:

```ts
import '@testing-library/jest-dom';
```

- [ ] **Step 5: Add minimal smoke test**

Create `frontend/src/App.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders without crashing', () => {
  render(<App />);
  expect(document.body).toBeTruthy();
});
```

- [ ] **Step 6: Run the smoke test**

```bash
cd frontend && npx vitest run
```

Expected: 1 test passes.

- [ ] **Step 7: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add .gitignore frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/src frontend/public
git commit -m "scaffold: Vite + React + TS frontend project"
```

---

### Task 0.2: Port styles.css and fonts

**Files:**
- Create: `frontend/src/styles/styles.css` (copied verbatim from `design_handoff_provectus_analytics/design/styles.css`)
- Modify: `frontend/index.html`, `frontend/src/main.tsx`

- [ ] **Step 1: Copy styles.css verbatim**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
mkdir -p frontend/src/styles
cp design_handoff_provectus_analytics/design/styles.css frontend/src/styles/styles.css
```

- [ ] **Step 2: Add Geist font links to index.html**

Replace `frontend/index.html` head section so it contains:

```html
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
```

Set `<html lang="en" data-theme="dark">` and update `<title>` to `Provectus Aviation — Analytics`.

- [ ] **Step 3: Import styles in main.tsx**

Replace `frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/styles.css';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 4: Verify dev server renders the stylesheet**

```bash
cd frontend && npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173` in a browser. Body should have the dark background `#0A0A0A`. Kill the dev server.

- [ ] **Step 5: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add frontend/src/styles frontend/index.html frontend/src/main.tsx
git commit -m "port design styles.css + Geist fonts into frontend"
```

---

### Task 0.3: Add FastAPI dependencies and create app skeleton

**Files:**
- Modify: `requirements.txt`, `pyproject.toml` (if it lists runtime deps)
- Create: `src/provectus_analytics/api/__init__.py`, `src/provectus_analytics/api/main.py`, `tests/test_api/__init__.py`, `tests/test_api/test_healthz.py`

- [ ] **Step 1: Add FastAPI deps to requirements.txt**

Read current `requirements.txt`, append:

```
fastapi>=0.111
uvicorn[standard]>=0.30
httpx>=0.27
```

If `pyproject.toml` has a `[project.dependencies]` block listing the same deps, mirror the additions there.

- [ ] **Step 2: Install in active venv**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
pip install -r requirements.txt
```

- [ ] **Step 3: Create api/ package**

Create `src/provectus_analytics/api/__init__.py`:

```python
"""FastAPI app — replaces the legacy Dash web layer.

Run dev:
    uvicorn provectus_analytics.api.main:app --reload --port 8050
"""
from .main import app, create_app

__all__ = ["app", "create_app"]
```

- [ ] **Step 4: Write failing test for /api/healthz**

Create `tests/test_api/__init__.py` (empty).

Create `tests/test_api/test_healthz.py`:

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app


def test_healthz_returns_ok():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Run test to verify it fails**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
pytest tests/test_api/test_healthz.py -v
```

Expected: FAIL with `ImportError` for `provectus_analytics.api`.

- [ ] **Step 6: Implement main.py**

Create `src/provectus_analytics/api/main.py`:

```python
"""FastAPI app factory + uvicorn entry."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="Provectus Analytics", docs_url="/api/docs", openapi_url="/api/openapi.json")

    @app.get("/api/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # Static mount is added later (Task 0.4) once frontend/dist/ is built.
    return app


app = create_app()
```

- [ ] **Step 7: Run test to verify it passes**

```bash
pytest tests/test_api/test_healthz.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
git add requirements.txt pyproject.toml src/provectus_analytics/api tests/test_api
git commit -m "scaffold: FastAPI app skeleton with /api/healthz"
```

---

### Task 0.4: Mount frontend/dist/ as static files

**Files:**
- Modify: `src/provectus_analytics/api/main.py`
- Modify: `tests/test_api/test_healthz.py` (add static-mount test)

- [ ] **Step 1: Build the frontend once so dist/ exists**

```bash
cd "/Users/olsend/Documents/Provectus Analytics/frontend" && npm run build
```

Expected: `frontend/dist/index.html` and `frontend/dist/assets/*` created.

- [ ] **Step 2: Write failing test for static mount**

Append to `tests/test_api/test_healthz.py`:

```python
def test_root_serves_frontend_index():
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "<div id=\"root\"></div>" in response.text
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_api/test_healthz.py::test_root_serves_frontend_index -v
```

Expected: FAIL (404 — no route).

- [ ] **Step 4: Add StaticFiles mount in main.py**

Modify `src/provectus_analytics/api/main.py` `create_app`:

```python
from fastapi.staticfiles import StaticFiles

def create_app() -> FastAPI:
    app = FastAPI(...)

    @app.get("/api/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app
```

- [ ] **Step 5: Verify test passes**

```bash
pytest tests/test_api/test_healthz.py -v
```

Expected: both tests pass.

- [ ] **Step 6: Smoke test end-to-end**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
uvicorn provectus_analytics.api.main:app --port 8050 &
sleep 2
curl -sf http://127.0.0.1:8050/api/healthz
curl -sf http://127.0.0.1:8050/ | grep -c 'id="root"'
kill %1
```

Expected: `{"status":"ok"}` then `1`.

- [ ] **Step 7: Commit**

```bash
git add src/provectus_analytics/api/main.py tests/test_api/test_healthz.py
git commit -m "wire: FastAPI mounts frontend/dist at /"
```

---

## Phase 1 — Shared contracts (schemas + types)

### Task 1.1: Define Pydantic schemas

**Files:**
- Create: `src/provectus_analytics/api/schemas.py`
- Create: `tests/test_api/test_schemas.py`

- [ ] **Step 1: Write failing tests for core schemas**

Create `tests/test_api/test_schemas.py`:

```python
from provectus_analytics.api import schemas


def test_kpi_roundtrip():
    kpi = schemas.Kpi(
        key="ratings_completed", label="Ratings completed", value="42",
        sub="last 12 months", delta=0.12, positive=True, spark=[1, 2, 3],
        color="#6E56F8",
    )
    assert kpi.model_dump()["positive"] is True


def test_client_row_status_enum():
    row = schemas.ClientRow(
        id="c1", name="Alex Doe", rating="PPL", progressPct=0.5,
        hoursToDate=42.3, daysEnrolled=120, status="Active",
    )
    assert row.rating == "PPL"


def test_flight_row_billing_enum_rejects_invalid():
    import pydantic
    try:
        schemas.FlightRow(
            id="f1", date="2026-01-01", client="A", instructor="B", type="Dual",
            billing="INVALID", acClass="SE_BASIC", ground="Flight (0)", hours=1, cost=100,
        )
    except pydantic.ValidationError:
        return
    raise AssertionError("expected ValidationError for billing='INVALID'")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_api/test_schemas.py -v
```

Expected: FAIL with `ImportError` (no `schemas` module).

- [ ] **Step 3: Implement schemas.py**

Create `src/provectus_analytics/api/schemas.py`:

```python
"""Pydantic schemas — the wire contract for /api/*.

Mirrors frontend/src/data/types.ts. Any change here MUST be reflected there.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RatingCode = Literal["PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"]
RangeKey = Literal["30d", "90d", "6mo", "12mo", "ytd", "all"]
MetricKey = Literal["hours", "cost", "days"]
FlightStatus = Literal["Active", "On checkride", "Completed"]
BillingKind = Literal["Hobbs", "Tach", "Block", "—"]
AcClass = Literal["SE_BASIC", "SE_COMPLEX", "ME_BASIC", "HP_COMPLEX"]
GroundFlag = Literal["Flight (0)", "Ground (1)"]
OverridableField = Literal[
    "is_ground_lesson", "billing_category", "aircraft_class", "reservation_type"
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


class StudentTimelinePoint(BaseModel):
    rating: RatingCode
    start: str
    end: str | None
    milestones: list[dict]


class StudentDetail(BaseModel):
    id: str
    name: str
    timeline: list[StudentTimelinePoint]
    perRating: list[dict]


class InstructorSummary(BaseModel):
    id: str
    name: str
    hours: float
    students: int
    passRate: float


class InstructorDetail(BaseModel):
    id: str
    name: str
    students: list[ClientRow]
    perRating: list[dict]


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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_api/test_schemas.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/provectus_analytics/api/schemas.py tests/test_api/test_schemas.py
git commit -m "define: Pydantic v2 schemas for /api/* contract"
```

---

### Task 1.2: Define TypeScript types mirroring schemas

**Files:**
- Create: `frontend/src/data/types.ts`

- [ ] **Step 1: Create types.ts**

Create `frontend/src/data/types.ts`:

```ts
export type RatingCode = 'PPL' | 'IFR' | 'COM' | 'AMEL' | 'CFI' | 'CFII' | 'MEI';
export type RangeKey = '30d' | '90d' | '6mo' | '12mo' | 'ytd' | 'all';
export type MetricKey = 'hours' | 'cost' | 'days';
export type ThemeKey = 'dark' | 'light';
export type TabKey = 'overview' | 'rating' | 'student' | 'instructor' | 'flights';
export type FlightStatus = 'Active' | 'On checkride' | 'Completed';
export type BillingKind = 'Hobbs' | 'Tach' | 'Block' | '—';
export type AcClass = 'SE_BASIC' | 'SE_COMPLEX' | 'ME_BASIC' | 'HP_COMPLEX';
export type GroundFlag = 'Flight (0)' | 'Ground (1)';
export type OverridableField =
  | 'is_ground_lesson'
  | 'billing_category'
  | 'aircraft_class'
  | 'reservation_type';

export interface Kpi {
  key: string;
  label: string;
  value: string;
  sub: string;
  delta: number;
  positive: boolean;
  spark: number[];
  color: string;
}

export interface Rating {
  code: RatingCode;
  name: string;
  n: number;
  medianHrs: number; p25Hrs: number; p75Hrs: number;
  medianCost: number; p25Cost: number; p75Cost: number;
  medianDays: number; p25Days: number; p75Days: number;
  lowSample?: boolean;
}

export interface RatingBarPoint {
  code: RatingCode;
  name: string;
  n: number;
  median: number;
  p25: number;
  p75: number;
}

export interface RatingsCompletedRow {
  rating: RatingCode;
  count: number;
}

export interface Heatmap {
  rows: number[][];
  buckets: string[];
}

export interface ClientRow {
  id: string;
  name: string;
  rating: RatingCode;
  progressPct: number;
  hoursToDate: number;
  daysEnrolled: number;
  status: FlightStatus;
}

export interface StudentTimelinePoint {
  rating: RatingCode;
  start: string;
  end: string | null;
  milestones: Array<{ name: string; date: string }>;
}

export interface StudentDetail {
  id: string;
  name: string;
  timeline: StudentTimelinePoint[];
  perRating: Array<Record<string, unknown>>;
}

export interface InstructorSummary {
  id: string;
  name: string;
  hours: number;
  students: number;
  passRate: number;
}

export interface InstructorDetail {
  id: string;
  name: string;
  students: ClientRow[];
  perRating: Array<Record<string, unknown>>;
}

export interface FlightRow {
  id: string;
  date: string;
  client: string;
  instructor: string;
  type: string;
  billing: BillingKind;
  acClass: AcClass;
  ground: GroundFlag;
  hours: number;
  cost: number;
}

export interface FlightUpdate {
  field: OverridableField;
  value: string | boolean | null;
}

export interface DataState {
  flights: number;
  invoices: number;
  students: number;
  surveys: number;
  overrides: number;
}

export interface Meta {
  mode: 'real' | 'synthetic';
  liveClientCount: number;
  dataState: DataState;
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/data/types.ts
git commit -m "define: TS types mirroring Pydantic schemas"
```

---

### Task 1.3: Wire frontend API client + React Query provider

**Files:**
- Create: `frontend/src/data/client.ts`, `frontend/src/data/queries.ts`, `frontend/src/data/client.test.ts`
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx`

- [ ] **Step 1: Write failing test for client**

Create `frontend/src/data/client.test.ts`:

```ts
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { client, ApiError } from './client';

describe('client', () => {
  const origFetch = global.fetch;
  beforeEach(() => { global.fetch = vi.fn(); });
  afterEach(() => { global.fetch = origFetch; });

  test('getMeta hits /api/meta and returns parsed JSON', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ mode: 'synthetic', liveClientCount: 0, dataState: { flights: 0, invoices: 0, students: 0, surveys: 0, overrides: 0 } }),
    });
    const meta = await client.getMeta();
    expect(meta.mode).toBe('synthetic');
    expect(global.fetch).toHaveBeenCalledWith('/api/meta', expect.anything());
  });

  test('throws ApiError on non-2xx', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false, status: 500, text: async () => 'boom',
    });
    await expect(client.getMeta()).rejects.toBeInstanceOf(ApiError);
  });
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npx vitest run src/data/client.test.ts
```

Expected: FAIL (no `./client` module).

- [ ] **Step 3: Implement client.ts**

Create `frontend/src/data/client.ts`:

```ts
import type {
  Meta, Kpi, RatingBarPoint, RatingsCompletedRow, Heatmap,
  ClientRow, StudentDetail, InstructorSummary, InstructorDetail,
  FlightRow, FlightUpdate, RangeKey, MetricKey, RatingCode, Rating,
} from './types';

export class ApiError extends Error {
  constructor(public status: number, public body: string, message?: string) {
    super(message ?? `API error ${status}: ${body}`);
  }
}

async function get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const qs = params
    ? '?' + new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined) as [string, string][]
      ).toString()
    : '';
  const res = await fetch(path + qs, { headers: { 'Accept': 'application/json' } });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json() as Promise<T>;
}

export const client = {
  getMeta: () => get<Meta>('/api/meta'),
  getKpis: (range: RangeKey) => get<Kpi[]>('/api/kpis', { range }),
  getRatingBars: (metric: MetricKey, range: RangeKey) =>
    get<RatingBarPoint[]>('/api/ratings', { metric, range }),
  getRating: (code: RatingCode, range: RangeKey) =>
    get<Rating>(`/api/ratings/${code}`, { range }),
  getRatingsCompleted: (range: RangeKey) =>
    get<RatingsCompletedRow[]>('/api/ratings/completed', { range }),
  getHeatmap: (range: RangeKey) => get<Heatmap>('/api/heatmap', { range }),
  getClients: (range: RangeKey, rating?: RatingCode) =>
    get<ClientRow[]>('/api/students', { range, rating }),
  getStudent: (id: string) => get<StudentDetail>(`/api/students/${id}`),
  getInstructors: () => get<InstructorSummary[]>('/api/instructors'),
  getInstructor: (id: string) => get<InstructorDetail>(`/api/instructors/${id}`),
  getFlights: (filter: { instructor?: string; client?: string; ground?: string; sort?: string }) =>
    get<FlightRow[]>('/api/flights', filter),
  updateFlight: (id: string, patchBody: FlightUpdate) =>
    patch<FlightRow>(`/api/flights/${id}`, patchBody),
  importFsp: () => post<{ imported: unknown; built: unknown }>('/api/import-fsp'),
  rebuild: (synthetic = false) =>
    post<{ built: unknown }>(`/api/rebuild${synthetic ? '?synthetic=true' : ''}`),
};

export type Client = typeof client;
```

- [ ] **Step 4: Run client tests to verify pass**

```bash
cd frontend && npx vitest run src/data/client.test.ts
```

Expected: 2 tests pass.

- [ ] **Step 5: Create queries.ts (React Query hooks)**

Create `frontend/src/data/queries.ts`:

```ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { client } from './client';
import type { RangeKey, MetricKey, RatingCode, FlightUpdate } from './types';

export const queryKeys = {
  meta: ['meta'] as const,
  kpis: (range: RangeKey) => ['kpis', range] as const,
  ratingBars: (metric: MetricKey, range: RangeKey) => ['ratingBars', metric, range] as const,
  rating: (code: RatingCode, range: RangeKey) => ['rating', code, range] as const,
  ratingsCompleted: (range: RangeKey) => ['ratingsCompleted', range] as const,
  heatmap: (range: RangeKey) => ['heatmap', range] as const,
  clients: (range: RangeKey, rating?: RatingCode) => ['clients', range, rating] as const,
  student: (id: string) => ['student', id] as const,
  instructors: ['instructors'] as const,
  instructor: (id: string) => ['instructor', id] as const,
  flights: (filter: object) => ['flights', filter] as const,
};

export const useMeta = () => useQuery({ queryKey: queryKeys.meta, queryFn: client.getMeta });

export const useKpis = (range: RangeKey) =>
  useQuery({ queryKey: queryKeys.kpis(range), queryFn: () => client.getKpis(range) });

export const useRatingBars = (metric: MetricKey, range: RangeKey) =>
  useQuery({ queryKey: queryKeys.ratingBars(metric, range), queryFn: () => client.getRatingBars(metric, range) });

export const useRating = (code: RatingCode | undefined, range: RangeKey) =>
  useQuery({
    queryKey: queryKeys.rating(code!, range),
    queryFn: () => client.getRating(code!, range),
    enabled: !!code,
  });

export const useRatingsCompleted = (range: RangeKey) =>
  useQuery({ queryKey: queryKeys.ratingsCompleted(range), queryFn: () => client.getRatingsCompleted(range) });

export const useHeatmap = (range: RangeKey) =>
  useQuery({ queryKey: queryKeys.heatmap(range), queryFn: () => client.getHeatmap(range) });

export const useClients = (range: RangeKey, rating?: RatingCode) =>
  useQuery({ queryKey: queryKeys.clients(range, rating), queryFn: () => client.getClients(range, rating) });

export const useStudent = (id: string | undefined) =>
  useQuery({ queryKey: queryKeys.student(id!), queryFn: () => client.getStudent(id!), enabled: !!id });

export const useInstructors = () =>
  useQuery({ queryKey: queryKeys.instructors, queryFn: client.getInstructors });

export const useInstructor = (id: string | undefined) =>
  useQuery({ queryKey: queryKeys.instructor(id!), queryFn: () => client.getInstructor(id!), enabled: !!id });

export const useFlights = (filter: { instructor?: string; client?: string; ground?: string; sort?: string }) =>
  useQuery({ queryKey: queryKeys.flights(filter), queryFn: () => client.getFlights(filter) });

export const useUpdateFlight = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: FlightUpdate }) => client.updateFlight(id, patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['flights'] });
      qc.invalidateQueries({ queryKey: ['student'] });
      qc.invalidateQueries({ queryKey: ['kpis'] });
      qc.invalidateQueries({ queryKey: ['ratingBars'] });
    },
  });
};

export const useImportFsp = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: client.importFsp,
    onSuccess: () => qc.invalidateQueries(),
  });
};

export const useRebuild = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ synthetic }: { synthetic: boolean }) => client.rebuild(synthetic),
    onSuccess: () => qc.invalidateQueries(),
  });
};
```

- [ ] **Step 6: Wrap App with QueryClientProvider**

Replace `frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './styles/styles.css';
import App from './App';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>
);
```

- [ ] **Step 7: Type-check + tests**

```bash
cd frontend && npx tsc --noEmit && npx vitest run
```

Expected: no TS errors, all tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/data frontend/src/main.tsx
git commit -m "wire: API client + React Query hooks + provider"
```

---

## Phase 2 — /api/meta end-to-end (proves the seam)

### Task 2.1: Implement adapters.meta() + /api/meta endpoint

**Files:**
- Create: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/routers/__init__.py`, `src/provectus_analytics/api/routers/meta.py`
- Modify: `src/provectus_analytics/api/main.py`
- Create: `tests/test_api/test_meta.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_api/test_meta.py`:

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data


def test_meta_returns_synthetic_when_no_real_exports(tmp_path, monkeypatch):
    # Build a fresh synthetic DB in tmp
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)

    app = create_app()
    client = TestClient(app)
    response = client.get("/api/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "synthetic"
    assert body["liveClientCount"] == 0
    assert body["dataState"]["flights"] > 0
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/test_api/test_meta.py -v
```

Expected: FAIL (404 for /api/meta).

- [ ] **Step 3: Implement adapters.py meta()**

Create `src/provectus_analytics/api/adapters.py`:

```python
"""Adapters bridge web/data.py outputs to api/schemas.py.

This is the only module that imports from web/data.py. Routers import from here.
"""
from __future__ import annotations

from ..web import data as web_data
from . import schemas


def meta() -> schemas.Meta:
    counts = web_data.row_counts(web_data.DEFAULT_DB)
    live_count = web_data.is_live_data(web_data.DEFAULT_DB)
    flight, invoice = web_data._has_real_exports()
    mode = "real" if (flight is not None and invoice is not None and live_count > 0) else "synthetic"
    return schemas.Meta(
        mode=mode,
        liveClientCount=live_count,
        dataState=schemas.DataState(
            flights=counts["flights"],
            invoices=counts["invoices"],
            students=counts["students"],
            surveys=counts["surveys"],
            overrides=counts["flight_overrides"],
        ),
    )
```

- [ ] **Step 4: Create routers/meta.py**

Create `src/provectus_analytics/api/routers/__init__.py` (empty).

Create `src/provectus_analytics/api/routers/meta.py`:

```python
from fastapi import APIRouter
from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta", response_model=schemas.Meta)
def get_meta() -> schemas.Meta:
    return adapters.meta()
```

- [ ] **Step 5: Wire router into main.py**

Modify `src/provectus_analytics/api/main.py` `create_app`:

```python
from .routers import meta as meta_router

def create_app() -> FastAPI:
    from .. import web  # ensure web/data.py is importable
    from ..web import data as web_data

    app = FastAPI(...)
    web_data.ensure_db(web_data.DEFAULT_DB)

    @app.get("/api/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(meta_router.router)

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app
```

- [ ] **Step 6: Run test to verify pass**

```bash
pytest tests/test_api/test_meta.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/provectus_analytics/api tests/test_api/test_meta.py
git commit -m "wire: /api/meta end-to-end with adapter pattern"
```

---

## Phase 3 — App shell (Sidebar, Topbar, theme, shortcuts, router)

### Task 3.1: Port Icon component

**Files:**
- Create: `frontend/src/components/Icon.tsx`
- Create: `frontend/src/components/Icon.test.tsx`

- [ ] **Step 1: Read the source**

Read `design_handoff_provectus_analytics/design/icons.jsx` start-to-end. It's a single component with a `switch` over `name`. Port verbatim to TSX.

- [ ] **Step 2: Write failing test**

Create `frontend/src/components/Icon.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { Icon } from './Icon';

test('renders an svg', () => {
  const { container } = render(<Icon name="search" size={16} />);
  expect(container.querySelector('svg')).toBeTruthy();
});
```

- [ ] **Step 3: Port Icon.tsx**

Create `frontend/src/components/Icon.tsx` — copy the `Icon` component from `design/icons.jsx` and add types:

```tsx
type IconProps = { name: string; size?: number; className?: string };

export function Icon({ name, size = 16, className }: IconProps) {
  // ... port the switch verbatim from design/icons.jsx
}
```

(Full body: copy each `case` from the source file verbatim.)

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/Icon.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Icon.tsx frontend/src/components/Icon.test.tsx
git commit -m "port: Icon component from design handoff"
```

---

### Task 3.2: Port primitives (Sparkline, Delta, Skel)

**Files:**
- Create: `frontend/src/components/primitives/Sparkline.tsx`
- Create: `frontend/src/components/primitives/Delta.tsx`
- Create: `frontend/src/components/primitives/Skel.tsx`
- Create: `frontend/src/components/primitives/index.ts`
- Create: `frontend/src/components/primitives/primitives.test.tsx`

- [ ] **Step 1: Read source**

Read `design_handoff_provectus_analytics/design/primitives.jsx` end-to-end.

- [ ] **Step 2: Port each primitive**

For each component, create a TSX file. Example for `Sparkline.tsx`:

```tsx
type SparklineProps = { values: number[]; color?: string; width?: number; height?: number };

export function Sparkline({ values, color = 'currentColor', width = 80, height = 24 }: SparklineProps) {
  // Body copied verbatim from design/primitives.jsx, with type annotations on locals.
}
```

Repeat for `Delta` and `Skel`. Match props from the source JSX.

Create `frontend/src/components/primitives/index.ts`:

```ts
export { Sparkline } from './Sparkline';
export { Delta } from './Delta';
export { Skel } from './Skel';
```

- [ ] **Step 3: Write smoke tests**

Create `frontend/src/components/primitives/primitives.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { Sparkline, Delta, Skel } from './';

test('Sparkline renders svg', () => {
  const { container } = render(<Sparkline values={[1, 2, 3]} />);
  expect(container.querySelector('svg')).toBeTruthy();
});

test('Delta renders signed value', () => {
  const { getByText } = render(<Delta value={0.12} positive />);
  expect(getByText(/12/)).toBeTruthy();
});

test('Skel renders placeholder', () => {
  const { container } = render(<Skel width={80} />);
  expect(container.querySelector('.skel')).toBeTruthy();
});
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/primitives
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/primitives
git commit -m "port: Sparkline/Delta/Skel primitives from design handoff"
```

---

### Task 3.3: Implement useTheme, useShortcuts, usePersistedTab, useRange hooks

**Files:**
- Create: `frontend/src/hooks/useTheme.ts`, `useShortcuts.ts`, `usePersistedTab.ts`, `useRange.ts`
- Create: `frontend/src/hooks/hooks.test.tsx`

- [ ] **Step 1: Write failing tests for useTheme**

Create `frontend/src/hooks/hooks.test.tsx`:

```tsx
import { renderHook, act } from '@testing-library/react';
import { useTheme } from './useTheme';
import { useRange } from './useRange';

beforeEach(() => { localStorage.clear(); document.documentElement.removeAttribute('data-theme'); });

test('useTheme defaults to dark', () => {
  const { result } = renderHook(() => useTheme());
  expect(result.current.theme).toBe('dark');
});

test('useTheme toggles + persists', () => {
  const { result } = renderHook(() => useTheme());
  act(() => result.current.toggle());
  expect(result.current.theme).toBe('light');
  expect(localStorage.getItem('pv-theme')).toBe('light');
  expect(document.documentElement.getAttribute('data-theme')).toBe('light');
});

test('useRange defaults to 12mo', () => {
  const { result } = renderHook(() => useRange());
  expect(result.current.range).toBe('12mo');
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npx vitest run src/hooks
```

Expected: FAIL (no module).

- [ ] **Step 3: Implement hooks**

Create `frontend/src/hooks/useTheme.ts`:

```ts
import { useEffect, useState, useCallback } from 'react';
import type { ThemeKey } from '../data/types';

const STORAGE_KEY = 'pv-theme';

function readInitial(): ThemeKey {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'dark' || stored === 'light') return stored;
  return 'dark';
}

export function useTheme() {
  const [theme, setTheme] = useState<ThemeKey>(readInitial);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem(STORAGE_KEY, theme); } catch {}
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme(t => (t === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, toggle, setTheme };
}
```

Create `frontend/src/hooks/useRange.ts`:

```ts
import { useState } from 'react';
import type { RangeKey } from '../data/types';

export function useRange(initial: RangeKey = '12mo') {
  const [range, setRange] = useState<RangeKey>(initial);
  return { range, setRange };
}
```

Create `frontend/src/hooks/usePersistedTab.ts`:

```ts
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export function usePersistedTab() {
  const location = useLocation();
  useEffect(() => {
    try { localStorage.setItem('pv-tab', location.pathname); } catch {}
  }, [location.pathname]);
}
```

Create `frontend/src/hooks/useShortcuts.ts`:

```ts
import { useEffect } from 'react';

type Handlers = {
  onCmdK?: () => void;
  onCollapseSidebar?: () => void;
  onToggleTheme?: () => void;
  onNavOverview?: () => void;
  onNavRating?: () => void;
  onNavStudent?: () => void;
  onNavInstructor?: () => void;
  onNavFlights?: () => void;
};

function isEditable(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  return (
    el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable
  );
}

export function useShortcuts(h: Handlers) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === 'k') { e.preventDefault(); h.onCmdK?.(); return; }
      if (mod && e.key === '\\') { e.preventDefault(); h.onCollapseSidebar?.(); return; }
      if (mod && e.shiftKey && e.key.toLowerCase() === 't') { e.preventDefault(); h.onToggleTheme?.(); return; }
      if (isEditable(e.target)) return;
      const k = e.key.toLowerCase();
      if (k === 'o') h.onNavOverview?.();
      else if (k === 'r') h.onNavRating?.();
      else if (k === 's') h.onNavStudent?.();
      else if (k === 'i') h.onNavInstructor?.();
      else if (k === 'f') h.onNavFlights?.();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [h]);
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/hooks
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks
git commit -m "hooks: useTheme, useRange, usePersistedTab, useShortcuts"
```

---

### Task 3.4: Build Sidebar component

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/components/Sidebar.test.tsx`

- [ ] **Step 1: Read source**

Read `design_handoff_provectus_analytics/design/panels.jsx` — find the `<Sidebar>` function. Note its props and structure: workspace header, nav section with 5 items, pinned reports, data-state block, user menu footer.

- [ ] **Step 2: Write failing test**

Create `frontend/src/components/Sidebar.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Sidebar } from './Sidebar';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

test('renders nav links', () => {
  render(wrap(<Sidebar collapsed={false} onToggleCollapse={() => {}} />));
  expect(screen.getByText('Overview')).toBeTruthy();
  expect(screen.getByText('Rating detail')).toBeTruthy();
  expect(screen.getByText('Student')).toBeTruthy();
  expect(screen.getByText('Instructor')).toBeTruthy();
  expect(screen.getByText('Flights')).toBeTruthy();
});
```

- [ ] **Step 3: Implement Sidebar.tsx**

Create `frontend/src/components/Sidebar.tsx` — port from `design/panels.jsx`'s `<Sidebar>` and the `NAV` constant. Replace anchor-based nav with `<NavLink>` from `react-router-dom`. Wire the data-state block to `useMeta()`:

```tsx
import { NavLink } from 'react-router-dom';
import { useMeta } from '../data/queries';
import { Icon } from './Icon';

const NAV = [
  { key: 'overview', label: 'Overview', shortcut: 'O', path: '/' },
  { key: 'rating', label: 'Rating detail', shortcut: 'R', path: '/ratings' },
  { key: 'student', label: 'Student', shortcut: 'S', path: '/students' },
  { key: 'instructor', label: 'Instructor', shortcut: 'I', path: '/instructors' },
  { key: 'flights', label: 'Flights', shortcut: 'F', path: '/flights' },
];

type Props = { collapsed: boolean; onToggleCollapse: () => void };

export function Sidebar({ collapsed, onToggleCollapse }: Props) {
  const meta = useMeta();
  // ... port markup from design/panels.jsx Sidebar exactly, replacing:
  //   - data-state block values with meta.data?.dataState
  //   - nav <a> with <NavLink to={path}>
  //   - pinned reports section as-is (static for now)
}
```

(Full markup: port from `design/panels.jsx`; preserve all class names exactly. The collapsed/expanded conditional logic is in the source.)

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/Sidebar.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Sidebar.tsx frontend/src/components/Sidebar.test.tsx
git commit -m "port: Sidebar component wired to /api/meta"
```

---

### Task 3.5: Build Topbar component

**Files:**
- Create: `frontend/src/components/Topbar.tsx`
- Create: `frontend/src/components/Topbar.test.tsx`

- [ ] **Step 1: Read source**

Find `<Topbar>` in `design/panels.jsx`. Note props: breadcrumb, range, cmdk-trigger, notification bell, theme toggle, import button, live pill.

- [ ] **Step 2: Write smoke test**

Create `frontend/src/components/Topbar.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Topbar } from './Topbar';

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

test('renders breadcrumb', () => {
  render(wrap(
    <Topbar
      breadcrumb="Overview" range="12mo" onRangeChange={() => {}}
      onOpenCmdK={() => {}} onToggleTheme={() => {}} theme="dark"
      onImport={() => {}} onOpenNotifications={() => {}}
    />
  ));
  expect(screen.getByText(/Provectus Aviation/)).toBeTruthy();
  expect(screen.getByText(/Overview/)).toBeTruthy();
});
```

- [ ] **Step 3: Implement Topbar.tsx**

Port `<Topbar>` from `design/panels.jsx` to TSX. Wire the Live pill to `useMeta()` — show `Live · N clients` when `mode === 'real'`, else `Synthetic data`.

Props:

```tsx
type TopbarProps = {
  breadcrumb: string;
  range: RangeKey;
  onRangeChange: (r: RangeKey) => void;
  onOpenCmdK: () => void;
  onToggleTheme: () => void;
  theme: ThemeKey;
  onImport: () => void;
  onOpenNotifications: () => void;
  showRangePicker?: boolean;
};
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/Topbar.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Topbar.tsx frontend/src/components/Topbar.test.tsx
git commit -m "port: Topbar component with Live pill bound to /api/meta"
```

---

### Task 3.6: Set up react-router-dom with 5 placeholder routes

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/routes/Overview.tsx`, `RatingDetail.tsx`, `Student.tsx`, `Instructor.tsx`, `Flights.tsx` (placeholders)
- Modify: `frontend/src/main.tsx` (wrap with BrowserRouter)

- [ ] **Step 1: Add BrowserRouter to main.tsx**

Modify `frontend/src/main.tsx`:

```tsx
import { BrowserRouter } from 'react-router-dom';

// ... inside createRoot:
<BrowserRouter>
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
</BrowserRouter>
```

- [ ] **Step 2: Create placeholder route files**

For each route, create `frontend/src/routes/<Name>.tsx`:

```tsx
export default function Overview() {
  return <div className="page-head"><h1>Overview</h1></div>;
}
```

Repeat for `RatingDetail`, `Student`, `Instructor`, `Flights` with their respective `<h1>` text.

- [ ] **Step 3: Replace App.tsx with router shell**

Replace `frontend/src/App.tsx`:

```tsx
import { useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import Overview from './routes/Overview';
import RatingDetail from './routes/RatingDetail';
import Student from './routes/Student';
import Instructor from './routes/Instructor';
import Flights from './routes/Flights';
import { useTheme } from './hooks/useTheme';
import { useShortcuts } from './hooks/useShortcuts';
import { usePersistedTab } from './hooks/usePersistedTab';
import { useRange } from './hooks/useRange';
import type { RangeKey } from './data/types';

function breadcrumbFor(pathname: string): string {
  if (pathname === '/') return 'Overview';
  if (pathname.startsWith('/ratings')) return 'Rating detail';
  if (pathname.startsWith('/students')) return 'Student';
  if (pathname.startsWith('/instructors')) return 'Instructor';
  if (pathname.startsWith('/flights')) return 'Flights';
  return 'Overview';
}

export default function App() {
  const navigate = useNavigate();
  const { theme, toggle: toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const { range, setRange } = useRange();
  usePersistedTab();

  useShortcuts({
    onCmdK: () => setCmdkOpen(v => !v),
    onCollapseSidebar: () => setCollapsed(v => !v),
    onToggleTheme: toggleTheme,
    onNavOverview: () => navigate('/'),
    onNavRating: () => navigate('/ratings'),
    onNavStudent: () => navigate('/students'),
    onNavInstructor: () => navigate('/instructors'),
    onNavFlights: () => navigate('/flights'),
  });

  const pathname = window.location.pathname;
  const breadcrumb = breadcrumbFor(pathname);

  return (
    <div className="app">
      <Sidebar collapsed={collapsed} onToggleCollapse={() => setCollapsed(v => !v)} />
      <div className="main">
        <Topbar
          breadcrumb={breadcrumb}
          range={range}
          onRangeChange={setRange}
          onOpenCmdK={() => setCmdkOpen(true)}
          onToggleTheme={toggleTheme}
          theme={theme}
          onImport={() => { /* wired later */ }}
          onOpenNotifications={() => {}}
          showRangePicker={pathname === '/'}
        />
        <div className="canvas">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/ratings/:code?" element={<RatingDetail />} />
            <Route path="/students/:id?" element={<Student />} />
            <Route path="/instructors/:id?" element={<Instructor />} />
            <Route path="/flights" element={<Flights />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Smoke test — build + run**

```bash
cd frontend && npm run build
```

Expected: build succeeds.

Run the FastAPI server in one terminal, open `http://127.0.0.1:8050/` — verify sidebar + topbar render, click nav links, theme toggle works, ⌘K state toggles (no UI yet but no errors).

- [ ] **Step 5: Type-check + tests**

```bash
cd frontend && npx tsc --noEmit && npx vitest run
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx frontend/src/routes frontend/src/main.tsx
git commit -m "wire: router shell with 5 placeholder routes"
```

---

## Phase 4 — Overview tab

### Task 4.1: Build adapter helpers (range filtering, data-state)

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`
- Create: `tests/test_api/test_adapters.py`

- [ ] **Step 1: Write tests for range-to-cutoff helper**

Create `tests/test_api/test_adapters.py`:

```python
from datetime import date, timedelta
from provectus_analytics.api import adapters


def test_range_cutoff_30d_returns_30_days_ago():
    cutoff = adapters.range_cutoff("30d", today=date(2026, 1, 31))
    assert cutoff == date(2026, 1, 1)


def test_range_cutoff_12mo():
    cutoff = adapters.range_cutoff("12mo", today=date(2026, 1, 31))
    assert cutoff == date(2025, 1, 31)


def test_range_cutoff_all_returns_none():
    assert adapters.range_cutoff("all") is None
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/test_api/test_adapters.py -v
```

- [ ] **Step 3: Add range_cutoff() helper**

Append to `src/provectus_analytics/api/adapters.py`:

```python
from datetime import date, timedelta
from .schemas import RangeKey

def range_cutoff(range_key: RangeKey, today: date | None = None) -> date | None:
    today = today or date.today()
    if range_key == "30d":  return today - timedelta(days=30)
    if range_key == "90d":  return today - timedelta(days=90)
    if range_key == "6mo":  return today - timedelta(days=180)
    if range_key == "12mo": return today - timedelta(days=365)
    if range_key == "ytd":  return date(today.year, 1, 1)
    if range_key == "all":  return None
    raise ValueError(f"unknown range_key: {range_key}")
```

- [ ] **Step 4: Verify pass + commit**

```bash
pytest tests/test_api/test_adapters.py -v
git add src/provectus_analytics/api/adapters.py tests/test_api/test_adapters.py
git commit -m "adapters: range_cutoff helper for range filtering"
```

---

### Task 4.2: Implement /api/kpis endpoint

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/main.py`
- Create: `src/provectus_analytics/api/routers/kpis.py`, `tests/test_api/test_kpis.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_api/test_kpis.py`:

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data


def test_kpis_returns_four_cards(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()

    app = create_app()
    client = TestClient(app)
    response = client.get("/api/kpis?range=12mo")
    assert response.status_code == 200
    kpis = response.json()
    assert len(kpis) == 4
    keys = {k["key"] for k in kpis}
    assert keys == {"ratings_completed", "active_clients", "flight_hours", "total_billed"}
    for k in kpis:
        assert "value" in k and "spark" in k and isinstance(k["spark"], list)
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/test_api/test_kpis.py -v
```

- [ ] **Step 3: Implement adapters.kpis()**

Append to `src/provectus_analytics/api/adapters.py`:

```python
import sqlite3
from . import schemas

def kpis(range_key: schemas.RangeKey) -> list[schemas.Kpi]:
    cutoff = range_cutoff(range_key)
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        # 1) Ratings completed in range
        if cutoff:
            ratings_completed = conn.execute(
                "SELECT COUNT(*) FROM milestones WHERE milestone_name='checkride' AND milestone_date >= ?",
                (cutoff.isoformat(),)
            ).fetchone()[0]
        else:
            ratings_completed = conn.execute(
                "SELECT COUNT(*) FROM milestones WHERE milestone_name='checkride'"
            ).fetchone()[0]

        # 2) Active clients = students with flights in range, no checkride yet
        if cutoff:
            active = conn.execute(
                """SELECT COUNT(DISTINCT s.student_id) FROM students s
                   JOIN flights f USING (student_id)
                   LEFT JOIN milestones m ON m.milestone_name='checkride'
                   WHERE f.flight_date >= ?""", (cutoff.isoformat(),)
            ).fetchone()[0]
        else:
            active = conn.execute(
                """SELECT COUNT(DISTINCT s.student_id) FROM students s
                   JOIN flights f USING (student_id)"""
            ).fetchone()[0]

        # 3) Flight hours billed in range
        if cutoff:
            hours = conn.execute(
                "SELECT COALESCE(SUM(length_hrs),0) FROM flights WHERE flight_date >= ?",
                (cutoff.isoformat(),)
            ).fetchone()[0]
        else:
            hours = conn.execute("SELECT COALESCE(SUM(length_hrs),0) FROM flights").fetchone()[0]

        # 4) Total billed in range
        if cutoff:
            billed = conn.execute(
                """SELECT COALESCE(SUM(amount),0) FROM invoices i
                   JOIN flights f USING (fsp_reservation)
                   WHERE f.flight_date >= ?""", (cutoff.isoformat(),)
            ).fetchone()[0] or 0.0
        else:
            billed = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM invoices"
            ).fetchone()[0] or 0.0
    finally:
        conn.close()

    # Spark = placeholder rolling weekly trend; deterministic for now
    return [
        schemas.Kpi(key="ratings_completed", label="Ratings completed", value=str(ratings_completed),
                    sub=_range_sub(range_key), delta=0.0, positive=True,
                    spark=[ratings_completed]*8, color="#6E56F8"),
        schemas.Kpi(key="active_clients", label="Active clients", value=str(active),
                    sub=_range_sub(range_key), delta=0.0, positive=True,
                    spark=[active]*8, color="#3DD68C"),
        schemas.Kpi(key="flight_hours", label="Flight hours", value=f"{hours:,.0f}",
                    sub=_range_sub(range_key), delta=0.0, positive=True,
                    spark=[hours]*8, color="#22D3EE"),
        schemas.Kpi(key="total_billed", label="Total billed", value=f"${billed:,.0f}",
                    sub=_range_sub(range_key), delta=0.0, positive=True,
                    spark=[billed]*8, color="#F59E0B"),
    ]

def _range_sub(range_key: str) -> str:
    return {"30d":"last 30 days","90d":"last 90 days","6mo":"last 6 months",
            "12mo":"last 12 months","ytd":"year to date","all":"all time"}[range_key]
```

(Note: deltas and sparklines are wired with trivial values for now — Phase-4-stretch task can compute real deltas vs prior period.)

- [ ] **Step 4: Create routers/kpis.py**

Create `src/provectus_analytics/api/routers/kpis.py`:

```python
from fastapi import APIRouter, Query
from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["kpis"])

@router.get("/kpis", response_model=list[schemas.Kpi])
def get_kpis(range: schemas.RangeKey = Query("12mo")) -> list[schemas.Kpi]:
    return adapters.kpis(range)
```

- [ ] **Step 5: Wire in main.py**

In `create_app()`, add `from .routers import kpis as kpis_router` and `app.include_router(kpis_router.router)`.

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_api/test_kpis.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/provectus_analytics/api tests/test_api/test_kpis.py
git commit -m "wire: /api/kpis endpoint with range filter"
```

---

### Task 4.3: Implement /api/ratings (cohort bars) + /api/ratings/completed + /api/heatmap

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/main.py`
- Create: `src/provectus_analytics/api/routers/ratings.py`, `tests/test_api/test_ratings.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_api/test_ratings.py`:

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data


def _fresh(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app())


def test_rating_bars_one_row_per_rating(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    r = client.get("/api/ratings?metric=hours&range=all")
    assert r.status_code == 200
    rows = r.json()
    assert {row["code"] for row in rows} <= {"PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"}
    for row in rows:
        assert row["median"] >= 0
        assert row["p25"] <= row["median"] <= row["p75"]


def test_ratings_completed(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    r = client.get("/api/ratings/completed?range=all")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_heatmap_returns_7x12_matrix(tmp_path, monkeypatch):
    client = _fresh(tmp_path, monkeypatch)
    r = client.get("/api/heatmap?range=all")
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) == 7
    assert all(len(row) == 12 for row in body["rows"])
    assert len(body["buckets"]) == 12
```

- [ ] **Step 2: Run to verify fail**

```bash
pytest tests/test_api/test_ratings.py -v
```

- [ ] **Step 3: Implement adapter functions**

Append to `src/provectus_analytics/api/adapters.py`:

```python
def rating_bars(metric: schemas.MetricKey, range_key: schemas.RangeKey) -> list[schemas.RatingBarPoint]:
    from .. import norms
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        norm_rows = norms.compute_rating_norms(conn)
    finally:
        conn.close()
    name_map = {"PPL":"Private Pilot","IFR":"Instrument","COM":"Commercial SE",
                "AMEL":"Multi-Engine","CFI":"CFI","CFII":"CFII","MEI":"MEI"}
    metric_to_attrs = {
        "hours": ("median_hours", "p25_hours", "p75_hours"),
        "cost":  ("median_cost",  "p25_cost",  "p75_cost"),
        "days":  ("median_days",  "p25_days",  "p75_days"),
    }
    med_a, p25_a, p75_a = metric_to_attrs[metric]
    out: list[schemas.RatingBarPoint] = []
    for n in norm_rows:
        out.append(schemas.RatingBarPoint(
            code=n.rating_code, name=name_map.get(n.rating_code, n.rating_code),
            n=n.n, median=getattr(n, med_a) or 0,
            p25=getattr(n, p25_a) or 0, p75=getattr(n, p75_a) or 0,
        ))
    return out


def ratings_completed(range_key: schemas.RangeKey) -> list[schemas.RatingsCompletedRow]:
    cutoff = range_cutoff(range_key)
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        if cutoff:
            rows = conn.execute(
                """SELECT r.code, COUNT(*) FROM milestones m
                   JOIN enrollments e USING (enrollment_id)
                   JOIN ratings r USING (rating_id)
                   WHERE m.milestone_name='checkride' AND m.milestone_date >= ?
                   GROUP BY r.code""", (cutoff.isoformat(),)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT r.code, COUNT(*) FROM milestones m
                   JOIN enrollments e USING (enrollment_id)
                   JOIN ratings r USING (rating_id)
                   WHERE m.milestone_name='checkride' GROUP BY r.code"""
            ).fetchall()
    finally:
        conn.close()
    return [schemas.RatingsCompletedRow(rating=code, count=cnt) for code, cnt in rows]


def heatmap(range_key: schemas.RangeKey) -> schemas.Heatmap:
    cutoff = range_cutoff(range_key)
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    buckets = ["6a","8a","10a","12p","2p","4p","6p","8p","10p","12a","2a","4a"]
    rows = [[0.0]*12 for _ in range(7)]
    try:
        if cutoff:
            data_rows = conn.execute(
                """SELECT flight_date FROM flights WHERE flight_date >= ?""",
                (cutoff.isoformat(),)
            ).fetchall()
        else:
            data_rows = conn.execute("SELECT flight_date FROM flights").fetchall()
    finally:
        conn.close()
    # FSP doesn't give time-of-day; use day-of-week only and spread evenly.
    # When real time-of-day arrives, bucket properly. For now, this approximates
    # the visual density per dow in the design.
    from datetime import datetime
    for (date_s,) in data_rows:
        try:
            dow = datetime.fromisoformat(date_s).weekday()
        except Exception:
            continue
        for col in range(12):
            rows[dow][col] += 1 / 12
    return schemas.Heatmap(rows=rows, buckets=buckets)
```

- [ ] **Step 4: Create routers/ratings.py**

Create `src/provectus_analytics/api/routers/ratings.py`:

```python
from fastapi import APIRouter, Query
from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["ratings"])

@router.get("/ratings", response_model=list[schemas.RatingBarPoint])
def get_rating_bars(
    metric: schemas.MetricKey = Query("hours"),
    range: schemas.RangeKey = Query("12mo"),
):
    return adapters.rating_bars(metric, range)

@router.get("/ratings/completed", response_model=list[schemas.RatingsCompletedRow])
def get_ratings_completed(range: schemas.RangeKey = Query("12mo")):
    return adapters.ratings_completed(range)

@router.get("/heatmap", response_model=schemas.Heatmap)
def get_heatmap(range: schemas.RangeKey = Query("12mo")):
    return adapters.heatmap(range)
```

(`/ratings/{code}` is added in Task 5.1 — leave for now.)

- [ ] **Step 5: Wire in main.py + run tests**

Include the ratings router. Run:

```bash
pytest tests/test_api/test_ratings.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/provectus_analytics/api tests/test_api/test_ratings.py
git commit -m "wire: /api/ratings, /api/ratings/completed, /api/heatmap"
```

---

### Task 4.4: Implement /api/students (clients table)

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/main.py`
- Create: `src/provectus_analytics/api/routers/students.py`, `tests/test_api/test_students.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_api/test_students.py`:

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data


def _fresh(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db_path)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path / "no_exports")
    web_data.build_db(db_path, force_synthetic=True)
    web_data.clear_caches()
    return TestClient(create_app())


def test_students_returns_rows(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/students?range=all")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0
    row = rows[0]
    assert {"id","name","rating","progressPct","hoursToDate","daysEnrolled","status"} <= row.keys()
    assert row["status"] in {"Active","On checkride","Completed"}


def test_students_filtered_by_rating(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/students?range=all&rating=PPL")
    assert r.status_code == 200
    rows = r.json()
    assert all(row["rating"] == "PPL" for row in rows)
```

- [ ] **Step 2: Run to verify fail**

- [ ] **Step 3: Implement adapters.clients()**

Append to `adapters.py`:

```python
def clients(range_key: schemas.RangeKey, rating: schemas.RatingCode | None = None) -> list[schemas.ClientRow]:
    cutoff = range_cutoff(range_key)
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        params: list = []
        sql = """
          SELECT s.student_id, s.fsp_display_name, r.code, COALESCE(SUM(f.length_hrs),0) AS hours,
                 MIN(f.flight_date) AS first_flight, MAX(f.flight_date) AS last_flight,
                 EXISTS (
                   SELECT 1 FROM milestones m JOIN enrollments e2 USING (enrollment_id)
                   WHERE e2.student_id = s.student_id AND e2.rating_id = r.rating_id
                     AND m.milestone_name='checkride'
                 ) AS has_checkride
          FROM students s
          JOIN enrollments e USING (student_id)
          JOIN ratings r USING (rating_id)
          LEFT JOIN flights f ON f.student_id = s.student_id AND f.enrollment_id = e.enrollment_id
          WHERE 1=1
        """
        if cutoff:
            sql += " AND (f.flight_date >= ? OR f.flight_date IS NULL)"
            params.append(cutoff.isoformat())
        if rating:
            sql += " AND r.code = ?"; params.append(rating)
        sql += " GROUP BY s.student_id, r.code ORDER BY s.fsp_display_name"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    out: list[schemas.ClientRow] = []
    from datetime import date as _date
    for sid, name, code, hours, first, last, has_check in rows:
        # progressPct: hours / median for that rating, capped at 1.0
        # status: Completed if checkride, On checkride if hours within 10% of median, else Active
        days = 0
        if first:
            try:
                days = (_date.today() - _date.fromisoformat(first)).days
            except Exception:
                days = 0
        progress = 0.5  # TODO compute vs norm; placeholder for first cut
        status = "Completed" if has_check else ("On checkride" if progress > 0.9 else "Active")
        out.append(schemas.ClientRow(
            id=str(sid), name=name or "Unknown", rating=code,
            progressPct=progress, hoursToDate=float(hours or 0),
            daysEnrolled=int(days), status=status,
        ))
    return out
```

- [ ] **Step 4: Create routers/students.py**

```python
from fastapi import APIRouter, Query
from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["students"])

@router.get("/students", response_model=list[schemas.ClientRow])
def get_clients(
    range: schemas.RangeKey = Query("12mo"),
    rating: schemas.RatingCode | None = Query(None),
):
    return adapters.clients(range, rating)
```

- [ ] **Step 5: Wire + test + commit**

```bash
pytest tests/test_api/test_students.py -v
git add src/provectus_analytics/api tests/test_api/test_students.py
git commit -m "wire: /api/students endpoint with rating filter"
```

---

### Task 4.5: Port charts (RatingBars, RatingsList, Heatmap)

**Files:**
- Create: `frontend/src/components/charts/RatingBars.tsx`, `RatingsList.tsx`, `Heatmap.tsx`
- Create: `frontend/src/components/charts/charts.test.tsx`

- [ ] **Step 1: Read sources**

Read `design_handoff_provectus_analytics/design/charts.jsx`. Each chart is hand-rolled SVG. Port verbatim.

- [ ] **Step 2: Port RatingBars**

Create `frontend/src/components/charts/RatingBars.tsx`. Copy the `<RatingBars>` component from `design/charts.jsx`. Replace the `data` prop type with `RatingBarPoint[]` from `data/types.ts`. Preserve all SVG path math.

- [ ] **Step 3: Port RatingsList**

Create `frontend/src/components/charts/RatingsList.tsx`. Same drill — port from source.

- [ ] **Step 4: Port Heatmap**

Create `frontend/src/components/charts/Heatmap.tsx`. Port. Props: `rows: number[][]`, `buckets: string[]`.

- [ ] **Step 5: Smoke tests**

Create `frontend/src/components/charts/charts.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { RatingBars } from './RatingBars';
import { Heatmap } from './Heatmap';

test('RatingBars renders SVG bars', () => {
  const { container } = render(<RatingBars
    data={[{ code: 'PPL', name: 'PPL', n: 10, median: 60, p25: 50, p75: 70 }]}
    metric="hours"
  />);
  expect(container.querySelector('svg')).toBeTruthy();
});

test('Heatmap renders 7x12 grid', () => {
  const rows = Array.from({ length: 7 }, () => Array(12).fill(0));
  const { container } = render(<Heatmap rows={rows} buckets={Array(12).fill('x')} />);
  expect(container.querySelector('svg')).toBeTruthy();
});
```

- [ ] **Step 6: Run + commit**

```bash
cd frontend && npx vitest run src/components/charts
git add frontend/src/components/charts
git commit -m "port: hand-rolled SVG charts (RatingBars, RatingsList, Heatmap)"
```

---

### Task 4.6: Build KpiGrid component

**Files:**
- Create: `frontend/src/components/KpiGrid.tsx`
- Create: `frontend/src/components/KpiGrid.test.tsx`

- [ ] **Step 1: Read source**

In `design/panels.jsx`, find `<KpiGrid>`. Note its prop shape and click-to-focus behavior.

- [ ] **Step 2: Write smoke test**

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { KpiGrid } from './KpiGrid';

test('renders KPI cards and focuses on click', () => {
  const onFocus = vi.fn();
  render(<KpiGrid
    kpis={[
      { key:'a', label:'A', value:'1', sub:'sub', delta:0.1, positive:true, spark:[1,2], color:'#fff' },
    ]}
    focusedKey={null}
    onFocus={onFocus}
  />);
  fireEvent.click(screen.getByText('A'));
  expect(onFocus).toHaveBeenCalledWith('a');
});
```

- [ ] **Step 3: Port KpiGrid.tsx**

Port `<KpiGrid>` from `design/panels.jsx`. Props:

```tsx
type Props = { kpis: Kpi[]; focusedKey: string | null; onFocus: (key: string) => void };
```

- [ ] **Step 4: Run + commit**

```bash
cd frontend && npx vitest run src/components/KpiGrid.test.tsx
git add frontend/src/components/KpiGrid.tsx frontend/src/components/KpiGrid.test.tsx
git commit -m "port: KpiGrid component"
```

---

### Task 4.7: Build ClientsTable component

**Files:**
- Create: `frontend/src/components/ClientsTable.tsx`
- Create: `frontend/src/components/ClientsTable.test.tsx`

- [ ] **Step 1: Read source**

In `design/panels.jsx`, find `<ClientsTable>`. Sortable, searchable, with progress bars + status pills.

- [ ] **Step 2: Write smoke test**

```tsx
import { render, screen } from '@testing-library/react';
import { ClientsTable } from './ClientsTable';

test('renders rows', () => {
  render(<ClientsTable rows={[
    { id:'1', name:'Alex', rating:'PPL', progressPct:0.5, hoursToDate:40, daysEnrolled:60, status:'Active' },
  ]} />);
  expect(screen.getByText('Alex')).toBeTruthy();
});
```

- [ ] **Step 3: Port ClientsTable.tsx**

Port `<ClientsTable>` from `design/panels.jsx`. Props:

```tsx
type Props = { rows: ClientRow[]; filterRating?: RatingCode | null; onClearFilter?: () => void };
```

- [ ] **Step 4: Run + commit**

```bash
cd frontend && npx vitest run src/components/ClientsTable.test.tsx
git add frontend/src/components/ClientsTable.tsx frontend/src/components/ClientsTable.test.tsx
git commit -m "port: ClientsTable component"
```

---

### Task 4.8: Wire Overview route end-to-end

**Files:**
- Modify: `frontend/src/routes/Overview.tsx`
- Create: `frontend/src/routes/Overview.test.tsx`

- [ ] **Step 1: Read source**

In `design/app.jsx`, find `<OverviewTab>`. It composes `<KpiGrid>`, the cohort `<RatingBars>` card, the two-up row with `<RatingsList>` + `<Heatmap>`, and `<ClientsTable>`.

- [ ] **Step 2: Implement Overview.tsx**

```tsx
import { useState } from 'react';
import { useKpis, useRatingBars, useRatingsCompleted, useHeatmap, useClients } from '../data/queries';
import { KpiGrid } from '../components/KpiGrid';
import { ClientsTable } from '../components/ClientsTable';
import { RatingBars } from '../components/charts/RatingBars';
import { RatingsList } from '../components/charts/RatingsList';
import { Heatmap } from '../components/charts/Heatmap';
import { Skel } from '../components/primitives';
import type { RangeKey, MetricKey, RatingCode } from '../data/types';

type Props = { range: RangeKey };

export default function Overview({ range }: Props) {
  const [metric, setMetric] = useState<MetricKey>('hours');
  const [focusedKpi, setFocusedKpi] = useState<string | null>(null);
  const [focusedRating, setFocusedRating] = useState<RatingCode | null>(null);

  const kpis = useKpis(range);
  const bars = useRatingBars(metric, range);
  const completed = useRatingsCompleted(range);
  const heatmap = useHeatmap(range);
  const clients = useClients(range, focusedRating ?? undefined);

  return (
    <div className="overview">
      <div className="page-head">
        <div className="eyebrow">Cohort overview</div>
        <h1>All ratings</h1>
        <div className="page-sub">Median + P25–P75 to checkride · {rangeLabel(range)} · all ratings</div>
      </div>

      {kpis.isLoading ? <Skel height={120} /> : kpis.data ? (
        <KpiGrid kpis={kpis.data} focusedKey={focusedKpi} onFocus={k => setFocusedKpi(focusedKpi === k ? null : k)} />
      ) : null}

      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Median {metric} to checkride · by rating</div>
            <div className="card-sub">Click a bar to filter clients</div>
          </div>
          <div className="metric-switch">
            {(['hours','cost','days'] as MetricKey[]).map(m => (
              <button key={m} className={metric===m ? 'active':''} onClick={() => setMetric(m)}>{m}</button>
            ))}
          </div>
        </div>
        {bars.isLoading ? <Skel height={280} /> : bars.data ? (
          <RatingBars data={bars.data} metric={metric}
                      focusedCode={focusedRating} onFocus={(c) => setFocusedRating(focusedRating === c ? null : c)} />
        ) : null}
      </div>

      <div className="two-up">
        <div className="card">
          <div className="card-title">Ratings completed</div>
          {completed.isLoading ? <Skel height={180}/> : completed.data ?
            <RatingsList data={completed.data} /> : null}
        </div>
        <div className="card">
          <div className="card-title">When clients train</div>
          {heatmap.isLoading ? <Skel height={180}/> : heatmap.data ?
            <Heatmap rows={heatmap.data.rows} buckets={heatmap.data.buckets} /> : null}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">Clients</div>
          {focusedRating && (
            <button onClick={() => setFocusedRating(null)}>Clear filter</button>
          )}
        </div>
        {clients.isLoading ? <Skel height={400} /> : clients.data ? (
          <ClientsTable rows={clients.data} filterRating={focusedRating} onClearFilter={() => setFocusedRating(null)} />
        ) : null}
      </div>
    </div>
  );
}

function rangeLabel(r: RangeKey): string {
  const map: Record<RangeKey, string> = {
    '30d':'last 30 days','90d':'last 90 days','6mo':'last 6 months',
    '12mo':'last 12 months','ytd':'year to date','all':'all time',
  };
  return map[r];
}
```

- [ ] **Step 3: Update App.tsx to pass range to Overview**

In `App.tsx`, the route now needs:

```tsx
<Route path="/" element={<Overview range={range} />} />
```

- [ ] **Step 4: Write smoke test**

```tsx
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Overview from './Overview';

test('renders Overview shell', () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } }});
  global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><Overview range="12mo" /></MemoryRouter>
    </QueryClientProvider>
  );
});
```

- [ ] **Step 5: Manual smoke test**

Build frontend, run uvicorn, open browser. Verify Overview renders cards + bars + heatmap + table against synthetic data. Compare side-by-side with `design/Dashboard.html` and `screenshots/01-overview-dark.png`. Note diffs but don't fix yet — pixel polish comes after all tabs work.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/Overview.tsx frontend/src/routes/Overview.test.tsx frontend/src/App.tsx
git commit -m "wire: Overview tab end-to-end against /api/* endpoints"
```

---

## Phase 5 — Rating Detail tab

### Task 5.1: Implement /api/ratings/{code} endpoint

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/routers/ratings.py`
- Create: `tests/test_api/test_rating_detail.py`

- [ ] **Step 1: Write failing test**

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data

def test_rating_detail_ppl(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path/"no_exports")
    web_data.build_db(db, force_synthetic=True); web_data.clear_caches()
    c = TestClient(create_app())
    r = c.get("/api/ratings/PPL")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "PPL"
    assert "medianHrs" in body
```

- [ ] **Step 2: Implement adapters.rating_detail()**

Append to adapters.py:

```python
def rating_detail(code: schemas.RatingCode) -> schemas.Rating:
    from .. import norms
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        rows = norms.compute_rating_norms(conn)
    finally:
        conn.close()
    for n in rows:
        if n.rating_code == code:
            name_map = {"PPL":"Private Pilot","IFR":"Instrument","COM":"Commercial SE",
                        "AMEL":"Multi-Engine","CFI":"CFI","CFII":"CFII","MEI":"MEI"}
            return schemas.Rating(
                code=code, name=name_map.get(code, code), n=n.n,
                medianHrs=n.median_hours or 0, p25Hrs=n.p25_hours or 0, p75Hrs=n.p75_hours or 0,
                medianCost=n.median_cost or 0, p25Cost=n.p25_cost or 0, p75Cost=n.p75_cost or 0,
                medianDays=n.median_days or 0, p25Days=n.p25_days or 0, p75Days=n.p75_days or 0,
                lowSample=(n.n < 10),
            )
    raise LookupError(f"rating not found: {code}")
```

- [ ] **Step 3: Add 404 handler in main.py**

In `create_app`, add:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(LookupError)
def _lookup_handler(request: Request, exc: LookupError):
    return JSONResponse(status_code=404, content={"error": str(exc)})

@app.exception_handler(KeyError)
def _key_handler(request: Request, exc: KeyError):
    return JSONResponse(status_code=404, content={"error": str(exc)})
```

- [ ] **Step 4: Add endpoint to ratings router**

```python
@router.get("/ratings/{code}", response_model=schemas.Rating)
def get_rating(code: schemas.RatingCode, range: schemas.RangeKey = Query("12mo")):
    return adapters.rating_detail(code)
```

- [ ] **Step 5: Run + commit**

```bash
pytest tests/test_api/test_rating_detail.py -v
git add src/provectus_analytics/api tests/test_api/test_rating_detail.py
git commit -m "wire: /api/ratings/{code} with 404 handling"
```

---

### Task 5.2: Port tab-helpers (Select, BigKpi, MiniKpi, DeltaText)

**Files:**
- Create: `frontend/src/components/helpers/{Select,BigKpi,MiniKpi,DeltaText}.tsx`
- Create: `frontend/src/components/helpers/index.ts`

- [ ] **Step 1: Read source**

Read `design_handoff_provectus_analytics/design/tab-helpers.jsx`. Port each component to its own TSX file with explicit prop types.

- [ ] **Step 2: Port each**

Create `Select.tsx`, `BigKpi.tsx`, `MiniKpi.tsx`, `DeltaText.tsx`. Match props from the JSX source.

`frontend/src/components/helpers/index.ts`:

```ts
export { Select } from './Select';
export { BigKpi } from './BigKpi';
export { MiniKpi } from './MiniKpi';
export { DeltaText } from './DeltaText';
```

- [ ] **Step 3: Smoke test + commit**

```bash
cd frontend && npx tsc --noEmit && npx vitest run
git add frontend/src/components/helpers
git commit -m "port: tab-helpers (Select, BigKpi, MiniKpi, DeltaText)"
```

---

### Task 5.3: Build RatingDetail route

**Files:**
- Modify: `frontend/src/routes/RatingDetail.tsx`

- [ ] **Step 1: Read source**

In `design/tab-rating.jsx`, find the rating-detail component.

- [ ] **Step 2: Implement RatingDetail.tsx**

```tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useRating, useRatingBars } from '../data/queries';
import { BigKpi, MiniKpi, DeltaText, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import type { RangeKey, RatingCode } from '../data/types';

const CODES: RatingCode[] = ['PPL','IFR','COM','AMEL','CFI','CFII','MEI'];

export default function RatingDetail({ range }: { range: RangeKey }) {
  const { code } = useParams<{ code?: RatingCode }>();
  const navigate = useNavigate();
  const selected = (code ?? 'PPL') as RatingCode;
  const rating = useRating(selected, range);

  return (
    <div className="rating-detail">
      <div className="page-head">
        <div className="eyebrow">Rating detail</div>
        <h1>{rating.data?.name ?? '—'}</h1>
        <Select value={selected} onChange={v => navigate(`/ratings/${v}`)}
                options={CODES.map(c => ({ value: c, label: c }))} />
      </div>

      {rating.isLoading ? <Skel height={400} /> : rating.data ? (
        <>
          <div className="big-kpi-row">
            <BigKpi label="Median hours" value={rating.data.medianHrs.toFixed(1)} />
            <BigKpi label="Median cost"  value={`$${rating.data.medianCost.toLocaleString()}`} />
            <BigKpi label="Median days"  value={String(rating.data.medianDays)} />
          </div>
          {/* TODO: distribution scatter + methodology — port from tab-rating.jsx */}
        </>
      ) : <div>No data.</div>}
    </div>
  );
}
```

- [ ] **Step 3: Wire route in App.tsx**

```tsx
<Route path="/ratings/:code?" element={<RatingDetail range={range} />} />
```

- [ ] **Step 4: Smoke + commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/routes/RatingDetail.tsx frontend/src/App.tsx
git commit -m "wire: RatingDetail tab end-to-end"
```

---

## Phase 6 — Student tab

### Task 6.1: Implement /api/students/{id} endpoint

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/routers/students.py`
- Create: `tests/test_api/test_student_detail.py`

- [ ] **Step 1: Write failing test**

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data

def test_student_detail(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path/"no_exports")
    web_data.build_db(db, force_synthetic=True); web_data.clear_caches()
    c = TestClient(create_app())
    # Get list first to grab an id
    rows = c.get("/api/students?range=all").json()
    sid = rows[0]["id"]
    r = c.get(f"/api/students/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == sid
    assert "timeline" in body
```

- [ ] **Step 2: Implement adapters.student_detail()**

Use existing `web_data.student_trajectory(db_path, student_name)` — but the route takes an id, not a name. Add a small lookup:

```python
def student_detail(student_id: str) -> schemas.StudentDetail:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        row = conn.execute(
            "SELECT fsp_display_name FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
        if not row:
            raise LookupError(f"student {student_id}")
        name = row[0]
    finally:
        conn.close()
    df = web_data.student_trajectory(str(web_data.DEFAULT_DB), name)
    # Group by rating into timeline points
    timeline = []
    for rating_code, group in df.groupby("rating"):
        ms = [{"name": r["milestone"], "date": r["milestone_date"]} for _, r in group.iterrows()]
        timeline.append(schemas.StudentTimelinePoint(
            rating=rating_code, start=ms[0]["date"] if ms else "",
            end=ms[-1]["date"] if len(ms) > 1 else None, milestones=ms,
        ))
    return schemas.StudentDetail(id=student_id, name=name, timeline=timeline, perRating=[])
```

- [ ] **Step 3: Wire endpoint + run test + commit**

```python
@router.get("/students/{student_id}", response_model=schemas.StudentDetail)
def get_student(student_id: str):
    return adapters.student_detail(student_id)
```

```bash
pytest tests/test_api/test_student_detail.py -v
git add src/provectus_analytics/api tests/test_api/test_student_detail.py
git commit -m "wire: /api/students/{id}"
```

---

### Task 6.2: Build Student route

**Files:**
- Modify: `frontend/src/routes/Student.tsx`

- [ ] **Step 1: Read source**

Read `design/tab-student.jsx`. Note: timeline of ratings (gantt-like bars with milestone dots) + per-rating mini-KPI grids with cohort overlay.

- [ ] **Step 2: Implement Student.tsx**

Port the design verbatim. Use `useStudent(id)` from queries. Use `<MiniKpi>` and `<DeltaText>` helpers.

(Full port — copy the JSX, retype, wire to `useStudent`.)

- [ ] **Step 3: Smoke + commit**

```bash
cd frontend && npx tsc --noEmit
git add frontend/src/routes/Student.tsx
git commit -m "wire: Student tab end-to-end"
```

---

## Phase 7 — Instructor tab

### Task 7.1: Implement /api/instructors + /api/instructors/{id}

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/main.py`
- Create: `src/provectus_analytics/api/routers/instructors.py`, `tests/test_api/test_instructors.py`

- [ ] **Step 1: Write failing tests**

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data

def _fresh(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path/"no_exports")
    web_data.build_db(db, force_synthetic=True); web_data.clear_caches()
    return TestClient(create_app())

def test_instructors_list(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    r = c.get("/api/instructors")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)

def test_instructor_detail(tmp_path, monkeypatch):
    c = _fresh(tmp_path, monkeypatch)
    rows = c.get("/api/instructors").json()
    if not rows: return  # synthetic data may have no instructors named
    iid = rows[0]["id"]
    r = c.get(f"/api/instructors/{iid}")
    assert r.status_code == 200
```

- [ ] **Step 2: Implement adapters**

```python
def instructors_list() -> list[schemas.InstructorSummary]:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        rows = conn.execute("""
            SELECT instructor, COALESCE(SUM(length_hrs),0) AS hours,
                   COUNT(DISTINCT student_id) AS students
            FROM flights WHERE instructor IS NOT NULL GROUP BY instructor
            ORDER BY hours DESC
        """).fetchall()
    finally:
        conn.close()
    return [schemas.InstructorSummary(
        id=name, name=name, hours=float(hours), students=int(students), passRate=0.0
    ) for name, hours, students in rows]

def instructor_detail(instructor_id: str) -> schemas.InstructorDetail:
    df = web_data.instructor_detail(str(web_data.DEFAULT_DB), instructor_id)
    students = [
        schemas.ClientRow(
            id=str(row.student) if hasattr(row, 'student') else "", name=row["student"],
            rating=row["rating"], progressPct=1.0, hoursToDate=float(row["hours"] or 0),
            daysEnrolled=int(row["days"] or 0), status="Completed",
        ) for _, row in df.iterrows()
    ]
    return schemas.InstructorDetail(id=instructor_id, name=instructor_id, students=students, perRating=[])
```

- [ ] **Step 3: Wire router + test + commit**

```python
# routers/instructors.py
from fastapi import APIRouter
from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["instructors"])

@router.get("/instructors", response_model=list[schemas.InstructorSummary])
def list_instructors(): return adapters.instructors_list()

@router.get("/instructors/{instructor_id}", response_model=schemas.InstructorDetail)
def get_instructor(instructor_id: str): return adapters.instructor_detail(instructor_id)
```

```bash
pytest tests/test_api/test_instructors.py -v
git add src/provectus_analytics/api tests/test_api/test_instructors.py
git commit -m "wire: /api/instructors and /api/instructors/{id}"
```

---

### Task 7.2: Build Instructor route

**Files:**
- Modify: `frontend/src/routes/Instructor.tsx`

- [ ] **Step 1: Port from design/tab-instructor.jsx**

Wire to `useInstructors()` and `useInstructor(id)`. Show hours logged, students touched, per-rating breakdown.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes/Instructor.tsx
git commit -m "wire: Instructor tab end-to-end"
```

---

## Phase 8 — Flights tab (with override surface)

### Task 8.1: Implement /api/flights GET

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/main.py`
- Create: `src/provectus_analytics/api/routers/flights.py`, `tests/test_api/test_flights.py`

- [ ] **Step 1: Write failing test**

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data

def test_flights_list(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path/"no_exports")
    web_data.build_db(db, force_synthetic=True); web_data.clear_caches()
    c = TestClient(create_app())
    r = c.get("/api/flights")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    if rows:
        assert {"id","date","client","instructor","type","billing","acClass","ground","hours","cost"} <= rows[0].keys()
```

- [ ] **Step 2: Implement adapters.flights()**

```python
def flights(filter: dict) -> list[schemas.FlightRow]:
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        sql = """
          SELECT f.fsp_reservation, f.flight_date, f.client_raw, f.instructor,
                 f.reservation_type, f.billing_category, f.aircraft_class,
                 f.is_ground_lesson, f.length_hrs,
                 COALESCE((SELECT SUM(amount) FROM invoices i WHERE i.fsp_reservation = f.fsp_reservation), 0) AS cost
          FROM flights f WHERE 1=1
        """
        params: list = []
        if filter.get("instructor"):
            sql += " AND instructor = ?"; params.append(filter["instructor"])
        if filter.get("client"):
            sql += " AND client_raw LIKE ?"; params.append(f"%{filter['client']}%")
        if filter.get("ground") == "Flight (0)":
            sql += " AND COALESCE(is_ground_lesson, 0) = 0"
        elif filter.get("ground") == "Ground (1)":
            sql += " AND COALESCE(is_ground_lesson, 0) = 1"
        sort = filter.get("sort", "-date")
        order = "DESC" if sort.startswith("-") else "ASC"
        sql += f" ORDER BY f.flight_date {order} LIMIT 500"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    out: list[schemas.FlightRow] = []
    for res, date, client, instructor, rtype, billing, acclass, is_ground, hours, cost in rows:
        out.append(schemas.FlightRow(
            id=str(res), date=date or "", client=client or "", instructor=instructor or "",
            type=rtype or "Dual flight training",
            billing=_norm_billing(billing),
            acClass=_norm_acclass(acclass),
            ground="Ground (1)" if is_ground else "Flight (0)",
            hours=float(hours or 0), cost=float(cost or 0),
        ))
    return out

def _norm_billing(v):
    if v in ("Hobbs","Tach","Block"): return v
    return "—"

def _norm_acclass(v):
    if v in ("SE_BASIC","SE_COMPLEX","ME_BASIC","HP_COMPLEX"): return v
    return "SE_BASIC"
```

- [ ] **Step 3: Wire router + test + commit**

```python
# routers/flights.py
from fastapi import APIRouter, Query
from .. import adapters, schemas

router = APIRouter(prefix="/api", tags=["flights"])

@router.get("/flights", response_model=list[schemas.FlightRow])
def get_flights(
    instructor: str | None = Query(None),
    client: str | None = Query(None),
    ground: str | None = Query(None),
    sort: str | None = Query("-date"),
):
    return adapters.flights({"instructor": instructor, "client": client, "ground": ground, "sort": sort})
```

```bash
pytest tests/test_api/test_flights.py -v
git add src/provectus_analytics/api tests/test_api/test_flights.py
git commit -m "wire: /api/flights GET with filters"
```

---

### Task 8.2: Implement PATCH /api/flights/{id} (override surface)

**Files:**
- Modify: `src/provectus_analytics/api/adapters.py`, `src/provectus_analytics/api/routers/flights.py`
- Create: `tests/test_api/test_flight_override.py`

- [ ] **Step 1: Write failing test**

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data

def test_override_persists(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path/"no_exports")
    web_data.build_db(db, force_synthetic=True); web_data.clear_caches()
    c = TestClient(create_app())

    flights = c.get("/api/flights").json()
    if not flights: return
    fid = flights[0]["id"]

    r = c.patch(f"/api/flights/{fid}", json={"field": "is_ground_lesson", "value": True})
    assert r.status_code == 200
    after = r.json()
    assert after["ground"] == "Ground (1)"

    # Reading again returns the override
    flights2 = c.get("/api/flights").json()
    target = next(f for f in flights2 if f["id"] == fid)
    assert target["ground"] == "Ground (1)"


def test_override_invalid_field_returns_422(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path/"no_exports")
    web_data.build_db(db, force_synthetic=True); web_data.clear_caches()
    c = TestClient(create_app())
    flights = c.get("/api/flights").json()
    if not flights: return
    r = c.patch(f"/api/flights/{flights[0]['id']}", json={"field": "client_name", "value": "x"})
    assert r.status_code == 422
```

- [ ] **Step 2: Implement adapters.update_flight()**

```python
def update_flight(flight_id: str, patch: schemas.FlightUpdate) -> schemas.FlightRow:
    from .. import ingest, partition, milestones
    conn = sqlite3.connect(web_data.DEFAULT_DB)
    try:
        if patch.value is None:
            ingest.clear_flight_override(conn, flight_id, patch.field)
        else:
            ingest.set_flight_override(conn, flight_id, patch.field, patch.value)
        ingest.apply_overrides(conn)
        partition.partition_flights(conn)
        milestones.compute_milestones(conn)
        conn.commit()
    finally:
        conn.close()
    web_data.clear_caches()
    # Return updated row
    rows = flights({})
    for r in rows:
        if r.id == flight_id:
            return r
    raise LookupError(f"flight {flight_id}")
```

- [ ] **Step 3: Add PATCH endpoint**

```python
# routers/flights.py
@router.patch("/flights/{flight_id}", response_model=schemas.FlightRow)
def update_flight_endpoint(flight_id: str, patch: schemas.FlightUpdate):
    return adapters.update_flight(flight_id, patch)
```

- [ ] **Step 4: Run + commit**

```bash
pytest tests/test_api/test_flight_override.py -v
git add src/provectus_analytics/api tests/test_api/test_flight_override.py
git commit -m "wire: PATCH /api/flights/{id} with override whitelist"
```

---

### Task 8.3: Build Flights route with editable cells

**Files:**
- Modify: `frontend/src/routes/Flights.tsx`
- Create: `frontend/src/components/OverrideMenu.tsx`

- [ ] **Step 1: Read source**

Read `design/tab-flights.jsx`. Editable cells with popovers, dirty-row indicator, override count in topbar.

- [ ] **Step 2: Port OverrideMenu.tsx**

Extract the override popover into its own component. Props:

```tsx
type Props = {
  field: 'is_ground_lesson' | 'billing_category' | 'aircraft_class' | 'reservation_type';
  currentValue: string | boolean;
  onSelect: (value: string | boolean | null) => void;  // null = clear
  onClose: () => void;
};
```

- [ ] **Step 3: Port Flights.tsx**

Compose `useFlights(filter)` + `useUpdateFlight()` mutation. Filter controls at top, editable table with `OverrideMenu` on cell click.

- [ ] **Step 4: Manual smoke**

Start the server, load `/flights`, edit a cell, refresh page, verify override persists.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/Flights.tsx frontend/src/components/OverrideMenu.tsx
git commit -m "wire: Flights tab with editable cell overrides"
```

---

## Phase 9 — Polish (CmdK, Import/Rebuild buttons, error boundary)

### Task 9.1: Implement Import + Rebuild endpoints

**Files:**
- Modify: `src/provectus_analytics/api/routers/meta.py`
- Create: `tests/test_api/test_import_rebuild.py`

- [ ] **Step 1: Write failing tests**

```python
from fastapi.testclient import TestClient
from provectus_analytics.api import create_app
from provectus_analytics.web import data as web_data

def test_rebuild_synthetic(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(web_data, "DEFAULT_DB", db)
    monkeypatch.setattr(web_data, "FSP_EXPORTS_DIR", tmp_path/"no_exports")
    c = TestClient(create_app())
    r = c.post("/api/rebuild?synthetic=true")
    assert r.status_code == 200
    assert "built" in r.json()
```

- [ ] **Step 2: Implement endpoints**

Add to `routers/meta.py`:

```python
from fastapi import Query
from ... import import_exports

@router.post("/import-fsp")
def import_fsp():
    results = import_exports.import_latest()
    web_data.clear_caches()
    built = web_data.build_db(web_data.DEFAULT_DB)
    return {"imported": import_exports.summarize(results), "built": built}

@router.post("/rebuild")
def rebuild(synthetic: bool = Query(False)):
    web_data.clear_caches()
    built = web_data.build_db(web_data.DEFAULT_DB, force_synthetic=synthetic)
    return {"built": built}
```

(Import `web_data` at top of file: `from ..web import data as web_data`.)

- [ ] **Step 3: Run + commit**

```bash
pytest tests/test_api/test_import_rebuild.py -v
git add src/provectus_analytics/api/routers/meta.py tests/test_api/test_import_rebuild.py
git commit -m "wire: POST /api/import-fsp and /api/rebuild"
```

---

### Task 9.2: Build CmdK palette

**Files:**
- Create: `frontend/src/components/CmdK.tsx`
- Create: `frontend/src/components/CmdK.test.tsx`

- [ ] **Step 1: Read source**

Find `<CmdK>` in `design/panels.jsx`. Lists nav, range presets, theme toggle, import, rebuild. Arrow keys + enter to select.

- [ ] **Step 2: Port + wire**

Props:

```tsx
type Props = {
  open: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
  onSetRange: (r: RangeKey) => void;
  onToggleTheme: () => void;
  onImport: () => void;
  onRebuild: (synthetic: boolean) => void;
};
```

Port the markup from source. Add `Rebuild (synthetic)` as a separate item.

- [ ] **Step 3: Wire in App.tsx**

```tsx
const importMut = useImportFsp();
const rebuildMut = useRebuild();

<CmdK
  open={cmdkOpen}
  onClose={() => setCmdkOpen(false)}
  onNavigate={(path) => { navigate(path); setCmdkOpen(false); }}
  onSetRange={(r) => { setRange(r); setCmdkOpen(false); }}
  onToggleTheme={() => { toggleTheme(); setCmdkOpen(false); }}
  onImport={() => { importMut.mutate(); setCmdkOpen(false); }}
  onRebuild={(synth) => { rebuildMut.mutate({ synthetic: synth }); setCmdkOpen(false); }}
/>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/CmdK.tsx frontend/src/components/CmdK.test.tsx frontend/src/App.tsx
git commit -m "wire: ⌘K command palette"
```

---

### Task 9.3: Wire sidebar Import + Rebuild buttons + notifications stub

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`, `frontend/src/components/Topbar.tsx`
- Create: `frontend/src/components/NotificationsPopover.tsx`

- [ ] **Step 1: Wire Import button in Sidebar + Topbar**

Pass `onImport` from `App.tsx` (`importMut.mutate`) through to both. Show a small status indicator (`importMut.isPending ? 'Importing…' : null`).

- [ ] **Step 2: Add Rebuild button to Sidebar foot**

Sidebar already has the spot. Wire it.

- [ ] **Step 3: Build NotificationsPopover stub**

```tsx
type Props = { open: boolean; onClose: () => void };

export function NotificationsPopover({ open, onClose }: Props) {
  if (!open) return null;
  return (
    <div className="notif-popover">
      <div className="notif-empty">All caught up</div>
      <button onClick={onClose}>Close</button>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components frontend/src/App.tsx
git commit -m "wire: Sidebar/Topbar Import + Rebuild + notifications stub"
```

---

### Task 9.4: Add ErrorBoundary

**Files:**
- Create: `frontend/src/components/ErrorBoundary.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Build ErrorBoundary**

```tsx
import { Component, type ReactNode } from 'react';

type State = { error: Error | null };

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };
  static getDerivedStateFromError(error: Error): State { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div className="error-screen">
          <h2>Something broke</h2>
          <pre>{this.state.error.message}</pre>
          <button onClick={() => window.location.reload()}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: Wrap App content**

In `App.tsx`, wrap the `<Routes>` block with `<ErrorBoundary>`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ErrorBoundary.tsx frontend/src/App.tsx
git commit -m "add: ErrorBoundary around routes"
```

---

## Phase 10 — Packaging + boss launcher

### Task 10.1: Update Provectus.command launcher

**Files:**
- Modify: `Provectus.command`

- [ ] **Step 1: Read current launcher**

```bash
cat "/Users/olsend/Documents/Provectus Analytics/Provectus.command"
```

- [ ] **Step 2: Update to launch uvicorn**

Replace the launch command. Where current launcher runs `python app.py`, change to:

```bash
"${VENV}/bin/python" -m uvicorn provectus_analytics.api.main:app --host 127.0.0.1 --port 8050 &
SERVER_PID=$!
sleep 1
open "http://127.0.0.1:8050"
wait $SERVER_PID
```

Keep the venv-bootstrap logic intact. Ensure `requirements.txt` has been updated to include `fastapi`, `uvicorn[standard]`.

- [ ] **Step 3: Smoke test in clean tmp venv**

```bash
cp Provectus.command /tmp/test_launcher.command
chmod +x /tmp/test_launcher.command
# Run manually, observe browser opens to the new UI
```

- [ ] **Step 4: Commit**

```bash
git add Provectus.command requirements.txt
git commit -m "wire: Provectus.command launcher uses uvicorn + new API"
```

---

### Task 10.2: Update dist packaging script

**Files:**
- Modify: `tools/` (whatever script builds dist/Provectus Analytics.zip — find it first)

- [ ] **Step 1: Find packaging script**

```bash
ls "/Users/olsend/Documents/Provectus Analytics/tools/"
grep -r "Provectus Analytics.zip" .
```

- [ ] **Step 2: Update zip include/exclude**

Ensure the zip:
- Includes `frontend/dist/`
- Excludes `frontend/node_modules/`, `frontend/src/`, `frontend/index.html`, `frontend/package*.json`, `frontend/tsconfig*`, `frontend/vite.config.ts`
- Includes the new `src/provectus_analytics/api/`
- Continues to exclude `.git/`, `.venv/`, `tests/`

- [ ] **Step 3: Build + verify**

Run the packaging script. Inspect the resulting zip contents.

- [ ] **Step 4: Commit**

```bash
git add tools/
git commit -m "package: include frontend/dist in distribution zip"
```

---

### Task 10.3: Full end-to-end boss smoke test

- [ ] **Step 1: Build everything from scratch**

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
rm -rf .venv frontend/dist
cd frontend && npm install && npm run build && cd ..
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

- [ ] **Step 2: Launch via Provectus.command**

Double-click. Verify browser opens to the new UI. Click through all 5 tabs. Set an override in Flights. Click Rebuild. Click Import (will no-op on synthetic).

- [ ] **Step 3: If anything is broken, fix it, commit, re-test**

---

## Phase 11 — Decommission Dash

### Task 11.1: Move web/data.py to api/queries.py

**Files:**
- Create: `src/provectus_analytics/api/queries.py` (renamed from `web/data.py`)
- Modify: `src/provectus_analytics/api/adapters.py` (update imports)

- [ ] **Step 1: Move the file**

```bash
git mv src/provectus_analytics/web/data.py src/provectus_analytics/api/queries.py
```

- [ ] **Step 2: Update all imports**

Find every `from ..web import data as web_data` and `from ..web.data import ...`. Replace with imports from `api.queries`.

```bash
grep -rn "web.data\|web import data" src/ tests/
```

Update each match.

- [ ] **Step 3: Run all tests**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/provectus_analytics
git commit -m "refactor: move web/data.py to api/queries.py"
```

---

### Task 11.2: Delete legacy Dash code

**Files:**
- Delete: `app.py`, `src/provectus_analytics/web/`

- [ ] **Step 1: Sanity check — confirm new app fully working**

(If you skipped Task 10.3, do it now.)

- [ ] **Step 2: Delete**

```bash
git rm app.py
git rm -r src/provectus_analytics/web
```

- [ ] **Step 3: Remove Dash from requirements.txt**

Edit `requirements.txt`, remove the `dash` line and any Dash-only deps.

- [ ] **Step 4: Run all tests**

```bash
pytest -v
```

- [ ] **Step 5: Commit**

```bash
git add app.py src/provectus_analytics/web requirements.txt
git commit -m "remove: legacy Dash app and src/provectus_analytics/web/"
```

---

### Task 11.3: Update ROADMAP.md

**Files:**
- Modify: `ROADMAP.md`

- [ ] **Step 1: Add Phase 10 entry**

Add to ROADMAP.md just before "Phase 10 — Public transparency view":

```markdown
### Phase 9.7 — React + FastAPI rewrite ✓

Replaced the Dash UI with a Vite + React 18 + TypeScript frontend backed by a FastAPI app that wraps the existing Python pipeline. Boss distribution model preserved (prebuilt dist/ shipped in zip, `.command` launcher → uvicorn → 127.0.0.1:8050). Phase 9.5 override surface (editable Flights cells → `set_flight_override` + partition/milestones rerun) preserved end-to-end. Hand-rolled SVG charts ported from the Claude Design hi-fi handoff (`design_handoff_provectus_analytics/`).

Spec: `docs/superpowers/specs/2026-05-25-dash-to-react-rewrite-design.md`
Plan: `docs/superpowers/plans/2026-05-25-dash-to-react-rewrite.md`
```

Update the "Status snapshot" line at top:

```markdown
- **Phase 9.7 (React + FastAPI rewrite) — done.** Dash is gone; frontend is Vite+React+TS, backend is FastAPI. All 5 tabs at parity. Boss launcher unchanged.
```

- [ ] **Step 2: Commit**

```bash
git add ROADMAP.md
git commit -m "docs: add Phase 9.7 React+FastAPI rewrite to ROADMAP"
```

---

## Done criteria

All checked when:

- [ ] `pytest -v` passes 100% (backend)
- [ ] `cd frontend && npx vitest run` passes 100% (frontend)
- [ ] `cd frontend && npx tsc --noEmit` passes (no TS errors)
- [ ] Manual smoke: `Provectus.command` boots in a clean venv on a fresh checkout, opens browser, all 5 tabs render with synthetic data
- [ ] Flights override: set value, refresh page, override persists; clear override, refresh, original value back
- [ ] Import button: with real FSP exports in `FSP Exports/`, click → DB rebuilds with real data, Live pill turns green
- [ ] Theme toggle persists across reload
- [ ] Keyboard shortcuts: ⌘K, ⌘\, ⌘⇧T, O/R/S/I/F work as designed
- [ ] No console errors on any tab
- [ ] `app.py` and `src/provectus_analytics/web/` are deleted; only `src/provectus_analytics/api/` + `src/provectus_analytics/{ingest,partition,milestones,norms,...}/` remain on the Python side
