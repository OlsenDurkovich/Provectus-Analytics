# Stage-check integration spec (2026-06-28)

How the **Provectus Stage Check Record** Google Form feeds the FSP-based
analytics pipeline. Companion to `Stage Check Form Spec.md` (the form itself).

**Status:** spec only — not built. Build once the form's response sheet is
linked and has a few real rows to test against.

## Goal

Turn each stage check into a confirmed, dated, rating-labeled pointer the
attribution engine can use as a *hard boundary* instead of a heuristic guess.
FSP supplies the numbers (hours, cost, counts); stage checks supply the rating
labels and milestone dates FSP can't.

## Data flow

```
Google Form  →  linked Responses Sheet  →  export to repo (stage_checks.xlsx)
   →  ingest_stage_checks()        # new — loads rows into `stage_checks` table
   →  reconcile()                  # existing matcher sets stage_checks.student_id
   →  build_enrollments()          # stage-check dates pin/refine rating windows
   →  milestones.compute_*()       # stage-check dates supply solo/XC/near-end dates
   →  norms                        # unchanged
```

Pulling the sheet mirrors the existing FSP-export + alumni-survey flow (manual
export → repo, automate later). Each rebuild re-reads it.

## New table: `stage_checks`

| Column | Notes |
|--------|-------|
| `stage_check_id` | PK |
| `student_id` | NULL until reconciled (FK → students) |
| `student_name` | from form |
| `student_email` | from form — **primary match key** |
| `check_date` | the stage check date (not submit time) |
| `rating` | PPL / IFR / COM / AMEL / CFI / CFII / MEI |
| `stage` | normalized: pre_solo / pre_xc / xc_complete / pre_checkride |
| `result` | satisfactory / unsatisfactory / partial |
| `hobbs_hours` | optional — independent hours-at-date cross-check |
| `conducting_instructor` | optional |
| `primary_cfi` | optional |
| `aircraft` | C172 / PA-28 / BE-76 / Other-ASEL / Other-AMEL |
| `match_status` | matched / unmatched (for manual reconcile surface) |
| `raw_json` | full original row, for audit |

Normalize the form's free-text stage labels into the short `stage` codes above
on ingest (e.g. "Stage 1 - XC time complete" → `xc_complete`).

## The join (integration point)

`reconcile.py` already matches survey rows to FSP clients: **email → normalized
name → token-subset**. Reuse it verbatim for stage checks — set
`stage_checks.student_id` the same way. A matched row is now bolted to the same
student as their FSP flights/invoices. Unmatched rows get `match_status =
'unmatched'` and are surfaced for manual fix-up (same pattern as unmatched
surveys; expose via the CLI or an admin view).

## How stage checks drive attribution

Precedence for a given student+rating window: **stage-check date → survey date →
guesstimate heuristic.** Stage checks are live + instructor-confirmed, so they
outrank both. For future students who never fill the retroactive survey, stage
checks become the primary boundary source.

Stage → milestone mapping (what each pins):

| Rating | Stage | Pins |
|--------|-------|------|
| PPL | pre_solo | `first_solo` |
| PPL | pre_xc | `xc_solos_complete` |
| PPL | pre_checkride | rating-end window (upper bound) |
| IFR | xc_complete (Stage 1) | `xc_pic_complete` |
| IFR | pre_checkride (Stage 2) | rating-end window |
| Others | pre_checkride | rating-end window |

`build_enrollments` consumes these as window inputs; `milestones.py` can read the
solo/XC dates directly (markers FSP can't label). The `aircraft` value maps to
SE/ME engine class (C172/PA-28 → SE, BE-76 → ME, the two "Other" buckets carry
the class) and feeds the SE-vs-ME overlap resolver. `hobbs_hours` is a sanity
check against the hours the FSP partition computes at that date — flag large
divergences.

## Honest caveats

- **Email accuracy is the weak link.** The *instructor* fills the form and may
  not know the student's exact FSP email. Name-match is the fallback; mismatches
  will happen → the unmatched surface is mandatory, not optional.
- **Stage checks refine, not fully define, windows.** They pin solo/XC and
  "near the end," but for most ratings the only stage check is pre-checkride, so
  the rating *start* is still inferred from flights. Tighter windows, not exact.
- **A pre-checkride stage check precedes the actual checkride** by days/weeks —
  it brackets the end, it isn't the checkride date (that still comes from the
  logged Check Ride flight).

## Implementation steps (when building)

1. `schema.py`: add the `stage_checks` table + migration.
2. `ingest.py`: `ingest_stage_checks(xlsx)` — load + normalize stage/result/aircraft.
3. `reconcile.py`: extend to set `stage_checks.student_id` (reuse the matcher).
4. `partition.py` / `build_enrollments`: prefer stage-check dates as window
   boundaries; document the precedence.
5. `milestones.py`: use stage-check solo/XC dates directly when present.
6. Unmatched surface: CLI report (or admin view) of `match_status='unmatched'`.
7. Tests: synthetic stage-check rows → assert windows/milestones pin correctly;
   matched + unmatched cases.

## Future upgrade

A form that pulls a **live student dropdown from the FSP roster** (Apps Script
or a Sheets/roster sync) eliminates the email-matching problem entirely — pick
the student, get their exact id. Worth doing once volume justifies it.
