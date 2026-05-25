# Provectus Analytics — Roadmap

**Goal:** Pull data from Flight Schedule Pro (FSP) to track total cost, training duration, flight hours billed, and event counts across ratings (PPL, IFR, ASEL COM, AMEL, CFI, CFII, MEI). Compare individual students to norms at each milestone. Use it internally for course/instructor efficiency and externally for cost-transparency marketing.

## Status snapshot (2026-05-25)

- **Phase 1 (schema) — done.** Metrics + milestones locked, see below.
- **Phase 2 (FSP discovery) — done.** Reporting Hub is the data path. No Training Hub at Provectus, so no course/enrollment data in FSP. API path investigated but deferred (no subscription).
- **Phase 3 (alumni data collection) — plan written, awaiting boss sign-off + outreach send.** See `ALUMNI_DATA_COLLECTION_PLAN.md`. Synthetic test data substituting until real responses arrive — see `SYNTHETIC_DATA_README.md`.
- **Phase 4 (name reconciliation + rating attribution) — done against synthetic data.** Code in `src/provectus_analytics/{reconcile,partition}.py`. End-to-end test asserts output matches `ground_truth_per_milestone.csv` exactly.
- **Phase 5 (data model) — done.** SQLite via `src/provectus_analytics/{schema,db}.py`. Tables: students, ratings, enrollments, milestones, flights, invoices, surveys.
- **Phase 6 (cleaning + norms) — done.** `src/provectus_analytics/norms.py`. Tukey-fence outlier filter, median + P25/P75, low-sample flag at n<10.
- **Phase 7 (MVP dashboard) — done for PPL, then superseded.** Original framework was Streamlit; see `PHASE7_FRAMEWORK_DECISION.md`. The PPL MVP validated the pipeline + methodology before scaling.
- **Phase 8 (full web app) — done, then redesigned.** First pass in Streamlit (all 7 ratings, four pages). Second pass: rewrote in Dash for design control. Same four pages: All Ratings overview, Rating Detail, Student drill-down, Instructor view. No auth (boss-only access; add later if needed). Still on synthetic data.
- **Phase 8.5 (design polish) — done.** Custom design system inspired by Linear / Stripe / Strava / Whoop / Hex. Dark + light mode (persisted via localStorage). Stripe-style metric cards, Whoop-style P25/P75 band charts, Strava-style per-rating timeline on Student page. Provectus logo in sidebar. Native system font stack (works under Brave Shields, corporate firewalls, offline).
- **Phase 8.6 (boss distribution) — done.** Packaged the app as a double-click `.command` launcher with first-run venv bootstrap, plus a boss-facing `Read Me First.pdf`. Distribution zip lives in `dist/` (gitignored). Boss flow: unzip → right-click `Provectus.command` → Open → app installs deps on first run and opens browser to `127.0.0.1:8050`. App runs entirely on his Mac; no hosting needed.
- **Phase 9 (automation) — done (manual-trigger flavor).** Claude-in-Chrome prompt drives the two Reporting Hub exports (`tools/fsp_export_prompt.md`); dashboard sidebar gained an "Import latest FSP exports" button that copies the newest matching XLSX files from `~/Downloads/` into `FSP Exports/` with canonical names and rebuilds the DB. Cadence: weekly + on-demand. Unattended scheduling intentionally not built. See `PHASE9_AUTOMATION.md`.
- **Phase 9.5 (incremental ingest + override surface) — done.** `build_db()` is now non-destructive when real exports are present: `flights` UPSERT on `fsp_reservation`, invoices truncate-and-reload, `flight_overrides` table preserves manual tweaks across every weekly re-import. New **Flights** page in the dashboard provides an editable table for per-flight overrides (is_ground_lesson, billing_category, aircraft_class, reservation_type). Validated end-to-end against real exports (1915 flights, 4355 invoice lines, override survives rebuild).
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

### Phase 7 — MVP dashboard (PPL only, local) ✓

Built in **Streamlit** for the MVP (see `PHASE7_FRAMEWORK_DECISION.md`). PPL cost/hours/duration distribution + a single student plotted against the norm. Validated the data pipeline, methodology, and framework choice before scaling to all ratings. Superseded by Phase 8.

---

### Phase 8 — Full web app ✓

Expanded to all 7 ratings. Four pages: All Ratings overview, Rating Detail (date filter + student overlay), Student drill-down, Instructor view (student list + efficiency vs cohort). Auth deferred — not needed yet.

Framework note: shipped initially in Streamlit, then rewritten in **Dash** (Phase 8.5) for finer-grained design control. Launch: `python app.py` → `http://127.0.0.1:8050`.

---

### Phase 8.5 — Design polish ✓

