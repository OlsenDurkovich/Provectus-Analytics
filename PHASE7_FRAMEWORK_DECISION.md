# Phase 7 — Framework decision

**Decision (2026-05-24): Streamlit + Plotly.**

## Why Streamlit (not Flask)

- **Solo build, internal users first.** The MVP audience is the boss reviewing PPL norms. No public-facing requirements until Phase 10, and even then the cohort view can be statically exported.
- **Minimal web code.** Streamlit reads like a Python script — no routes, no templates, no JS. Faster iteration on what to display while we're still figuring out which metrics actually matter.
- **Plotly bundled.** Interactive box plots, histograms, scatter overlays without picking a charting library separately.
- **Caching primitives** (`st.cache_data`) handle the DB-read-on-every-rerun problem out of the box.
- **Deployable later** to Streamlit Community Cloud (free) or behind a corp VPN with one Dockerfile.

## When to revisit (switch to Flask + Plotly)

- We need real authentication beyond basic password gating.
- We need URL routing for shareable per-student permalinks.
- We need to serve the public transparency view (Phase 10) at a custom domain with branded styling.
- Streamlit's rerun-on-every-interaction model starts hurting performance with the real dataset.

None of those apply today. Defer.

## What's built in this phase

- `app.py` at repo root — Streamlit entry (`streamlit run app.py`)
- `src/provectus_analytics/dashboard.py` — page code
- Auto-builds `provectus.db` from synthetic CSVs on first launch
- Sidebar: PPL alum picker, rebuild-DB button
- Page sections:
  1. Cohort overview (4 metric cards: n alumni, median hours, median cost, median days)
  2. Cohort distribution — box plots for hours / cost / days with selected student as a point
  3. Selected student trajectory — milestone table with delta vs cohort median

PPL only, per ROADMAP. Other ratings come in Phase 8.
