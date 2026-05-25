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

The dashboard reads four CSV files from this folder:

| File | Where it comes from |
|---|---|
| `synthetic_fsp_clients.csv` | FSP Reporting Hub → Sales by Client (or equivalent) |
| `synthetic_fsp_reservations.csv` | FSP Reporting Hub → Reservation Detail |
| `synthetic_fsp_invoices.csv` | FSP Reporting Hub → Invoice Detail |
| `synthetic_alumni_survey.csv` | Google Form → Responses → Download as CSV |

Until real data swaps in, these are synthetic. To use real data:
1. Replace the four CSVs above (keep the same filenames).
2. In the sidebar of the dashboard, click **"Rebuild DB."**
3. Reload the page.

The exact column structure each file needs is documented in `SYNTHETIC_DATA_README.md`. The synthetic files in this folder are valid examples to copy the headers from.

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
