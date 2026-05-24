# Provectus Analytics — Roadmap

**Goal:** Pull data from Flight Schedule Pro (FSP) to track total cost, training duration, flight hours billed, and event counts across ratings (PPL, IFR, ASEL COM, AMEL, CFI, CFII, MEI). Compare individual students to norms at each milestone. Use it internally for course/instructor efficiency and externally for cost-transparency marketing.

## Status snapshot (2026-05-24)

- **Phase 1 (schema) — done.** Metrics + milestones locked, see below.
- **Phase 2 (FSP discovery) — done.** Reporting Hub is the data path. No Training Hub at Provectus, so no course/enrollment data in FSP. API path investigated but deferred (no subscription).
- **Phase 3 (alumni data collection) — plan written, awaiting boss sign-off + outreach send.** See `ALUMNI_DATA_COLLECTION_PLAN.md`. Synthetic test data substituting until real responses arrive — see `SYNTHETIC_DATA_README.md`.
- **Phase 4 (name reconciliation + rating attribution) — done against synthetic data.** Code in `src/provectus_analytics/{reconcile,partition}.py`. End-to-end test asserts output matches `ground_truth_per_milestone.csv` exactly.
- **Phase 5 (data model) — done.** SQLite via `src/provectus_analytics/{schema,db}.py`. Tables: students, ratings, enrollments, milestones, flights, invoices, surveys.
- **Phase 6 (cleaning + norms) — done.** `src/provectus_analytics/norms.py`. Tukey-fence outlier filter, median + P25/P75, low-sample flag at n<10.
- **Phase 7 (MVP dashboard) — done for PPL.** Streamlit + Plotly; see `PHASE7_FRAMEWORK_DECISION.md`. Launch: `streamlit run app.py`. Cohort overview + box plot distributions + selected-student trajectory vs cohort median.
- **Phase 8 (full web app) — done.** All 7 ratings. Pages: All Ratings overview, Rating Detail (with date-range filter + student overlay), Student drill-down (all ratings + vs-cohort delta), Instructor view (student list + efficiency vs cohort norms). No auth (boss-only access; add later if needed). Still on synthetic data.
- All subsequent phases below.

## Data path decision (locked)

**Reporting Hub UI exports (manual CSV/XLSX), not the API.** Reporting Hub Basic is included with their existing subscription. API access wasn't pursued because (a) no subscription, (b) pricing not public, (c) export path is sufficient for current scale. Automation cadence (live pulls vs scheduled) is a future problem, possibly solved by Claude-driven export later. Not blocking.

---

## Phases

### Phase 1 — Schema (locked) ✓

Ratings: PPL, IFR, ASEL COM, AMEL, CFI, CFII, MEI.

Milestones per rating:

- **PPL:** start → first solo → XC solos completed → initial checkride
- **IFR:** start → XC PIC time-building completed → initial checkride
- **ASEL COM:** start → initial checkride
- **AMEL:** start → initial checkride
- **CFI:** start → initial checkride
- **CFII:** start → initial checkride
- **MEI:** start → initial checkride

Metrics per milestone: cumulative flight hours, cumulative cost, calendar days from rating start, number of events.

---

### Phase 2 — FSP discovery (done) ✓

See `PHASE2_FSP_FIELD_MEMO.md` for full memo. Headline:

- Provectus uses Scheduling Hub + Billing Hub (no Training Hub).
- Reporting Hub Basic is available. Relevant reports: Reservation Detail, Invoice Detail, Flight Detail, Sales by Client, Analyze Reservations.
- Reservation types in use at Provectus: **Check Ride, Dual Flight Training, Introductory Flight, Maintenance, Owner Flight, Student Solo**. Solos and checkrides are distinctly typed (correction to prior assumption that everything was "dual flight training").
- Per-flight fields available: date, type, client(s), aircraft (tail + make + model), instructor, length (hrs), status, reservation #, flight #.
- No course/enrollment/rating tag on flights — that's the gap the alumni survey fills.

