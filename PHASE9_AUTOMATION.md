# Phase 9 — Automation

**Status:** done (Claude-in-Chrome path) + Phase 9.5 (incremental ingest + override surface). API path remains deferred.

## Decision

No FSP API subscription. The Phase 9 deliverable is a Claude-in-Chrome–driven
export flow plus a sidebar button that ingests whatever it produces.

## How it works

```
Claude in Chrome (logged into FSP)
        │
        ▼ runs 2 Reporting Hub exports
  ~/Downloads/
    FlightDetail_Report*.xlsx           (or "2026 Flight 5:25:26.xlsx" etc.)
    Invoice*.xlsx
        │
        ▼ user clicks "Import latest FSP exports" in dashboard sidebar
  FSP Exports/                          ← canonical names
    FlightDetail_Report.xlsx
    Invoice_Report.xlsx
        │
        ▼ same button triggers Rebuild DB (incremental, non-destructive)
  provectus.db                          ← flights UPSERTed by reservation #
                                          invoices truncate-reloaded
                                          flight_overrides re-applied
        │
        ▼ dashboard reads
  Flights page                          ← edit ground/billing/etc.; saved as
                                          rows in flight_overrides, survive
                                          every weekly re-import
```

Four moving pieces:

1. **`tools/fsp_export_prompt.md`** — the prompt you paste into Claude in
   Chrome. Drives the two exports with a rolling 3-year window and saves
   each XLSX in `~/Downloads/`.
2. **`src/provectus_analytics/import_exports.py`** — small helper that picks
   the freshest matching XLSX for each report from `~/Downloads/` (or, as
   a fallback, from `FSP Exports/` if the user dropped them there) and copies
   it to `FSP Exports/<canonical name>`. Idempotent.
3. **`src/provectus_analytics/web/data.py::build_db()`** — auto-detects real
   vs synthetic exports. Real path uses `open_or_create()` (non-destructive),
   UPSERTs flights by reservation #, truncate-and-reloads invoices, then
   re-applies `flight_overrides` so manual tweaks survive.
4. **Dashboard "Flights" page** — editable DataTable for the four whitelisted
   override columns: `is_ground_lesson`, `billing_category`, `aircraft_class`,
   `reservation_type`. Save handler diffs against original rows and writes
   to `flight_overrides` + re-runs partition + milestones.

## Cadence

- **Weekly (recommended):** add a calendar reminder for Monday 8 AM that says
  "Open FSP, run Claude in Chrome export, click Import in dashboard."
  Optionally use Claude's scheduled tasks (`mcp__scheduled-tasks`) to fire a
  weekly chat reminder.
- **On-demand:** run the prompt + click Import any time fresh numbers are
  needed (e.g. before a leadership meeting).

A fully unattended schedule would require either (a) the boss's machine to be
unlocked, signed into FSP, and running Claude in Chrome at schedule time, or
(b) a server-side replacement for Claude in Chrome (e.g. Playwright with stored
credentials). We are not building (b) until the manual cadence becomes a real
pain point.

## Why not FSP API (still)

Documented in `PHASE2_FSP_FIELD_MEMO.md` §1. Summary: no API subscription,
pricing not public, and exports + this automation cover the current scale.
Revisit if (a) export size hits Reporting Hub Basic's row caps, or (b) the
boss buys an API plan for other reasons.

## What's intentionally left undone

- **No alerting on stale data.** If the boss forgets to run the prompt, the
  dashboard happily shows last week's numbers. Future: a freshness indicator
  like "Data as of May 25" in the sidebar.
- **Override surface is whitelisted to four columns.** Extending to other
  columns (e.g. instructor reassignment, custom student linking) requires a
  one-line addition in `_OVERRIDABLE_COLUMNS` + the Flights page column list.
- **Student-side overrides** (e.g. "this flight belongs to Jane's CFI rating,
  not her CFII") aren't in the UI yet — currently those would be set via the
  partitioner logic, not the override surface. Revisit if the partitioner
  starts mis-attributing flights that the UI can't fix.
- **`partition.partition_flights()` runs over the whole table** every save.
  Fine at 1900 flights; might need to scope to changed enrollments at 50K.