Rewrote the Streamlit app in Dash to enable a custom design system. Reference apps: Linear (layout/density), Stripe (metric cards/tables), Strava (timeline + cohort comparison), Whoop/Oura (P25/P75 band charts), Hex (prose + data mix). Dark sidebar / light content with full dark-mode toggle (persisted via `localStorage`). Native system font stack — no network dependency, works under Brave Shields and offline. Provectus logo lives in a white badge at the top of the sidebar.

Structure:

```
src/provectus_analytics/web/
  app.py            Dash app factory + sidebar + routing
  theme.py          Plotly template + chart color tokens
  data.py           cached DB queries
  components.py     metric cards, tables, page headers
  pages/            one file per route (all_ratings, rating_detail, student, instructor)
assets/
  styles.css        design system (CSS variables for both themes)
  00-theme-init.js  applies persisted theme before paint
  Provectus.jpg     logo
```

---

### Phase 8.6 — Boss distribution ✓

Packaged the app for delivery to a non-technical user. Three artifacts:

- **`Provectus.command`** — double-clickable macOS launcher. On first run, creates a Python virtual env and installs deps; on subsequent runs, just launches and opens the default browser to `127.0.0.1:8050`.
- **`Read Me First.pdf`** — boss-facing plain-English instructions generated by `tools/build_boss_pdf.py`. Covers right-click→Open the first time, normal double-click after, where to put the four CSVs, the Rebuild DB button, troubleshooting, theme toggle.
- **`dist/Provectus Analytics.zip`** — clean 123 KB bundle (`dist/` is gitignored). Contains the app, assets, synthetic CSVs, launcher, and PDF. Excludes `.git/`, `.venv/`, tests, dev tools, and any local FSP exports.

Distribution flow: AirDrop or email the zip. Boss unzips, right-clicks the launcher, clicks Open at the Gatekeeper warning (first time only). App runs entirely on his Mac.

Caveats: macOS Gatekeeper requires the right-click→Open ritual on first launch (code-signing is $99/yr; not worth it for internal use). Updates ship as a new zip. Once real alumni data is loaded, the launcher should be paired with at least a shared-password auth layer before shipping further.

---

### Phase 9 — Automation ✓

Shipped the Claude-in-Chrome flavor (option a). Full details in `PHASE9_AUTOMATION.md`. Headline:

- `tools/fsp_export_prompt.md` — the prompt the user pastes into Claude in Chrome to drive the three Reporting Hub exports (Flight Detail, Invoice Detail, Reservation Detail) with a rolling 3-year window.
- `src/provectus_analytics/import_exports.py` — picks the newest matching XLSX for each report from `~/Downloads/` (or `FSP Exports/`) and copies it into `FSP Exports/` with canonical filenames. Idempotent.
- Dashboard sidebar → **"Import latest FSP exports"** button — runs the import helper then `build_db()` in one click.
- Cadence: weekly calendar reminder + on-demand. Optional Claude scheduled-task reminder. No fully-unattended schedule (would require the boss's machine to be unlocked + signed in at trigger time).

Options (b) Reporting Hub Advanced and (c) API access remain deferred.

**Phase 9.5 closed this gap.** `build_db()` now auto-detects whether real exports exist in `FSP Exports/` and routes to either the live XLSX pipeline (non-destructive, override-preserving) or the synthetic CSV pipeline (destructive, used by tests). Two reports needed weekly: Flight Detail + Invoice Detail. Reservation Detail dropped — redundant with Flight Detail.

### Phase 9.5 — Incremental ingest + override surface ✓

Motivation: the user hand-curates a non-trivial number of flight rows (e.g. reclassifying multi-engine events that the auto-heuristic flagged as flights but were actually ground). A destructive rebuild would clobber those edits every week.

Shipped:

- `schema.py` — new `flight_overrides` table (`flight_id, field_name, value, note, set_at`). All DDL switched to `CREATE TABLE IF NOT EXISTS` so the rebuild path is a forward-only migrator.
- `db.py` — new `open_or_create()` helper. Preserves existing data; reseeds ratings via `INSERT OR IGNORE`.
- `ingest.py` — added `ingest_invoice_xlsx()` (truncate-and-reload), reworked `ingest_flight_detail_xlsx()` to UPSERT on reservation #, plus `apply_overrides()` / `set_flight_override()` / `clear_flight_override()`. Whitelist of overridable columns: `is_ground_lesson`, `billing_category`, `aircraft_class`, `reservation_type`.
- `web/data.py` — `build_db()` auto-detects real vs synthetic exports.
- `web/pages/flights.py` — new sidebar page. Sortable + filterable DataTable, inline edit on the four whitelisted columns. Save handler diffs against original rows, writes overrides, re-runs partition + milestones.

End-to-end test (in `/tmp` sandbox): first build inserts 1915 flights / 4355 invoice lines; second build with an override set updates all 1915 rows and the override survives, applied during `build_db()` final step.

**To extend overridable columns:** add to `_OVERRIDABLE_COLUMNS` in `ingest.py` AND to the editable columns list in `pages/flights.py`.

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
