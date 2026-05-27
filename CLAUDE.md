# Provectus Analytics

Python analytics web app pulling data from Flight Schedule Pro (FSP) to measure cost, duration, flight hours, and event counts per student/rating/milestone. Goal: improve course + instructor efficiency, and produce a public cost-transparency view.

**The roadmap is the source of truth — read it first:** `ROADMAP.md` in this folder.

## Current phase
**Website migration (Phases 10–14)** — moving from local `.command` launcher to a hosted Railway deployment with auth. Working doc: [MIGRATION.md](MIGRATION.md). Pipeline + dashboard are built against synthetic data; real alumni survey responses are landing now (Phase 10.2). Phases 1–8.6 + Phase 9 (Claude-in-Chrome automation) + Phase 9.5 (incremental ingest + per-flight override surface) complete.

## Key context (already locked, don't re-litigate)
- Ratings covered: PPL, IFR, ASEL COM, AMEL, CFI, CFII, MEI.
- Scale: ~50 alumni for historical survey; future students collected via FSP automation.
- Milestones per rating: see ROADMAP.md Phase 1.
- **Core data problem:** every training flight is labeled "dual flight training" in FSP; PPL/IFR/ASEL COM all billed as "primary." Rating attribution is the hardest engineering problem — see ROADMAP.md Phase 2.5.
- Alumni survey's primary job is collecting rating-boundary dates to enable historical attribution.

## Working preferences
- Be brief, no filler or trailing summaries.
- Flag guesses explicitly.
- GitHub pushes are manual — confirm before `git push`.
- Web framework: **FastAPI + Vite + React 19 + TypeScript** (replaced Dash in Phase 10, May 2026). Backend factory at `src/provectus_analytics/api/main.py`; frontend under `frontend/`. Launch locally via `Provectus.command` (double-click) or `python -m uvicorn provectus_analytics.api.main:app`. Frontend dev server: `cd frontend && npm run dev`. Production build: `cd frontend && npm run build` (output served by FastAPI via `StaticFiles` + SPA fallback).
