# Alumni Data Collection Plan

**For:** boss review — first deliverable
**Audience:** ~50 former Provectus students who completed one or more ratings here
**Why this is needed:** Provectus's FSP setup does not include Training Hub, so FSP has no course/enrollment/rating tag on training flights. To attribute historical flights to the right rating (PPL vs IFR vs ASEL COM, etc.), we need rating-boundary dates from each alum. Aircraft type, checkride flags, and solo flags get us partway; alumni input closes the gap.

---

## 1. What FSP gives us (no survey needed)

Confirmed from Reporting → Reservation Detail report:

- Reservation type per flight: **Check Ride**, **Dual Flight Training**, **Introductory Flight**, **Student Solo**, **Maintenance**, **Owner Flight**
- Aircraft tail + make + model per flight → single vs multi-engine derivable from model
- Instructor per flight
- Date, length (hrs), client name, reservation #, flight #
- Billing data via Invoice Detail / Sales by Client reports (separate report — not yet column-mapped)

What this means for attribution before the survey:
- **Student Solo → PPL phase** (inferred — solos are overwhelmingly PPL-stage in typical training pipelines; not guaranteed for every flight, will be validated against alumni-reported PPL date windows)
- **Check Ride → rating completion boundary** (but FSP doesn't say *which* rating — needs sequence inference or survey)
- **Multi-engine aircraft → AMEL or MEI phase**
- **Single-engine + Dual Flight Training** → ambiguous between PPL, IFR, ASEL COM, CFI, CFII

So the survey only needs to disambiguate the single-engine "Dual Flight Training" cohort and confirm checkride-to-rating mapping.

---

## 2. What we ask alumni for

Minimum viable survey. Every field is "if you completed this at Provectus, fill in; otherwise skip."

### Per rating, two dates (start + checkride pass)
- **PPL** — start date, first solo date, XC solos complete date, checkride pass date
- **IFR** — start date, XC PIC time-building complete date, checkride pass date
- **ASEL COM** — start date, checkride pass date
- **AMEL** — start date, checkride pass date
- **CFI** — start date, checkride pass date
- **CFII** — start date, checkride pass date
- **MEI** — start date, checkride pass date

Dates can be approximate (month + year accepted) — recall accuracy declines past 2 years and we don't want to bottleneck on perfection.

### Identity + consent
- Full name (to match against FSP client name)
- Email (for follow-up only)
- One checkbox: "I consent to Provectus using my anonymized training cost/hours data in public marketing materials"

That's it. Form should take a returning alum 3–5 minutes.

---

## 3. Mechanic

**Google Form → Google Sheet → ingest to our SQLite store.**

- Each rating gets its own section, with a "Did you complete this rating at Provectus?" gate question. If "no," skip the section.
- Date fields: month/year picker (no day required). Easier recall, still good enough for partitioning flights into rating buckets.
- Pre-fill the alum's name from a personalized link if possible (`?entry.123=Jane+Doe`).

**Outreach cadence:**
1. Day 0: personal email from Provectus leadership (not from a noreply alias) with the form link and a one-sentence "why."
2. Day 7: reminder email to non-responders.
3. Day 14: short phone call to remaining non-responders (the bulk of value is in the ~10–15 most data-rich alumni who completed multiple ratings here — those calls are worth the time).

Target: 70%+ response rate over 3 weeks. Realistic; at 50 alumni that's 35 responses — enough to validate the attribution rules and produce defensible norms for the higher-volume ratings (PPL, IFR).

---

## 4. What we do with the data

1. **Match alum name → FSP client name** (manual reconciliation step; ~50 rows, doable in 30 min).
2. **Partition each alum's flights into rating buckets** using their reported boundary dates:
   - Flights between [PPL start, PPL checkride] → PPL
   - Flights between [IFR start, IFR checkride] → IFR
   - etc.
   - Concurrent ratings (ASEL COM + AMEL, CFI + CFII) split by aircraft (SE vs ME) and lesson type if available.
3. **Aggregate per-rating metrics:** cumulative cost, cumulative flight hours, calendar days from start to checkride, event count.
4. **Compute norms:** median + P25–P75 band per rating per milestone.
5. **Validate:** spot-check 5–10 alumni's bucketed data with them on a call. If aggregates look wrong, iterate the partitioning rules before going wider.

---

## 5. Privacy / consent

- Survey collects email + dates. No SSN, no financial data, no health.
- Marketing-use checkbox is **opt-in** and **anonymized only** — aggregate norms, no individual identification.
- Raw responses live in our Google Sheet (Provectus-owned) and SQLite store (local). No third-party sharing.
- Mention this on the form's intro screen so consent is informed.

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Low response rate (<50%) | Personal-email send + phone follow-up; offer small incentive (Provectus swag, $25 gift card) if rate looks weak after day 7 |
| Date recall errors | Accept month/year granularity; cross-check first-solo date against FSP's Student Solo reservations as a sanity check |
| Alum can't be matched to FSP client name | Ask for name variations + middle name; fall back to email match if Provectus has historical email records |
| Boss wants the data sooner than 3 weeks | Send the form to a friendly subset of 5–10 alumni first ("pilot batch") to validate the form copy + identify questions to drop |
| Survey design changes after launch | Don't rush — get the form copy reviewed once before the day-0 send. Resends look unprofessional |

---

## 7. Timeline

| When | What |
|---|---|
| Week 1 day 1–2 | Build the Google Form, draft outreach email copy, get boss sign-off |
| Week 1 day 3 | Pilot send to 5 friendly alumni |
| Week 1 day 5 | Iterate form based on pilot feedback |
| Week 2 day 1 | Full send to all ~50 alumni |
| Week 2 day 7 | Reminder email |
| Week 3 | Phone follow-up for non-responders |
| Week 4 | Reconcile names, partition flights, compute first norms (PPL only as MVP) |

---

## 8. Open decisions for boss

- **Incentive yes/no.** $25 gift card × ~30 responses = ~$750. Cheap insurance on response rate.
- **Who signs the outreach email.** Carries more weight from a named Provectus principal than from "Provectus Analytics."
- **Public-transparency scope confirm.** The consent checkbox commits us to marketing use of anonymized aggregates. If that's broader than boss expects, narrow the language.

---

## 9. What this plan does NOT do (deferred)

- Doesn't pull invoice/cost data — that's a separate Reporting Hub investigation (Invoice Detail report). Cost partitioning piggybacks on the same rating buckets once we have them.
- Doesn't set up FSP automation — manual CSV export from Reporting Hub is the working assumption.
- Doesn't address current/future students — they don't need a survey because their boundaries can be captured prospectively (e.g., instructor-tags lesson type or rating manually going forward). Separate workstream.
