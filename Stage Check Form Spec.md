# Stage Check Record — form spec & data mapping

A short, instructor-friendly form filled out **at each stage check**. Its job is
to give the analytics pipeline a dated, rating-tagged, phase-tagged event in real
time — the signal it otherwise reconstructs from heuristics + the retroactive
alumni survey. For students going forward, this can largely replace the survey.

## Fields

Required set is deliberately small (6 fields) so instructors actually complete it.

| # | Field | Type | Required | Notes |
|---|-------|------|----------|-------|
| 1 | Date of stage check | Date (incl. year) | Yes | The real date, not the submit date. |
| 2 | Student full name | Short text | Yes | Reconcile fallback. |
| 3 | Student email | Short text | Yes | **Primary match key** to FSP records. |
| 4 | Rating in training | Multiple choice | Yes | Branches to the stage question. |
| 5 | Which stage check? | Multiple choice | Yes | Options depend on rating (below). |
| 6 | Result | Multiple choice | Yes | Satisfactory / Unsatisfactory / Partial. |
| 7 | Total flight hours to date (Hobbs) | Short text | No | Independent hours-at-milestone check. |
| 8 | Conducting instructor | Short text | No | Stage-check examiner. |
| 9 | Student's primary CFI | Short text | No | Feeds instructor view. |
| 10 | Aircraft flown | Dropdown | No | Family-level, maps to engine class (below). |
| 11 | Notes / areas to improve | Paragraph | No | Future efficiency analysis. |

## Rating → stage options (branched)

- **PPL:** Pre-solo · Pre-cross-country (solo XC) · Pre-checkride (end of course)
- **IFR:** Stage 1 — XC time complete · Stage 2 — pre-checkride
- **ASEL COM / AMEL / CFI / CFII / MEI:** Pre-checkride (end of course)

## Aircraft dropdown → engine class

Family-level options keep the data clean (free text breaks the lookup). The two
"Other" buckets still preserve the single/multi signal when the model isn't listed.

| Dropdown option | Engine class |
|-----------------|--------------|
| C172 | Single-engine (ASEL) |
| PA-28 | Single-engine (ASEL) |
| BE-76 | Multi-engine (AMEL) |
| Other single-engine (ASEL) | Single-engine (ASEL) |
| Other multi-engine (AMEL) | Multi-engine (AMEL) |

When the stage-check ingest is built, these map straight to the SE/ME class the
attribution engine uses. (BE-76 isn't yet in `ingest.AIRCRAFT_CLASS` — add it as
multi-engine when wiring the ingest.)

## How each stage maps to a tracked milestone

The pipeline already models these milestones; a stage check stamps the date.

| Rating | Stage check | Milestone it pins |
|--------|-------------|-------------------|
| PPL | Pre-solo | `first_solo` |
| PPL | Pre-cross-country | `xc_solos_complete` |
| PPL | Pre-checkride | rating end (near `checkride`) |
| IFR | Stage 1 — XC time complete | `xc_pic_complete` |
| IFR | Stage 2 — pre-checkride | rating end (near `checkride`) |
| Others | Pre-checkride | rating end (near `checkride`) |

Note: a *pre*-checkride stage check happens shortly **before** the actual
checkride, so it brackets the rating's end window tightly but isn't the checkride
date itself — that still comes from the logged Check Ride flight in FSP. The
stage check's real value is confirming *which rating was active on that date* and
pinning the interior milestones (solo, XC) that FSP can't label.

## Feeding it into the pipeline (next step, not yet built)

Form responses land in a linked Google Sheet (one row per stage check). To make
them count as pointers we'd add a small ingest path — mirrors the survey ingest:

1. Export/pull the responses sheet (same mechanic as the alumni survey).
2. Reconcile each row to a `student_id` by email (then name).
3. Write each stage check as a dated milestone marker for that student+rating,
   which `partition.py` uses as a hard boundary instead of guessing — and which
   `milestones.py` can read directly for solo/XC dates.

This is a clean follow-on once the form is live and we can see the real response
columns. Ask and I'll build it.
