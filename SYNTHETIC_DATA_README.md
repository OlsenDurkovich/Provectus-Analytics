# Synthetic Test Data

Fake data for pipeline testing while real alumni outreach is on hold pending boss decisions.
**Do not use in real analytics or marketing.** No real PII.

## Files

| File | Rows | Purpose |
|---|---|---|
| `synthetic_alumni_survey.csv` | 20 | Google Form responses — alumni-reported rating boundary dates |
| `synthetic_alumni_survey.xlsx` | 20 | Same data, formatted with edge-case rows highlighted |
| `synthetic_fsp_clients.csv` | 27 | FSP People/Users roster (20 alumni + 7 noise clients) |
| `synthetic_fsp_reservations.csv` | 1,697 | FSP Reservation Detail export — per-flight rows |
| `synthetic_fsp_invoices.csv` | 3,448 | FSP Invoice Detail export — billable line items |
| `synthetic_fsp_data.xlsx` | — | All three FSP exports as a single workbook (3 sheets) |
| `generate_synthetic_fsp_data.py` | — | Generator script (seed=42, reproducible) |
| `ground_truth_per_milestone.csv` | 118 | Phase 4 ground truth: per (alum, rating, milestone) cumulative metrics |
| `ground_truth_rating_norms.csv` | 7 | Phase 6 ground truth: per-rating cohort norms (P25/median/P75) at checkride |
| `ground_truth.xlsx` | — | Both ground-truth files as one workbook |
| `compute_ground_truth.py` | — | Derives ground truth from synthetic CSVs (re-run after regenerating) |

---

## 1. Alumni Survey (`synthetic_alumni_survey.csv`)

Mirrors the Google Sheet a real Google Form response would write to. One row per alum, columns match `SURVEY_FORM_SPEC.md` Q1–Q27 plus a `Consent` column.

**Note — discrepancy flagged:** the form spec does not currently include the marketing-consent checkbox that `ALUMNI_DATA_COLLECTION_PLAN.md` §2 says it should. The CSV includes a `Consent` column anyway. Drop the column if the form ships without it.

### Cohort design (20 alumni)

| Rating | Count |
|---|---|
| PPL | 12 |
| IFR | 15 |
| ASEL COM | 15 |
| AMEL | 11 |
| CFI | 11 |
| CFII | 9 |
| MEI | 8 |

Heavier on PPL/IFR/COM by design — realistic high-volume ratings even with transfer-ins thinning the PPL count. Distribution is within ~2x rather than perfectly flat, which would be unrealistic.

### Edge cases (intentional)

| Row | Alum | Edge case | What it tests |
|---|---|---|---|
| 3 | Sarah Williams | Transfer-in with PPL elsewhere, did IFR onward at Provectus | Partitioner must not crash on missing PPL window |
| 6 | David Kim | Short transfer (only IFR + COM at Provectus) | Sparse rating coverage; Q27 free-text explains |
| 9 | Sofia Garcia | PPL-only recreational, no further ratings | Single-rating norm case |
| 10 | Tyler Brooks | Started PPL, never finished — all "No" responses, only Q27 has content | Form submission with zero completions; should not produce rating buckets |
| 11 | Olivia Nguyen | Concurrent ASEL COM + AMEL (overlapping windows, same-month checkride) | Partitioner overlap resolver — needs SE/ME aircraft tiebreaker from FSP |
| 12 | Brandon Lee | Transfer with PPL/IFR/COM/AMEL — only instructor ratings at Provectus | Reverse of common case |
| 14 | Christopher Wilson | Transfer with PPL/IFR/COM single — did AMEL + CFI + MEI, **skipped CFII** | Non-contiguous progression; MEI without CFII is valid (MEI prereq is CFI + AMEL) |
| 16 | Noah Carter | Form says "Noah Carter," FSP roster says "Noah J. Carter" | Name reconciliation must handle middle-initial variations |
| 18 | Ethan Murphy | Transfer with PPL+IFR — did COM, CFI, CFII but no AMEL or MEI | Skipping AMEL is unusual but valid |

### Survey notes

- **Date format** is "Month YYYY" (free-text, matching form spec). Empty string = "skipped."
- **Booleans** (`Completed PPL`, etc.) are literal "Yes" / "No" strings.
- **Consent** is 15/20 Yes. Phase 10 public transparency view must exclude the 5 No respondents (Marcus, Sofia, Tyler, Ethan, Lucas).
- **Ryan O'Brien** has an apostrophe in the name — verify CSV parser handles it.

