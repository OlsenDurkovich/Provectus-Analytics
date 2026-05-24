"""End-to-end pipeline runner.

    python -m provectus_analytics.cli run [--data-dir PATH] [--db PATH]

Runs: init → ingest → reconcile → build_enrollments → partition → milestones → norms.
Writes:
    {db}                     SQLite DB with all derived tables
    {data-dir}/output/       per_milestone.csv, rating_norms.csv, unmatched.csv

Defaults assume the synthetic CSVs are in the same directory as this script.
"""
from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

from . import db as _db
from . import ingest, reconcile, partition, milestones, norms

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2]


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def run(data_dir: Path, db_path: Path) -> dict:
    conn = _db.init_db(db_path)

    counts = ingest.ingest_all(
        conn,
        data_dir / "synthetic_fsp_clients.csv",
        data_dir / "synthetic_fsp_reservations.csv",
        data_dir / "synthetic_fsp_invoices.csv",
        data_dir / "synthetic_alumni_survey.csv",
    )
    print(f"ingested: {counts}")

    matches = reconcile.reconcile(conn)
    matched = sum(1 for m in matches if m.method != "unmatched")
    print(f"reconciled: {matched}/{len(matches)} matched"
          f" (methods: {dict((m.method, sum(1 for x in matches if x.method == m.method)) for m in matches)})")

    enr_count = partition.build_enrollments(conn)
    print(f"enrollments built: {enr_count}")

    stats = partition.partition_flights(conn)
    print(f"flights partitioned: {stats}")

    ms_count = milestones.compute_milestones(conn)
    print(f"milestones computed: {ms_count}")

    rating_norms = norms.compute_rating_norms(conn)
    print(f"rating norms: {len(rating_norms)} ratings")

    # Output CSVs for inspection / comparison with ground truth
    out_dir = data_dir / "output"
    per_milestone_rows = []
    for row in conn.execute(
        """SELECT s.fsp_display_name AS client_fsp,
                  s.survey_name      AS survey_name,
                  r.code             AS rating,
                  m.milestone_name   AS milestone,
                  m.milestone_date,
                  m.days_from_rating_start,
                  m.cumulative_flights,
                  m.cumulative_hours,
                  m.cumulative_cost
           FROM milestones m
           JOIN enrollments e USING (enrollment_id)
           JOIN students    s USING (student_id)
           JOIN ratings     r USING (rating_id)
           ORDER BY s.fsp_display_name, r.sort_order, m.milestone_date"""
    ):
        per_milestone_rows.append(dict(row))
    _write_csv(out_dir / "per_milestone.csv", per_milestone_rows,
               ["client_fsp", "survey_name", "rating", "milestone", "milestone_date",
                "days_from_rating_start", "cumulative_flights",
                "cumulative_hours", "cumulative_cost"])

    _write_csv(out_dir / "rating_norms.csv",
               [asdict(n) for n in rating_norms],
               list(asdict(rating_norms[0]).keys()) if rating_norms else [])

    unmatched_rows = [
        dict(r) for r in conn.execute(
            "SELECT student_id, survey_name, email, match_status, match_notes "
            "FROM students WHERE match_status != 'matched'"
        )
    ]
    _write_csv(out_dir / "unmatched.csv", unmatched_rows,
               ["student_id", "survey_name", "email", "match_status", "match_notes"])

    print(f"output written to {out_dir}/")
    return {"counts": counts, "matched": matched, "enrollments": enr_count,
            "partition": stats, "milestones": ms_count, "rating_norms": len(rating_norms)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="provectus-analytics")
    sub = p.add_subparsers(dest="cmd", required=True)
    runp = sub.add_parser("run", help="Run the full pipeline")
    runp.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    runp.add_argument("--db", type=Path, default=Path("provectus.db"))
    args = p.parse_args(argv)

    if args.cmd == "run":
        run(args.data_dir, args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
