# Dash → React + FastAPI rewrite

**Date:** 2026-05-25
**Status:** Approved (user delegated technical approval)
**Owner:** Olsen
**Implementation start:** immediate, incremental

## Goal

Replace the Dash app at `app.py` + `src/provectus_analytics/web/` with a Vite+React+TypeScript frontend backed by a FastAPI service that wraps the existing Python data pipeline. Visual source of truth is the hi-fi prototype in `design_handoff_provectus_analytics/`. The boss distribution model (`Provectus.command` launcher → Python venv → browser on `127.0.0.1:8050`) is preserved.

The Dash app stays runnable on its current port until the new app reaches parity. Cutover is one tab at a time: Overview → Rating Detail → Student → Instructor → Flights.

## Non-goals

- No auth / login / account screens. Boss-only local-deploy.
- No public transparency view (that's Phase 10).
- No swap of the hand-rolled SVG charts for a chart library.
- No new analytical features. This is a UI shell rewrite; data semantics are unchanged.
- No Node toolchain on the boss's Mac — React is prebuilt on dev side.

## Locked decisions

| Choice | Pick | Reason |
|---|---|---|
| Frontend framework | Vite + React 18 + TypeScript | Handoff was authored to be ported as-is. |
| Backend framework | FastAPI | Type-driven JSON + Pydantic schemas align with TS frontend. |
| Rollout | Incremental, Overview tab first | Lower risk; each tab independently shippable. |
| Build location | Prebuild on dev, ship `dist/` in zip | Boss never installs Node. |
| UI scope | Match handoff exactly | Includes ⌘K palette, keyboard shortcuts, notifications popover, pinned reports. |
| State management | `useState` + `@tanstack/react-query` | Per handoff §3; no Redux/Zustand. |
| Charts | Hand-rolled SVG, port verbatim | Per handoff §3 and §10. |
| Styling | Plain CSS + CSS custom properties, port `styles.css` once | Per handoff §3 and §AGENTS.md ground rule 3. |
| Router | `react-router-dom@6` | Per handoff §3. |
| Sample data | Stays as typed seed module until backend is wired | Per handoff §1. |

## Architecture

### Repo layout (after rewrite)

```
Provectus Analytics/
├── app.py                          # legacy Dash entry; kept until cutover complete
├── frontend/                       # NEW
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts              # /api → http://127.0.0.1:8050 proxy in dev
│   ├── src/
│   │   ├── main.tsx, App.tsx
│   │   ├── styles/styles.css       # ported verbatim from design/styles.css
│   │   ├── components/
│   │   │   ├── primitives/{Sparkline,Delta,Skel}.tsx
│   │   │   ├── Icon.tsx
│   │   │   ├── Sidebar.tsx, Topbar.tsx, KpiGrid.tsx, ClientsTable.tsx, CmdK.tsx
│   │   │   ├── DateRangePicker.tsx, NotificationsPopover.tsx
│   │   │   ├── charts/{RatingBars,RatingsList,Heatmap}.tsx
│   │   │   └── helpers/{Select,BigKpi,MiniKpi,DeltaText}.tsx
│   │   ├── routes/{Overview,RatingDetail,Student,Instructor,Flights}.tsx
│   │   ├── data/{client,queries,types}.ts
│   │   └── hooks/{useTheme,useShortcuts,usePersistedTab,useRange}.ts
│   └── dist/                       # build output, gitignored, shipped in zip
├── src/provectus_analytics/
│   ├── api/                        # NEW
│   │   ├── __init__.py             # create_app() factory
│   │   ├── main.py                 # uvicorn entry; mounts frontend/dist/ at /
│   │   ├── routers/
│   │   │   ├── meta.py             # GET /api/meta, POST /api/import-fsp, POST /api/rebuild
│   │   │   ├── kpis.py             # GET /api/kpis
│   │   │   ├── ratings.py          # GET /api/ratings, /api/ratings/{code}, /api/ratings/completed, /api/heatmap
│   │   │   ├── students.py         # GET /api/students, /api/students/{id}
│   │   │   ├── instructors.py      # GET /api/instructors, /api/instructors/{id}
│   │   │   └── flights.py          # GET /api/flights, PATCH /api/flights/{id}
│   │   ├── schemas.py              # Pydantic v2 models — source of truth for the contract
│   │   └── adapters.py             # reshapes web/data.py output → schemas
│   ├── web/                        # legacy Dash; unchanged
│   └── (ingest, partition, ...)    # unchanged
├── tests/
│   ├── test_api/                   # NEW — Pytest + httpx
│   └── (existing tests)            # unchanged
├── Provectus.command               # updated to launch uvicorn
└── docs/superpowers/specs/         # this file
```

### Processes

**Dev:**
- `uvicorn provectus_analytics.api.main:app --reload --port 8050` (Python)
- `npm run dev` (Vite on `:5173` with HMR; proxies `/api/*` to `:8050`)
- Two terminals (or one `make dev`).

**Prod (boss):**
- One process. `Provectus.command` activates venv, runs `uvicorn ... --port 8050`.
- FastAPI serves `frontend/dist/` at `/` (StaticFiles, html=True) and JSON at `/api/*`.
- Launcher opens `127.0.0.1:8050` in the default browser.

### Module boundaries

- `api/routers/` only knows Pydantic schemas + `api/adapters.py`. No raw SQL.
- `api/adapters.py` is the *only* place that calls into `web/data.py` and the pipeline modules. The seam where pandas → typed dicts → JSON happens.
- `frontend/src/data/client.ts` is the *only* place that talks to `/api/*`. Components consume hooks (`useKpis(range)`), never raw URLs.
- `styles.css` ported once; the prototype copy stays as reference but isn't edited.
- Existing pipeline modules (`ingest`, `partition`, `milestones`, `norms`, `guesstimate`, `reconcile`) are untouched.

## API surface

All endpoints under `/api`. Schemas in `api/schemas.py` mirror `frontend/src/data/types.ts` (the type contract in handoff `AGENTS.md`).

| Method | Path | Query / body | Returns |
|---|---|---|---|
| GET | `/api/meta` | — | `{ mode: 'real'\|'synthetic', liveClientCount, dataState }` |
| POST | `/api/import-fsp` | — | `{ imported: [...], built: {...} }` |
| POST | `/api/rebuild` | `?synthetic=true` optional | `{ built: {...} }` |
| GET | `/api/kpis` | `range` | `Kpi[]` |
| GET | `/api/ratings` | `metric`, `range` | `RatingBarPoint[]` |
| GET | `/api/ratings/{code}` | `range` | `RatingDetail` |
| GET | `/api/ratings/completed` | `range` | `{ rating, count }[]` |
| GET | `/api/heatmap` | `range` | `{ rows: number[][], buckets: string[] }` |
| GET | `/api/students` | `range`, `rating?` | `ClientRow[]` |
| GET | `/api/students/{id}` | — | `StudentDetail` |
| GET | `/api/instructors` | — | `InstructorSummary[]` |
| GET | `/api/instructors/{id}` | — | `InstructorDetail` |
| GET | `/api/flights` | `instructor?`, `client?`, `ground?`, `sort?` | `FlightRow[]` |
| PATCH | `/api/flights/{id}` | `{ field, value }` | `FlightRow` |

PATCH `field` is a `Literal['is_ground_lesson','billing_category','aircraft_class','reservation_type']` — out-of-whitelist requests return 422. `value: null` clears the override.

## Data flow

### Read

```
React component
  └─ useKpis(range)                                # React Query hook
       └─ client.getKpis(range)                    # frontend/src/data/client.ts
            └─ fetch('/api/kpis?range=12mo')
                 └─ FastAPI router (kpis.py)
                      └─ adapters.kpis(range)
                           └─ web/data.py queries
                                └─ SQLite (provectus.db)
            ← list[Kpi] (Pydantic-serialized JSON)
       ← Kpi[] (typed)
  ← { data, isLoading, error }
```

- Query keys: `['kpis', range]`, `['clients', range, rating]`, `['student', id]`, etc.
- React Query `isLoading` drives the handoff's 380ms shimmer (`<Skel>` components).
- Default React Query staleness is fine. Rebuild/Import mutations invalidate everything.

### Write (Flights override)

```
User clicks editable cell → OverrideMenu pops, picks value
  └─ useUpdateFlight().mutate({ id, field, value })
       └─ PATCH /api/flights/{id}  body: { field, value }
            └─ flights router → adapters.update_flight
                 ├─ ingest.set_flight_override / clear_flight_override
                 ├─ partition.partition_flights
                 └─ milestones.compute_milestones
            ← updated FlightRow
       ← invalidate ['flights', ...] + ['students', studentId] + ['kpis', ...]
```

- Synchronous. Optimistic update on the row; rollback on error.
- `partition` + `milestones` re-runs are kept full-pipeline for simplicity (matches current Dash behavior). Scope to a single student later if it gets slow.

### Mode + data-state

- `GET /api/meta` returns mode (real vs synthetic), live client count for the Live pill, and the data-state row counts.
- Frontend fetches on mount; refetches after successful Import or Rebuild.

### Import / Rebuild

- `POST /api/import-fsp` wraps the [web/app.py:179-201](../../../src/provectus_analytics/web/app.py) callback verbatim. Long-ish (seconds) but synchronous — matches Dash today.
- `POST /api/rebuild?synthetic=true|false` exposes both the real and synthetic rebuild paths. "Rebuild (synthetic)" moves out of the sidebar and into the `⌘K` command palette as a dev escape hatch.
- On success, the frontend invalidates all queries.

### State ownership

| State | Owner | Persistence |
|---|---|---|
| Current route | URL via `react-router-dom` | `pv-tab` localStorage (mirror) |
| Theme | `useTheme()` | `pv-theme` localStorage |
| Sidebar collapsed | local in `<App>` | none |
| Date range | local in `<App>` | none |
| Selected metric (hrs/cost/days) | local in `<Overview>` | none |
| Focused rating filter | local in `<Overview>` | none |
| Focused KPI | local in `<Overview>` | none |
| `cmdkOpen`, `notifOpen` | local in `<App>` | none |
| Server data | React Query cache | none |

## Type contract

Two locations, must match:

- **Source of truth:** `api/schemas.py` (Pydantic v2, validated at runtime on every response).
- **TS mirror:** `frontend/src/data/types.ts` (hand-maintained initially).

If drift becomes painful, add `openapi-typescript` as a dev dep and codegen `types.ts` from FastAPI's OpenAPI schema on `npm run build`. Not required for initial cutover.

## Error handling

### Backend

- Custom FastAPI exception handlers:
  - `KeyError` / `LookupError` → 404 with `{ error, detail }`.
  - `ValueError` → 400.
  - Pydantic validation → 422 (FastAPI default).
  - Anything else → 500, logged with traceback.
- No external error reporting (Sentry etc.) — boss-local-only deploy.
- Server logging via `logging` module, INFO level, stdout. Uvicorn handles access logs.

### Frontend

- React Query error states surface as card-level error banners (small red text + retry button, mirrors `<Skel>` placement).
- Whole-page crashes caught by an `<ErrorBoundary>` in `App.tsx` showing a fallback with a reload button.
- Mutation failures roll back optimistic updates and show an inline error.
- No global toast library yet — inline messages suffice for the boss-local context.

## Testing

### Backend

- Pytest + `httpx.AsyncClient` against a TestClient instance.
- One test file per router. Each test builds a fresh synthetic DB in `/tmp` using existing `build_db()` fixtures from `tests/`.
- Override the FastAPI dependency that yields the DB path to point at the temp DB.
- Type check: `mypy` on `src/provectus_analytics/api/`. Strictness level matches the rest of the project.

### Frontend

- Vitest + React Testing Library.
- Smoke test per route: renders without crash, calls expected query.
- Hand-rolled SVG charts are visually verified against `screenshots/`, not unit-tested.
- Type check: `tsc --noEmit` on every PR.

### CI

- Existing GitHub Actions stays; add `npm ci && npm run build && npm run test` step.
- Build step is the de-facto type check.

### Manual verification per tab

Before declaring a tab done, check against the corresponding screenshot in `design_handoff_provectus_analytics/screenshots/`:

- Pixel-identical at 1440×900 in dark mode.
- Light mode toggles cleanly.
- Hover/active/focus states match.
- Keyboard shortcut for the tab works.
- Loading shimmer appears ~380ms on range change.
- Numbers align in columns (tabular-nums working).

## Implementation order

1. **Scaffold + shell** — Vite app, FastAPI app, port `styles.css`, port `icons.jsx` + primitives, wire `<Sidebar>` + `<Topbar>`, theme + shortcuts. End state: empty body, sidebar + topbar visible, theme toggle works.
2. **`/api/meta` end-to-end** — endpoint + frontend hook + data-state block + Live pill. Validates the seam.
3. **Overview tab** — `/api/kpis`, `/api/ratings` (cohort bars), `/api/ratings/completed`, `/api/heatmap`, `/api/students` (clients table). Charts ported, KPI focus interaction, range picker. End state: Overview renders against real data; pixel-diff against `01-overview-dark.png`.
4. **Rating detail** — `/api/ratings/{code}`. BigKpi grid + cohort overlay + methodology disclosure.
5. **Student** — `/api/students/{id}`. Timeline + per-rating mini-KPIs.
6. **Instructor** — `/api/instructors`, `/api/instructors/{id}`.
7. **Flights** — `/api/flights` + PATCH endpoint + OverrideMenu. End-to-end test: set override → refresh → override persists.
8. **CmdK palette** — wire after all routes exist so palette items are real.
9. **Boss launcher + packaging** — swap `Provectus.command` from Dash to uvicorn. Update the `dist/Provectus Analytics.zip` packaging step to include `frontend/dist/` and exclude `frontend/node_modules/` and `frontend/src/`. Verify first-run venv bootstrap still works. Update `Read Me First.pdf` if anything user-visible changed.
10. **Decommission Dash** — once parity is hit and verified, move `src/provectus_analytics/web/data.py` to `src/provectus_analytics/api/queries.py` (it's the only `web/` module still in use; the rest are Dash-specific), update adapter imports, then delete `app.py` + the rest of `src/provectus_analytics/web/`.

## Open product questions (will surface during implementation)

- **Notifications**: handoff has a bell + popover but no backend concept. Plan: stub it (empty state showing "All caught up"). Will flag if user wants real notifications wired to something.
- **Pinned reports**: same — handoff shows 4 sample chips. Plan: stub with localStorage-backed pinning (no server side). Will flag.
- **Notifications dot**: handoff shows a red dot. Plan: hide until there's a real notification system.

## Risk register

| Risk | Mitigation |
|---|---|
| Type drift between Pydantic schemas and TS mirror | mypy + tsc in CI; add `openapi-typescript` if it hurts |
| Boss's first-run after launcher update fails | Test the launcher in a clean venv before shipping; keep Dash launcher behind a `--legacy` flag for one release |
| Real-data shape doesn't match handoff sample shape | Adapters do the reshaping; flagged in [api/adapters.py] if anything is missing — surface as a real product question |
| Override mutation rerunning full partition/milestones is slow | Measure first; scope to single-student rerun if median latency > 1s |
| Vite dev server proxy flaky on the user's setup | Document the two-terminal dev flow; provide `make dev` wrapper |
