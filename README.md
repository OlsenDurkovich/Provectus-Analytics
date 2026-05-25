# Provectus Analytics

Pipeline for measuring student training cost, hours, and duration per rating, using Flight Schedule Pro (FSP) Reporting Hub exports + alumni survey data.

See `ROADMAP.md` for phases and `SYNTHETIC_DATA_README.md` for the test data setup.

## Quick start

```bash
pip install -e ".[dev,dashboard]"
pytest                                       # run all tests (17, ~1.5s)
python -m provectus_analytics.cli run        # full pipeline against synthetic data
python app.py                                # Dash web app at http://127.0.0.1:8050
```

## Layout

```
src/provectus_analytics/
  schema.py        SQLite DDL
  db.py            connection helpers
  ingest.py        load CSV exports into the DB
  reconcile.py     survey name ↔ FSP client name matching
  partition.py     assign flights to rating buckets
  milestones.py    cumulative metrics at each milestone
  norms.py         per-rating cohort norms (P25/median/P75) + outlier filter
  cli.py           end-to-end runner
  web/             Dash web app (Phase 8)
    app.py           app factory + sidebar + routing
    theme.py         Plotly template + color tokens
    data.py          cached DB queries
    components.py    reusable UI (metric cards, tables, etc.)
    pages/           one file per route — All Ratings, Rating Detail, Student, Instructor

app.py             Dash entry point — `python app.py`
assets/styles.css  design system (Linear/Stripe/Strava/Whoop/Hex-inspired)
tests/             pytest suite (validates against ground_truth_per_milestone.csv)
```

## Conventions

- GitHub pushes are manual — confirm before `git push`.
- All synthetic data + outputs are CSV/xlsx in the repo root for visibility.
- The SQLite DB is treated as a derived artifact — deleted and rebuilt on each `ingest` run.