---

## 2. FSP Reservations (`synthetic_fsp_reservations.csv`)

Mirrors a Reporting Hub → Reservation Detail export. Fields come from `PHASE2_FSP_FIELD_MEMO.md` §3a.

### Schema

| Column | Notes |
|---|---|
| Reservation # | `R######` |
| Flight # | `F######`, blank for Canceled and Maintenance |
| Date | `YYYY-MM-DD` |
| Length (hrs) | Decimal, 0.0 if Canceled |
| Reservation Type | One of: Check Ride, Dual Flight Training, Student Solo, Introductory Flight, Maintenance, Owner Flight |
| Status | Completed or Canceled |
| Client | FSP display name, blank for Maintenance |
| Aircraft Tail / Make / Model | See fleet below |
| Instructor | Display name; blank for solos, checkrides, maintenance |
| **Rating Hint (synthetic answer key)** | **NOT a real FSP column** — only in synthetic data. Use it to validate your partitioner output. Real FSP exports won't have it. |

### Fleet (invented)

| Category | Tails | Used for |
|---|---|---|
| SE Basic | N4521P (172N), N7732K (172S), N8814M (PA-28-181), N6603L (172S) | PPL, IFR, CFI, CFII training |
| SE Complex | N9923R (182RG), N1175C (PA-28R-201) | Commercial training (~70%) |
| Multi-Engine | N3340T, N5567W (both PA-44-180 Seminole) | AMEL, MEI training |

### Instructors (invented)

5 CFIs: Mike Anderson, Sarah Phillips, Tom Reyes, Jenny Park, Doug Hayes. Each student has a deterministic primary instructor (hash-based) and ~20% of flights are with a substitute.

### Hours-per-rating assumptions (rough industry averages)

| Rating | Range |
|---|---|
| PPL | 55–70 hrs |
| IFR | 40–55 hrs |
| ASEL COM | 20–35 hrs (active training only; total time builds across all phases) |
| AMEL | 10–16 hrs |
| CFI | 25–38 hrs |
| CFII | 10–16 hrs |
| MEI | 8–14 hrs |

PPL students solo for ~30% of flights between first-solo and XC-solos-complete dates.
~4% of all reservations are Canceled (test row filtering).
1 Checkride per rating completion, on the last day of the rating window.

### Noise rows (in FSP but irrelevant to alumni analytics)

