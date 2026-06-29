# Provectus Analytics — Roadmap

**Goal:** Pull data from Flight Schedule Pro (FSP) to track total cost, training duration, flight hours billed, and event counts across ratings (PPL, IFR, ASEL COM, AMEL, CFI, CFII, MEI). Compare individual students to norms at each milestone. Use it internally for course/instructor efficiency and externally for cost-transparency marketing.

## Status snapshot (2026-05-25)

> **Update 2026-06-27 — LIVE.** Deployed on Railway at https://provectusanalytics.com (custom domain + HTTPS), serving synthetic data. Website-migration code (Phases 10–14) merged to `main`; Docker build verified. Remaining work is in the prioritized **Post-launch backlog** below. Ops/deploy details in MIGRATION.md.

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
- **Phase 9.7 (React + FastAPI rewrite) — done.** Dash is gone; frontend is Vite+React+TS, backend is FastAPI. All 5 tabs at parity. Boss launcher unchanged.
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

### Phase 9.7 — React + FastAPI rewrite ✓

Replaced the Dash UI with a Vite + React 18 + TypeScript frontend backed by a FastAPI app that wraps the existing Python pipeline. Boss distribution model preserved (prebuilt `frontend/dist/` shipped in zip, `.command` launcher → uvicorn → 127.0.0.1:8050). Phase 9.5 override surface (editable Flights cells → `set_flight_override` + partition/milestones rerun) preserved end-to-end. Hand-rolled SVG charts ported from the Claude Design hi-fi handoff (`design_handoff_provectus_analytics/`).

Shipped:

- `src/provectus_analytics/api/` — FastAPI app: schemas (Pydantic), adapters (Python→wire), routers (kpis, ratings, students, instructors, flights, meta).
- `src/provectus_analytics/api/queries.py` — formerly `web/data.py`, now lives next to the API code it serves.
- `frontend/` — Vite + React + TS app, all 5 tabs (Overview, Rating Detail, Student, Instructor, Flights), CmdK palette, ErrorBoundary, light/dark theme.
- `tools/build_dist.sh` — packs `frontend/dist/` + Python source into the boss-distributable zip.
- Legacy Dash code deleted: `app.py`, `src/provectus_analytics/web/`, `dash`/`plotly` deps.

37 backend tests + 48 frontend tests passing.

Spec: `docs/superpowers/specs/2026-05-25-dash-to-react-rewrite-design.md`
Plan: `docs/superpowers/plans/2026-05-25-dash-to-react-rewrite.md`

---

### Phase 10 — Public transparency view

Anonymized public page: "the average PPL at Provectus costs $X and takes Y hours, P25–P75 band shown." Marketing asset. Flows from the same data store, conditional on alumni having opted in via the consent checkbox in Phase 3.

---

## Post-launch backlog (prioritized) — added 2026-06-27

Deployment is done; the app is live on synthetic data. The following is the working to-do, ordered by urgency.

### P0 — Now (blocking / time-sensitive)

- **Boss upgrades Railway to the Hobby plan** before the 30-day / $5 trial credit runs out, or the live site pauses.
- **Load real alumni survey data** (Phase 10.2) — still on synthetic data; waiting on Seanna Glatzel's responses. Upload the real `alumni_survey.xlsx` via the in-app upload once received.

### P1 — High (do soon)

