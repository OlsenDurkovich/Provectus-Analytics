# FSP Reporting Hub — Claude in Chrome export prompt

Paste this prompt into Claude in Chrome when you are already logged into
Flight Schedule Pro. It instructs Claude to run the **two** Reporting Hub reports
the dashboard needs (Flight Detail + Invoice Detail) and download each to your
Downloads folder with the canonical filename the dashboard expects.

> Reservation Detail used to be in this list but was dropped — Flight Detail
> already contains every column we use from it.

> **Honesty flag (Olsen → boss):** the exact menu paths inside FSP have not been
> recorded by me. Claude in Chrome will need to navigate the Reporting Hub UI on
> its own based on what it sees. If a step in the prompt is wrong, edit it once
> and the prompt is fixed for next time.

---

## Prerequisites (one-time)

1. Install the **Claude in Chrome** extension. (Chrome / Brave — Anthropic extension.)
2. Sign in to Flight Schedule Pro in the same browser. Stay signed in.
3. Pin the Claude extension to the toolbar.

## Triggering an export

1. Open `https://app.flightschedulepro.com/` and confirm you are signed in.
2. Click the Claude in Chrome icon and paste the prompt below.
3. Claude will narrate each step and ask for confirmation on downloads — say yes.
4. When done, two files should be sitting in `~/Downloads/`. Then either:
   - click **Import latest FSP exports** in the dashboard sidebar, or
   - drag the two files into `FSP Exports/` manually and click **Rebuild DB**.

---

## The prompt (copy this whole block)

```
You are operating Flight Schedule Pro on my behalf via the Claude in Chrome
extension. I am already logged in. Run the two Reporting Hub reports below and
download each as XLSX to my Downloads folder. Use the exact filenames I specify
so my downstream tooling can find them. Use a ROLLING 3-YEAR window: END = today,
START = January 1 of the year three years before today (e.g. if today is
2026-05-25, START = 2023-01-01). Do not change any settings, do not edit any
data, do not share, email, or schedule anything from inside FSP. If a report has
a "Save" or "Schedule" option, ignore it — we only export.

Reports to run (in order):

1. Reporting Hub → Flight Detail
   - Date range: 3 years ago Jan 1 → today
   - Include all clients, all aircraft, all instructors (no filter)
   - Export format: XLSX
   - Save as: FlightDetail_Report.xlsx

2. Reporting Hub → Invoice Detail
   - Date range: 3 years ago Jan 1 → today (use Invoice Date)
   - Include all clients
   - Export format: XLSX
   - Save as: Invoice_Report.xlsx

Rules of engagement:
- Read the page and tell me which Reporting Hub item you see before clicking.
- If you cannot find a report by name, list what you do see and stop.
- Confirm each download with me before triggering it.
- If FSP asks for any agreement, terms-of-use acceptance, or permissions
  change, STOP and ask me — do not click through on my behalf.
- Never enter, view, or copy any credit card, banking, or password fields.
- When both files are downloaded, tell me the filename + size of each.
```

---

## What you do next

After the two files land in `~/Downloads/`, run the dashboard and click
**Import latest FSP exports** in the sidebar. The dashboard will copy the two
matching files into `FSP Exports/` (with canonical names), run Rebuild DB, and
reload.

The rebuild is **incremental + override-preserving** — your per-flight tweaks on
the Flights page survive every weekly re-import.