- 35 Maintenance flights (no client)
- 20 Owner Flight rentals (Robert Klein, Patricia O'Donnell)
- 12 Introductory / discovery flights (Michael Sanders, Karen Yoshida)
- 3 current students (Henry Walsh, Grace Liu, Daniel Park) — in FSP but NOT in the survey. Partition logic must exclude them from alumni norms.

---

## 3. FSP Clients (`synthetic_fsp_clients.csv`)

27 rows: 20 alumni + 7 noise. Notes column flags the Noah Carter name mismatch and current-student/owner roles.

---

## 4. FSP Invoices (`synthetic_fsp_invoices.csv`) — SCHEMA IS A GUESS

**The Invoice Detail report column inventory hasn't been done yet** (open question in ROADMAP). The schema below is a reasonable guess based on how flight schools typically itemize. Replace with real columns once we have them — this generator script needs to be re-run after the real schema is known.

### Guessed schema

| Column | Notes |
|---|---|
| Invoice # | `INV######` |
| Invoice Date | 0–3 days after the flight |
| Client | FSP display name |
| Reservation # | Links back to reservations table (this linkage may or may not exist in real FSP) |
| Line Item Description | Free text |
| Category | Aircraft, Instructor, or Ground |
| Quantity (hrs/units) | Hours billed |
| Rate ($) | Per-hour rate |
| Amount ($) | qty × rate |
| Status | Paid (92%) or Outstanding |

### Billing rules used (also guessed)

- Aircraft rental: every completed Dual / Solo / Checkride / Discovery flight, charged at the per-tail rate below.
- Instructor time: every dual flight, charged at $75/hr, often longer than flight time (briefing).
- Ground briefing: ~25% of dual flights get a separate Ground line at $65/hr.
- Solo flights: aircraft only, no instructor.
- Checkrides: aircraft only (DPE billed separately to student, not via school).
- Maintenance and Owner Flights: not invoiced to students.

### Per-tail hourly rates (invented)

C172N $175 · C172S $185 · PA-28-181 $190 · C182RG $230 · PA-28R-201 $235 · PA-44-180 $385

### Output sanity check

Total billed across all alumni: **$832,522** (831k for 20 alums = $42k average).
Full career-track (PPL→MEI) alums land $60–65k each. PPL-only $14.5k (Sofia). Tyler's incomplete PPL: $7.2k for 25 hrs.

---

## 5. Edge case map across files (cross-reference)

| Edge case | Survey | Reservations | Clients | Invoices |
|---|---|---|---|---|
| Sarah transfer-in | No PPL row data | No PPL flights | — | — |
| David transfer-in | Only IFR + COM | Only IFR + COM flights | — | — |
| Sofia PPL-only | PPL completed only | Only PPL flights | — | Only PPL invoices |
| Tyler incomplete | All No, Q27 explains | 16 flights, no checkride | Present | $7.2k billed |
| Olivia concurrent COM+AMEL | Same checkride month | 6 ME + 6 SE flights in Jun–Aug 2023 | — | — |
| Brandon transfer | Only CFI/CFII/MEI | Only instructor ratings | — | $20.7k (instructor only) |
| Chris skipped CFII | AMEL+CFI+MEI no CFII | Same | — | — |
| **Noah Carter / Noah J. Carter** | "Noah Carter" | "Noah J. Carter" | "Noah J. Carter" with name-differs note | "Noah J. Carter" |
| Ethan skipped AMEL+MEI | COM+CFI+CFII only | Same | — | — |
| Current students (not in survey) | Absent | Henry, Grace, Daniel present | Present, marked current | Present |

---

---

## 6. Ground Truth (`ground_truth_per_milestone.csv`, `ground_truth_rating_norms.csv`)

What your Phase 4 partitioner + Phase 6 aggregator should reproduce. Derived from the synthetic data — re-run `compute_ground_truth.py` if you regenerate the underlying CSVs.

### `ground_truth_per_milestone.csv` (118 rows)

One row per (alum, rating, milestone). Milestones per rating:

- **PPL:** first_solo, xc_solos_complete, checkride
- **IFR:** xc_pic_complete, checkride
- **All others:** checkride only

Columns: `client_fsp`, `survey_name`, `rating`, `milestone`, `milestone_date`, `days_from_rating_start`, `cumulative_flights`, `cumulative_hours`, `cumulative_cost`.

**Negative tests (must be ABSENT from ground truth):**
- Tyler Brooks — no completed milestones (started PPL, quit)
- Daniel Park, Henry Walsh, Grace Liu — current students in FSP, not in survey

### `ground_truth_rating_norms.csv` (7 rows)

Per-rating cohort norms at checkride: median + P25/P75 for hours, cost, days. `low_sample_flag = Yes` when n<10 (per ROADMAP Phase 6 rule).

Sample (from current synthetic data):

| rating | n | median_hrs | median_cost | median_days | low_sample |
|---|---|---|---|---|---|
| PPL | 12 | 64.2 | $16,569 | 407 | No |
| IFR | 15 | 48.0 | $13,022 | 225 | No |
| COM | 15 | 27.6 | $8,347 | 131 | No |
| AMEL | 11 | 14.0 | $6,422 | 69 | No |
| CFI | 11 | 31.9 | $8,690 | 113 | No |
| CFII | 9 | 14.6 | $3,741 | 74 | **Yes** |
| MEI | 8 | 12.6 | $5,820 | 67 | **Yes** |

### Milestone date semantics

- `first_solo`, `xc_solos_complete`, `checkride`: derived from the actual flight in reservations (Student Solo / Check Ride reservation types).
- `xc_pic_complete`: NOT derivable from flight type alone — uses the survey-reported month-end date.

Your partitioner must mirror this: solo and checkride dates come from flights; XC-PIC-complete comes from the survey.

---

## Regeneration

Re-run the generator to rebuild FSP CSVs (seed is fixed, output is identical):

```bash
cd "/Users/olsend/Documents/Provectus Analytics"
python3 generate_synthetic_fsp_data.py
python3 compute_ground_truth.py
```

To change the cohort, edit `WINDOWS` and `ALUMNI` at the top of both scripts (they must stay in sync). The survey CSV is hand-crafted — edit it directly if you change the cohort.

## What's still NOT included

- **Stress-test variant.** Current edge cases are realistic mix. A stress-test variant (missing dates, name typos, ambiguous overlaps) could be added.
- **Real Invoice Detail schema.** Replace guessed columns once the actual export is inspected.
- **Cohort-of-1 norms** (Sofia for PPL-only, Brandon for instructor-only) — included in norms but the cohort-of-N filter is your code's responsibility.
