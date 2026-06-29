"""Generate synthetic_stage_checks.csv from the ground-truth milestones.

Each stage check is dated shortly BEFORE the milestone it precedes, with the
matching rating, stage label, and (engine-appropriate) aircraft. This makes the
synthetic stage checks coherent with the synthetic students' real milestone
dates, so the ingest/reconcile join can be validated end-to-end.

Run from repo root:  python tools/make_synthetic_stage_checks.py
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (rating, milestone) -> (stage label, days the check precedes the milestone)
STAGE_MAP = {
    ("PPL", "first_solo"):          ("Pre-solo", 7),
    ("PPL", "xc_solos_complete"):   ("Pre-cross-country (solo XC)", 7),
    ("PPL", "checkride"):           ("Pre-checkride (end of course)", 7),
    ("IFR", "xc_pic_complete"):     ("Stage 1 - XC time complete", 0),
    ("IFR", "checkride"):           ("Stage 2 - pre-checkride", 7),
    ("COM", "checkride"):           ("Pre-checkride (end of course)", 7),
    ("AMEL", "checkride"):          ("Pre-checkride (end of course)", 7),
    ("CFI", "checkride"):           ("Pre-checkride (end of course)", 7),
    ("CFII", "checkride"):          ("Pre-checkride (end of course)", 7),
    ("MEI", "checkride"):           ("Pre-checkride (end of course)", 7),
}
MULTI_RATINGS = {"AMEL", "MEI"}
CFIS = ["Mike Anderson", "Rachel Torres", "David Kim", "Laura Bennett"]
CHIEFS = ["Tom Halloran (Chief)", "Susan Vance (Chief)"]


def load_emails() -> dict[str, str]:
    emails: dict[str, str] = {}
    with open(ROOT / "synthetic_fsp_clients.csv", newline="") as f:
        for row in csv.DictReader(f):
            emails[row["Display Name"].strip()] = row["Email"].strip()
    return emails


def main() -> None:
    emails = load_emails()
    out_rows = []
    seen_students = []  # stable ordering for deterministic CFI assignment

    with open(ROOT / "ground_truth_per_milestone.csv", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            key = (row["rating"], row["milestone"])
            if key not in STAGE_MAP:
                continue
            stage, lead = STAGE_MAP[key]
            name = row["client_fsp"].strip()
            if name not in seen_students:
                seen_students.append(name)
            cfi = CFIS[seen_students.index(name) % len(CFIS)]
            chief = CHIEFS[i % len(CHIEFS)]
            check_date = date.fromisoformat(row["milestone_date"]) - timedelta(days=lead)
            hours = float(row["cumulative_hours"])
            # a small, deterministic minority of stage checks need a repeat
            result = "Unsatisfactory - additional training" if i % 13 == 5 else "Satisfactory - proceed"
            aircraft = "BE-76" if row["rating"] in MULTI_RATINGS else ("C172" if i % 2 == 0 else "PA-28")
            out_rows.append({
                "date": check_date.isoformat(),
                "student_name": name,
                "student_email": emails.get(name, ""),
                "rating": row["rating"],
                "stage": stage,
                "result": result,
                "hobbs_hours": round(hours, 1),
                "conducting_instructor": chief,
                "primary_cfi": cfi,
                "aircraft": aircraft,
                "notes": "",
            })

    out_path = ROOT / "synthetic_stage_checks.csv"
    fields = ["date", "student_name", "student_email", "rating", "stage", "result",
              "hobbs_hours", "conducting_instructor", "primary_cfi", "aircraft", "notes"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {len(out_rows)} stage-check rows to {out_path.name}")


if __name__ == "__main__":
    main()