- **User & access management — DONE, MERGED + DEPLOYED** (2026-06-27, PRs #9–#13). Roles admin/instructor/viewer, admin user-management UI + API, self-service password change, last-admin guard — PLUS **per-user page access** (admins tick exactly which pages each user sees; enforced server-side via `require_page()`, not just UI) and **admin password reset**. Verified live on provectusanalytics.com. Specs: `docs/2026-06-27-user-access-management-spec.md`, `docs/2026-06-27-per-user-access-spec.md`.
  - *Instructor data scoping — DONE (PR #17, see Done).* The `instructor` role now sees only its own students via a dedicated scoped endpoint, same pattern as the student role.

### P2 — Medium

- **Color scheme / branding pass — DONE, MERGED + DEPLOYED** (accent: `feat/brand-color`; heatmap: `feat/chart-palette`). UI accent purple→logo green (light `#1B5E3F`, dark `#1F8A5B`) + the activity-heatmap single-hue scale→green. **Design decision (2026-06-27, Olsen):** the *categorical* palettes — the 7 per-rating colors and the 3-metric colors — are intentionally left multi-color. Greening them would collide with the existing green (`#3DD68C`) and hurt rating distinguishability, so this is considered complete. A full categorical-palette redesign around green is a separate design exercise only if ever wanted.
- **"Remember my login" / stay signed in — DONE, MERGED + DEPLOYED** (2026-06-27, PR #16, `feat/remember-me`). "Keep me signed in" checkbox → 30-day refresh token + localStorage (survives browser close); unchecked → sessionStorage. See Done.
- **Stage-check pipeline ingest — CORE BUILT + SYNTHETIC-VALIDATED** (2026-06-28, branch `feat/stage-check-ingest`). Wires the **Provectus Stage Check Record** Google Form into attribution. Done so far: `stage_checks` table; `ingest.ingest_stage_checks()` (normalizes stage/result/rating, derives SE/ME engine class); `reconcile.reconcile_stage_checks()` (email→name→subset join, unmatched flagged); `partition.apply_stage_check_windows()` (sets/refines rating windows from stage-check dates — pre_solo→first_solo, pre_xc→xc_solos, xc_complete→xc_pic, pre_checkride→window end — and **never touches survey-backed enrollments**, so historical alumni + the ground-truth test are safe). Synthetic data: `tools/make_synthetic_stage_checks.py` + `synthetic_stage_checks.csv` (118 rows from ground truth); +8 tests, ground-truth e2e still exact. **Remaining:** (1) wire ingest+reconcile+apply into `build_db` once the real response sheet is linked (needs the export path + observing the real column shape); (2) an unmatched-rows surface (instructors may mistype the FSP email); (3) honest limit — ratings with only a pre-checkride stage check don't pin a true *start*. Spec: `docs/2026-06-28-stage-check-integration-spec.md`. Form already live (`Stage Check Form Builder.gs`, `Stage Check Form Spec.md`).
- **Display account names instead of email — DONE, MERGED + DEPLOYED** (2026-06-28, PR #19, `feat/account-settings`). Shipped as part of self-service account settings: `display_name`/`phone`/`theme` columns, a Settings page (name/email/phone/theme/password) every user can reach, display name shown in the sidebar chip + topbar (fallback email), admins can edit name/email/phone per user.
- **Guard the "Rebuild DB" button** (added 2026-06-28, Olsen) — the rebuild is now crash-safe (atomic swap, self-heal — PR #20), but it's still a heavy one-click action that resets analytics + wipes accounts when on synthetic data. Add a confirmation dialog (admin types/confirms before it runs), and ideally show it's running (it's a long synchronous op). Stretch: move the rebuild to a background task so it can't tie up / time out a request. *Code:* button in `frontend/src/components/Sidebar.tsx` (`onRebuild`); endpoint `POST /api/rebuild` in `routers/meta.py`.

### P3 — Later

- **Public transparency view — DONE, MERGED + DEPLOYED** (`feat/public-transparency`) — see Done.
- **`www` subdomain — DONE** (2026-06-27) — see Done.

_(P3 is clear. All 2026-06-27 feature branches — user-access, brand-color, chart-palette, public-transparency, per-user-access, student-role (PR #14), rebuild-safety (PR #15) — are merged to `main` and deployed. Remaining open work is the P0 external blockers + the optional follow-ups: instructor data scoping, "remember my login", full categorical chart-palette redesign.)_

### Done

- ✅ **Instructor data scoping — own-students-only account** (2026-06-28, branch `feat/instructor-scoping`) — the `instructor` role now mirrors the student role: empty page set (every `require_page()` endpoint 403s for them) + an `instructor_name` link on the user row; admin picks the instructor from a list. One endpoint they reach, `GET /api/me/students` (dep `current_instructor`), serves only their own roster from the token-derived name. **Cost is stripped server-side** (no `costToDate`/`avgCost` ever leaves the server for an instructor) — progress/hours only, per the design choice. Frontend: `/my-students` page (roster table with progress bars), instructor-only nav, data-state hidden. Backend +11 tests / frontend +2; updated the page-preset test (instructor now → no pages). Decisions (2026-06-28, Olsen): dedicated scoped page (not a filtered dashboard); hide cost.
- ✅ **Rebuild DB safety — preserve logins + admin-only** (2026-06-27, PR #15, merged + deployed) — the "Rebuild DB" button took the synthetic path (current prod state) which **replaced the whole `provectus.db` file and silently wiped every login** (accounts live in the same file). `build_db` now snapshots + restores the `users` table around the file swap (`_snapshot_users`/`_restore_users` in `api/queries.py`); real-data path was already non-destructive. Also gated `POST /api/rebuild` + `/api/import-fsp` with `current_admin_user` (GET `/api/meta` stays open) — the button was admin-only in the UI but the endpoints weren't. +5 tests (in `tests/test_auth/`, since `test_api/conftest.py` overrides auth to a fake admin).
- ✅ **Student role — own-data-only account** (2026-06-27, PR #14, merged + deployed) — 4th role `student`, scoped to one person's training. Empty page set (so every `require_page()` endpoint already 403s for them) + a `student_id` link on the user row; admin picks the linked record from a list on the Users screen. The one endpoint they reach, `GET /api/me/training` (dep `current_student`), serves only their own `student_id` from the token, never from input. Frontend: `/my-training` page (own hours/cost/timeline, no cohort), student-only nav. **This is the first real per-person data wall** — the instructor-scoping follow-up (see P1) can reuse the same token-derived-id pattern. Backend +10 tests / frontend +2. Specs: `docs/2026-06-27-per-user-access-spec.md`.
- ✅ **Per-user page access + admin settings + password reset** (2026-06-27, PR #13, merged + deployed) — admins set exactly which pages each user sees via checkboxes on the Users screen; roles act as presets; enforced **server-side** with a `require_page()` dependency (per-endpoint on ratings/students; `meta` stays open). Adds `users.pages` column + migration, `/me`/users API return `pages`+`is_admin`, PATCH accepts `pages` + admin `new_password` reset. Frontend: `canSee()` gating of sidebar + routes, NoAccess fallback, per-user settings UI. Backend +9 tests, frontend +2; verified live. Caveat: page access gates pages/endpoints, not per-field data.

- ✅ **Public transparency view** (2026-06-27, branch `feat/public-transparency`, committed, awaiting push + merge) — public unauthenticated `/transparency` page + `GET /api/public/transparency`. Consent-filtered aggregate norms (median + P25/P75 for cost/hours/days), no PII, low-sample caveats, and a `data_mode` banner that labels synthetic sample data until real responses land. Backed by `norms.compute_rating_norms(consented_only=True)`. Backend +4 tests, frontend +2; full suites green.
- ✅ **`www` subdomain** (2026-06-27) — `www.provectusanalytics.com` added as a Railway custom domain + Cloudflare DNS (CNAME `www`→`h2drb6o0.up.railway.app`, DNS-only; TXT `_railway-verify.www`). Serves the app once Railway issues the cert (verifying). No repo change. Both apex and www serve the app; a www→apex redirect was deemed unnecessary.
- ✅ **Chart heatmap → brand green** (2026-06-27, branch `feat/chart-palette`, committed, awaiting push + merge) — activity-heatmap single-hue scale recolored purple→green. Categorical rating/metric palettes intentionally left (see P2 decision).
- ✅ **User & access management** (2026-06-27, branch `feat/user-access-management`, pushed, awaiting merge) — three roles admin/instructor/viewer (retired legacy `boss`, migrates boss→admin), admin-only `/api/users` (list/create/patch) + Users admin screen, self-service `/api/auth/change-password`, last-admin guard, `flights`+`upload` routers gated to admin. Backend 128 / frontend 80 tests pass; tsc + build clean. (Follow-up: instructor data scoping — see P1.)
- ✅ **Brand accent color** (2026-06-27, branch `feat/brand-color`, pushed, awaiting merge) — UI accent purple→Provectus logo green in both themes + accent-derived chrome. Chart-data palette deferred (see P2).
- ✅ **Clean up dead buttons** (2026-06-27) — audited every control; only the notifications bell was non-functional (placeholder, no feed). Removed the bell, the orphaned `NotificationsPopover.tsx`, the `notifOpen` plumbing, and dead `notif-*` CSS. Everything else was already wired. tsc + build clean, 76/76 frontend tests pass.
- ✅ **Auto-seed DB on empty at startup** (2026-06-27) — shipped as `feat(api): auto-seed analytics DB on startup if empty`; a fresh or wiped `/data` volume now self-heals instead of showing empty charts.
- ✅ **Sidebar user chip tied to login** (2026-06-27) — the bottom sidebar chip was hardcoded ("PA / Provectus Aviation / Internal analytics"); now shows the signed-in user (initials from email, email, role) from data already on the login. Also removed two dead "switcher" chevrons (workspace header + user chip). First concrete slice of User & access management — account *display* is live; account *creation* + role enforcement still pending.

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
