# Provectus Analytics

Python analytics web app pulling data from Flight Schedule Pro (FSP) to measure cost, duration, flight hours, and event counts per student/rating/milestone. Goal: improve course + instructor efficiency, and produce a public cost-transparency view.

**The roadmap is the source of truth — read it first:** `ROADMAP.md` in this folder.

## Current phase
Phase 2 — FSP data discovery. Confirm API vs export access, enumerate per-event fields, identify all billing categories beyond "primary."

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
- Framework choice (Streamlit vs Flask) deferred to Phase 7 — don't commit prematurely.
