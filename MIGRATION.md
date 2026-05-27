# Website Migration — Working Doc

Source of truth for the Phase 10 → 14 migration to a hosted Railway deployment with auth. Supersedes any inline plan in chat.

This doc captures: what we're shipping, what changed from the original plan after auditing the actual codebase, the execution order, and the open questions still on the table.

---

## Stack reality (2026-05-26)

- Backend: FastAPI app factory at [`src/provectus_analytics/api/main.py`](src/provectus_analytics/api/main.py), uvicorn entry on port 8050.
- Frontend: Vite + React 19 + TypeScript + react-router-dom + @tanstack/react-query under [`frontend/`](frontend/). Build outputs to `frontend/dist/` and is served by FastAPI via `StaticFiles` + SPA fallback.
- Data layer: SQLite at `provectus.db` (repo root, hardcoded), schema in [`schema.py`](src/provectus_analytics/schema.py), ingest in [`ingest.py`](src/provectus_analytics/ingest.py), reconcile in [`reconcile.py`](src/provectus_analytics/reconcile.py), partitioner in [`partition.py`](src/provectus_analytics/partition.py).
- Launcher: [`Provectus.command`](Provectus.command) — local `.command` double-click. Going away in Phase 13.
- Tests: 59 passing as of branch base.
- **No auth, no CORS, no security headers, no deployment config yet.**

---

## Plan adjustments (from audit)

| Original plan | Adjustment |
|---|---|
| 10.1 fall back to `synthetic_alumni_survey.xlsx` | Real file is `.xlsx`, synthetic is `.csv`. Loader checks for `alumni_survey.xlsx` first, falls back to `synthetic_alumni_survey.csv`. |
| 10.2 column-mapping problem | Real Google Form survey has identical column names to synthetic CSV. Problem is only date-format normalization (datetime → "Month YYYY" strings that `partition.py` expects). |
| 10.3 native label support | FSP `Type` column is hardcoded-fallback to "Dual Flight Training" ([ingest.py:287](src/provectus_analytics/ingest.py:287)). Real fix: read an optional rating-label column if FSP exports include one, plumb through to `partition.py` overlap resolver. |
| Phase 12 "replaces sidebar import" | Current import scans `~/Downloads` ([import_exports.py:71](src/provectus_analytics/import_exports.py:71)). Railway containers have no `~/Downloads` — this is a **deploy blocker**, not optional. Phase 12 must land before Phase 13. |
| Phase 13.3 Railway volume | DB path is hardcoded to `REPO_ROOT / "provectus.db"` ([queries.py:17](src/provectus_analytics/api/queries.py:17)). Code change required, not just a Railway env var. Plus add `PRAGMA journal_mode=WAL` on init to survive the rebuild blocking reads. |
| Phase 13.2 railway.toml only | Need a multi-stage Dockerfile (node:20 → python:3.12-slim). `railway.toml` alone won't orchestrate two runtimes cleanly. |
| Phase 14.2 security headers | Add `Content-Security-Policy` too (public-facing SPA). |

---

## Risks called out

1. **`/api/import-fsp` and `/api/rebuild` are public today.** ([meta.py:15-29](src/provectus_analytics/api/routers/meta.py:15-29)) Do not deploy to Railway before Phase 11 auth lands.
2. **`reservation_type` defaults to "Dual Flight Training"** if FSP doesn't send it. There's no validation. If FSP changes its export shape, we'll silently mis-attribute.
3. **`/api/rebuild` can be triggered concurrently with reads.** SQLite default journal mode blocks all reads during a rebuild. Phase 13 fixes this with WAL.
4. **Synthetic vs real data co-existence.** [`queries.py:86-98`](src/provectus_analytics/api/queries.py:86) purges synthetic rows when real exports appear. If a real survey lands without real flights, the cohort will look broken. Phase 10.2 must handle the "real survey, synthetic flights" interim state during testing.

---

## Status snapshot (end of overnight session)

All five branches shipped locally — no pushes yet (per user preference).
Five feature branches chained off main; merge order matches the table below.

| Branch                       | What's in it                                            | Status |
|---|---|---|
| `feat/phase-10-data-fixes`   | Real `alumni_survey.xlsx` ingest, FSP `rating_label`    | ✅ committed |
| `feat/phase-11-auth`         | JWT auth backend + login UI gate                        | ✅ committed |
| `feat/phase-12-upload`       | POST /api/upload/fsp + upload dialog                    | ✅ committed |
| `feat/phase-13-railway`      | Env-driven paths, WAL, Dockerfile, railway.toml         | ✅ committed |
| `feat/phase-14-hardening`    | CORS lock, security headers, pip-audit pass             | ✅ committed |

Test stats at the end of Phase 14:
- Backend: 111 passing
- Frontend: 76 passing
- tsc -b clean
- vite build clean
- pip-audit -r requirements.txt: no known vulnerabilities

Things left for the user to do (cannot do without them):
1. `git push -u origin <branch>` for each branch (manual push per CLAUDE.md).
2. Open PRs in the desired merge order (10 → 11 → 12 → 13 → 14).
3. On Railway: create project, add volume mounted at `/data`, set the env
   vars listed in the table below, deploy.
4. Optional: smoke-test `docker build .` locally before pushing — wasn't
   exercised in this session.

---

## Railway setup (Phase 13 — what the user does in the dashboard)

Container ships with these env defaults (set in Dockerfile):

| Env var            | Default                       | What to override |
|---|---|---|
| `DB_PATH`          | `/data/provectus.db`          | leave as-is on Railway |
| `FSP_EXPORTS_DIR`  | `/data/fsp-exports`           | leave as-is on Railway |
| `REAL_SURVEY_PATH` | `/data/alumni_survey.xlsx`    | leave as-is on Railway |
| `PROVECTUS_ENV`    | `prod`                        | leave as-is on Railway |
| `PORT`             | 8080 (Railway injects)        | Railway sets automatically |

User must set these in the Railway dashboard → Variables:

- `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`. **Required** when `PROVECTUS_ENV=prod`; the app will refuse to start without it.
- `INITIAL_ADMIN_EMAIL` + `INITIAL_ADMIN_PASSWORD` — only used on first startup when the users table is empty. The boot path will seed a single admin user and never touch the table again. Safe to leave set or unset thereafter.

Volume mount: add a Railway volume of any size (1 GB is plenty), mount path `/data`. The volume survives redeploys; the container's working tree does not.

Healthcheck: `GET /api/healthz` returns 200 unauthenticated; `railway.toml` is already wired to it.

## Open questions for the morning

- **Survey `Timestamp` is a datetime now, not a string.** [`reconcile.py:64`](src/provectus_analytics/reconcile.py:64) uses `raw.get("Timestamp")` directly as `submitted_at`. We're storing the JSON-stringified datetime, which means `.fromisoformat()` will be needed downstream if anything reads it. Currently nothing does, so it's fine — but worth flagging.
- **`Consent: Yes/No`** comes through as a string in the real survey too — matches synthetic, no work needed.
- **`Anything else`** column is a freeform text field we don't currently surface anywhere. Out of scope for now.
- **Custom domain**: plan mentions `analytics.provectusaviation.com`. Not configured yet; punted to user after Railway smoke test.
