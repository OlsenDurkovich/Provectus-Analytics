# How to run Provectus Analytics

A local dashboard that reads CSV exports from Flight Schedule Pro and turns them into per-rating cost / hours / duration analytics.

## First time

1. Open the `Provectus Analytics` folder in Finder.
2. **Right-click `Provectus.command` → Open.** (macOS will warn you about an unidentified developer the first time — click "Open" anyway. Only needed once.)
3. A Terminal window will open and start installing things. This takes 1–2 minutes the first time.
4. When setup is done, your default browser will open to the dashboard at `http://127.0.0.1:8050`.

After the first time, just **double-click** `Provectus.command` — no right-click needed.

## To stop the app

Either close the Terminal window or press **Ctrl+C** inside it. The browser tab can stay open; the dashboard just won't respond until you launch again.

## Updating data

The dashboard auto-detects whether to use real exports or fall back to synthetic CSVs.

**Real exports (preferred):** drop two XLSX files into `FSP Exports/`:

| File | Where it comes from |
|---|---|
| `FlightDetail_Report.xlsx` | FSP Reporting Hub → Flight Detail |
| `Invoice_Report.xlsx`      | FSP Reporting Hub → Invoice Detail |

Easiest workflow: use the Claude-in-Chrome prompt in `tools/fsp_export_prompt.md`. It downloads both to `~/Downloads/`, then click **"Import latest FSP exports"** in the sidebar — it copies + renames + rebuilds in one step.

**Important:** the rebuild is **incremental + override-preserving**. Per-flight tweaks on the Flights page (e.g. reclassifying a multi-engine event as ground) survive every weekly re-import. They live in the `flight_overrides` table and are re-applied at the end of each rebuild.

**Synthetic fallback:** if `FSP Exports/` is empty, the rebuild reads the four synthetic CSVs (`synthetic_fsp_*.csv`, `synthetic_alumni_survey.csv`). Used by tests + early development. Column structure documented in `SYNTHETIC_DATA_README.md`.

## Updating the app itself

When new features ship, you'll either:
- Get a new copy of this folder (just replace it), or
- Run `git pull` from Terminal if you're on the developer-managed copy.

The `.venv` folder caches dependencies; if a future update changes them, delete `.venv` and double-click `Provectus.command` to reinstall.

## Troubleshooting

- **"unidentified developer" warning:** right-click → Open the first time only.
- **Browser doesn't open:** go to `http://127.0.0.1:8050` manually.
- **App says "port already in use":** another copy is already running. Close that Terminal window first.
- **Data looks wrong after replacing CSVs:** click "Rebuild DB" in the sidebar, then reload.
- **Anything else:** show Olsen the Terminal output — that's where errors print.