---

### Phase 3 — Alumni data collection (CURRENT, boss priority)

**Deliverable:** Google Form survey to ~50 alumni capturing rating boundary dates + consent.
**Doc:** `ALUMNI_DATA_COLLECTION_PLAN.md` — covers field list, mechanic, outreach cadence, timeline, risks, open decisions.

Survey collects: per-rating start + checkride dates (month/year), plus PPL/IFR sub-milestones. Three-week outreach: email → reminder → phone follow-up.

Why this comes first: without rating-boundary dates, historical "Dual Flight Training" flights can't be attributed to a specific rating, which means we can't compute per-rating norms — the whole project's core deliverable.

---

### Phase 4 — Name reconciliation + rating attribution

Once survey responses are in:

1. Match each alum's name to their FSP client name (manual; ~50 rows).
2. Partition each alum's flights into rating buckets using their reported boundary dates as `[start, checkride]` windows.
3. Resolve concurrent-rating overlaps (ASEL COM + AMEL, CFI + CFII) using aircraft SE/ME from the Aircraft column.
4. Sanity-check: every flight should fall into exactly one rating bucket OR be excluded (Maintenance, Owner Flight, Introductory Flight).

**Validation:** spot-check 5–10 alumni's bucketed data with them on a call. If error rate is bad (>10%), revisit partitioning rules.

---

### Phase 5 — Data model & local store

Tables: students, ratings, enrollments (alum-reported windows), milestones, flights (per-reservation row from Reporting Hub export), invoices (cost line items), surveys.

SQLite. Python's `sqlite3` or SQLAlchemy. Small dataset, zero ops, file lives in the repo.

---

### Phase 6 — Cleaning + norm methodology

Define before visualizing:
- Outlier rule (probably >1.5× IQR).
- Central measure: median (more honest than mean for skewed training data).
- Spread: P25–P75 band (more useful than ±stddev).
- Minimum sample size per rating before publishing a norm (probably ≥10).
- Handling of transfer/prior-PPL students (separate cohort or excluded — boss decision).

Document the rules — the transparency story relies on defensibility.

---

### Phase 7 — MVP dashboard (PPL only, local)

Pick framework: **Streamlit** (recommended — fastest path for a solo build, minimal web code) vs **Flask + Plotly** (full control, deferred). Pick at start of this phase, document the why.

Build smallest useful view: PPL cost/hours/duration distribution + a single student plotted against the norm. Validates the data pipeline, methodology, and framework choice before scaling to all ratings.

---

### Phase 8 — Full web app ✓

Expanded to all 7 ratings. Four pages: All Ratings overview, Rating Detail (date filter + student overlay), Student drill-down, Instructor view (student list + efficiency vs cohort). Auth deferred — not needed yet.

---

### Phase 9 — Automation (deferred)

Manual CSV export from Reporting Hub is the working assumption. Revisit later: options include (a) Claude-driven scheduled export via Chrome, (b) upgrading to Reporting Hub Advanced for scheduled email reports, (c) revisiting API access if Provectus's plan changes. Not blocking until weekly export becomes a pain.

---

### Phase 10 — Public transparency view

Anonymized public page: "the average PPL at Provectus costs $X and takes Y hours, P25–P75 band shown." Marketing asset. Flows from the same data store, conditional on alumni having opted in via the consent checkbox in Phase 3.

---

## Open questions

- Incentive for survey responders (gift card y/n) — boss decision.
- Who signs the outreach email — boss or principal, not "Provectus Analytics."
- How to handle students who completed only part of a rating at Provectus (transferred in/out).
- Whether to instrument current/future students with instructor-side rating tagging at lesson logging time — separate workstream, doesn't block historical analysis.
- Invoice Detail report column inventory — not yet done; needed for Phase 4 cost partitioning.

## Reminders

- We push to GitHub manually — confirm before pushing.
- Honesty applies to the data: if a rating has <10 alumni, label the norm as low-sample.
- Don't lock framework choice until Phase 7.
