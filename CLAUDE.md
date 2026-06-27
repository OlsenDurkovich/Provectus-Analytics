# Provectus Analytics

Python analytics web app pulling data from Flight Schedule Pro (FSP) to measure cost, duration, flight hours, and event counts per student/rating/milestone. Goal: improve course + instructor efficiency, and produce a public cost-transparency view.

**The roadmap is the source of truth — read it first:** `ROADMAP.md` in this folder.

## Current phase
**Railway deployment + real-data load.** The Phase 10–14 website-migration *code* is done: all five phases (real-survey ingest, JWT auth, upload endpoint, Railway/Docker/WAL config, security hardening) are merged into `main` and pushed (PRs #3,#8,#4,#5,#6). Docker build smoke-tested 2026-06-27 (both stages replicated clean; `npm ci` pin applied). Working doc: [MIGRATION.md](MIGRATION.md). **What's left is not code:** (1) provision Railway in the dashboard (volume at `/data`, set `SECRET_KEY` + initial-admin env vars, deploy); (2) custom domain; (3) load real `alumni_survey.xlsx` — it currently holds ~20 synthetic-shaped rows, real responses still landing (waiting on Seanna Glatzel). Pipeline/dashboard still run on synthetic data until then. Phases 1–9.7 complete.

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
