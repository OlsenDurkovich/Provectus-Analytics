"""
Derive Phase 4 ground truth from the synthetic FSP data.

Reads:
- synthetic_fsp_reservations.csv
- synthetic_fsp_invoices.csv
- synthetic_alumni_survey.csv  (only used for name reconciliation)

Writes:
- ground_truth_per_milestone.csv  — per (alum, rating, milestone) cumulative metrics
- ground_truth_rating_norms.csv   — per-rating cohort norms (median, P25, P75)

The partitioner you build in Phase 4+5 should reproduce these numbers.
Re-run after regenerating synthetic data.
"""
import csv
import statistics
from datetime import date
from collections import defaultdict
from calendar import monthrange

# Rating windows — must match generator
WINDOWS = {
    "Alex Martinez": {
        "PPL": {"start": "2022-03", "solo": "2022-07", "xc": "2022-10", "end": "2022-12"},
        "IFR": {"start": "2023-01", "xc_pic": "2023-04", "end": "2023-06"},
        "COM": {"start": "2023-07", "end": "2023-10"},
        "AMEL":{"start": "2023-11", "end": "2023-12"},
        "CFI": {"start": "2024-01", "end": "2024-03"},
        "CFII":{"start": "2024-04", "end": "2024-05"},
        "MEI": {"start": "2024-06", "end": "2024-07"},
    },
    "Jamie Chen": {
        "PPL": {"start": "2021-09", "solo": "2022-02", "xc": "2022-06", "end": "2022-09"},
        "IFR": {"start": "2022-11", "xc_pic": "2023-03", "end": "2023-06"},
        "COM": {"start": "2023-08", "end": "2023-12"},
        "AMEL":{"start": "2024-02", "end": "2024-04"},
        "CFI": {"start": "2024-05", "end": "2024-09"},
        "CFII":{"start": "2024-10", "end": "2024-12"},
        "MEI": {"start": "2025-01", "end": "2025-03"},
    },
    "Sarah Williams": {
        "IFR": {"start": "2023-03", "xc_pic": "2023-07", "end": "2023-09"},
        "COM": {"start": "2023-10", "end": "2024-02"},
        "AMEL":{"start": "2024-03", "end": "2024-05"},
        "CFI": {"start": "2024-06", "end": "2024-10"},
        "CFII":{"start": "2024-11", "end": "2025-01"},
        "MEI": {"start": "2025-02", "end": "2025-04"},
    },
    "Marcus Johnson": {
        "IFR": {"start": "2022-06", "xc_pic": "2022-10", "end": "2023-01"},
        "COM": {"start": "2023-02", "end": "2023-05"},
        "AMEL":{"start": "2023-06", "end": "2023-08"},
        "CFI": {"start": "2023-09", "end": "2023-12"},
        "CFII":{"start": "2024-01", "end": "2024-02"},
        "MEI": {"start": "2024-03", "end": "2024-05"},
    },
    "Priya Patel": {
        "PPL": {"start": "2022-01", "solo": "2022-06", "xc": "2022-10", "end": "2023-01"},
        "IFR": {"start": "2023-02", "xc_pic": "2023-06", "end": "2023-09"},
        "COM": {"start": "2023-10", "end": "2024-02"},
        "AMEL":{"start": "2024-03", "end": "2024-05"},
        "CFI": {"start": "2024-06", "end": "2024-09"},
    },
    "David Kim": {
        "IFR": {"start": "2024-04", "xc_pic": "2024-08", "end": "2024-11"},
        "COM": {"start": "2024-12", "end": "2025-03"},
    },
    "Emma Thompson": {
        "PPL": {"start": "2020-10", "solo": "2021-03", "xc": "2021-08", "end": "2021-11"},
        "IFR": {"start": "2022-01", "xc_pic": "2022-05", "end": "2022-08"},
        "COM": {"start": "2022-09", "end": "2023-02"},
    },
    "Ryan O'Brien": {
        "PPL": {"start": "2020-02", "solo": "2020-08", "xc": "2021-02", "end": "2021-05"},
        "IFR": {"start": "2021-07", "xc_pic": "2021-12", "end": "2022-03"},
        "COM": {"start": "2022-04", "end": "2022-09"},
        "AMEL":{"start": "2022-10", "end": "2023-01"},
        "CFI": {"start": "2023-02", "end": "2023-06"},
        "CFII":{"start": "2023-07", "end": "2023-09"},
        "MEI": {"start": "2023-10", "end": "2023-12"},
    },
    "Sofia Garcia": {
        "PPL": {"start": "2023-04", "solo": "2023-09", "xc": "2024-03", "end": "2024-07"},
    },
    "Olivia Nguyen": {
        "PPL": {"start": "2021-05", "solo": "2021-10", "xc": "2022-02", "end": "2022-05"},
        "IFR": {"start": "2022-06", "xc_pic": "2022-11", "end": "2023-02"},
        "COM": {"start": "2023-03", "end": "2023-08"},
        "AMEL":{"start": "2023-06", "end": "2023-08"},
    },
    "Brandon Lee": {
        "CFI": {"start": "2024-02", "end": "2024-06"},
        "CFII":{"start": "2024-07", "end": "2024-09"},
        "MEI": {"start": "2024-10", "end": "2024-12"},
    },
    "Hannah Davis": {
        "PPL": {"start": "2022-08", "solo": "2023-01", "xc": "2023-07", "end": "2023-10"},
        "IFR": {"start": "2023-11", "xc_pic": "2024-03", "end": "2024-06"},
    },
    "Christopher Wilson": {
        "AMEL":{"start": "2023-08", "end": "2023-10"},
        "CFI": {"start": "2023-11", "end": "2024-02"},
        "MEI": {"start": "2024-03", "end": "2024-04"},
    },
    "Isabella Rodriguez": {
        "PPL": {"start": "2023-01", "solo": "2023-06", "xc": "2023-11", "end": "2024-02"},
        "IFR": {"start": "2024-03", "xc_pic": "2024-07", "end": "2024-10"},
        "COM": {"start": "2024-11", "end": "2025-02"},
        "AMEL":{"start": "2025-03", "end": "2025-04"},
        "CFI": {"start": "2025-05", "end": "2025-08"},
        "CFII":{"start": "2025-09", "end": "2025-10"},
        "MEI": {"start": "2025-11", "end": "2025-12"},
    },
    "Noah J. Carter": {
        "PPL": {"start": "2024-03", "solo": "2024-08", "xc": "2025-01", "end": "2025-04"},
        "IFR": {"start": "2025-05", "xc_pic": "2025-09", "end": "2025-12"},
        "COM": {"start": "2026-01", "end": "2026-04"},
    },
    "Ava Singh": {
        "PPL": {"start": "2021-06", "solo": "2021-11", "xc": "2022-04", "end": "2022-08"},
        "IFR": {"start": "2022-09", "xc_pic": "2023-02", "end": "2023-05"},
        "COM": {"start": "2023-06", "end": "2023-10"},
        "AMEL":{"start": "2023-11", "end": "2024-01"},
    },
    "Ethan Murphy": {
        "COM": {"start": "2024-01", "end": "2024-05"},
        "CFI": {"start": "2024-06", "end": "2024-09"},
        "CFII":{"start": "2024-10", "end": "2024-12"},
    },
    "Mia Foster": {
        "PPL": {"start": "2022-02", "solo": "2022-07", "xc": "2022-12", "end": "2023-03"},
        "IFR": {"start": "2023-04", "xc_pic": "2023-08", "end": "2023-11"},
        "COM": {"start": "2023-12", "end": "2024-04"},
        "AMEL":{"start": "2024-05", "end": "2024-07"},
    },
    "Lucas Bennett": {
        "IFR": {"start": "2022-08", "xc_pic": "2022-12", "end": "2023-03"},
        "COM": {"start": "2023-04", "end": "2023-07"},
        "CFI": {"start": "2023-08", "end": "2023-11"},
        "CFII":{"start": "2023-12", "end": "2024-02"},
    },
}

SURVEY_NAMES = {"Noah J. Carter": "Noah Carter"}  # FSP -> survey form name where different

def ym_first(s):
    y, m = s.split("-")
    return date(int(y), int(m), 1)

def ym_last(s):
    y, m = s.split("-")
    return date(int(y), int(m), monthrange(int(y), int(m))[1])

# ---- Load synthetic data ----
with open("synthetic_fsp_reservations.csv") as f:
    reservations = list(csv.DictReader(f))
with open("synthetic_fsp_invoices.csv") as f:
    invoices = list(csv.DictReader(f))

inv_by_res = defaultdict(list)
for inv in invoices:
    inv_by_res[inv["Reservation #"]].append(inv)

# ---- Compute per-milestone ground truth ----
per_milestone = []

for client, ratings in WINDOWS.items():
    survey_name = SURVEY_NAMES.get(client, client)
    for rating, window in ratings.items():
        # Filter to this client + rating's completed flights
        flights = [r for r in reservations
                   if r["Client"] == client
                   and r["Rating Hint (synthetic answer key)"] == rating
                   and r["Status"] == "Completed"]
        if not flights:
            continue
        flights.sort(key=lambda r: r["Date"])

        rating_start = ym_first(window["start"])

        # Identify milestones
        milestones = []
        if rating == "PPL":
            solos = [f for f in flights if f["Reservation Type"] == "Student Solo"]
            if solos:
                milestones.append(("first_solo", date.fromisoformat(solos[0]["Date"])))
                milestones.append(("xc_solos_complete", date.fromisoformat(solos[-1]["Date"])))
        elif rating == "IFR" and "xc_pic" in window:
            # XC PIC milestone is self-reported (no derivable flight marker) — use month-end
            milestones.append(("xc_pic_complete", ym_last(window["xc_pic"])))

        checkrides = [f for f in flights if f["Reservation Type"] == "Check Ride"]
        if checkrides:
            milestones.append(("checkride", date.fromisoformat(checkrides[0]["Date"])))

        for mname, mdate in milestones:
            cum = [f for f in flights if date.fromisoformat(f["Date"]) <= mdate]
            n = len(cum)
            hrs = sum(float(f["Length (hrs)"]) for f in cum)
            cost = sum(float(inv["Amount ($)"])
                       for f in cum
                       for inv in inv_by_res.get(f["Reservation #"], []))
            days = (mdate - rating_start).days
            per_milestone.append({
                "client_fsp": client,
                "survey_name": survey_name,
                "rating": rating,
                "milestone": mname,
                "milestone_date": mdate.isoformat(),
                "days_from_rating_start": days,
                "cumulative_flights": n,
                "cumulative_hours": round(hrs, 1),
                "cumulative_cost": round(cost, 2),
            })

# Sort for readability
RATING_ORDER = {"PPL": 0, "IFR": 1, "COM": 2, "AMEL": 3, "CFI": 4, "CFII": 5, "MEI": 6}
MILESTONE_ORDER = {"first_solo": 0, "xc_solos_complete": 1, "xc_pic_complete": 1, "checkride": 2}
per_milestone.sort(key=lambda r: (r["client_fsp"], RATING_ORDER[r["rating"]], MILESTONE_ORDER[r["milestone"]]))

with open("ground_truth_per_milestone.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=[
        "client_fsp", "survey_name", "rating", "milestone", "milestone_date",
        "days_from_rating_start", "cumulative_flights", "cumulative_hours", "cumulative_cost"
    ])
    w.writeheader()
    w.writerows(per_milestone)
print(f"per-milestone rows: {len(per_milestone)}")

# ---- Cohort norms (at checkride) ----
checkrides = [r for r in per_milestone if r["milestone"] == "checkride"]
agg = defaultdict(lambda: {"hours": [], "cost": [], "days": [], "flights": []})
for r in checkrides:
    a = agg[r["rating"]]
    a["hours"].append(r["cumulative_hours"])
    a["cost"].append(r["cumulative_cost"])
    a["days"].append(r["days_from_rating_start"])
    a["flights"].append(r["cumulative_flights"])

def stats3(vals):
    """Return (P25, median, P75). Falls back to (min, median, max) if n<4."""
    s = sorted(vals)
    n = len(s)
    med = statistics.median(s)
    if n >= 4:
        qs = statistics.quantiles(s, n=4)
        return qs[0], med, qs[2]
    return min(s), med, max(s)

with open("ground_truth_rating_norms.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["rating", "n_alumni",
                "p25_hours", "median_hours", "p75_hours",
                "p25_cost", "median_cost", "p75_cost",
                "p25_days", "median_days", "p75_days",
                "median_flights", "low_sample_flag"])
    for rating in ["PPL", "IFR", "COM", "AMEL", "CFI", "CFII", "MEI"]:
        if rating not in agg: continue
        a = agg[rating]
        n = len(a["hours"])
        p25h, medh, p75h = stats3(a["hours"])
        p25c, medc, p75c = stats3(a["cost"])
        p25d, medd, p75d = stats3(a["days"])
        medf = statistics.median(a["flights"])
        low = "Yes" if n < 10 else "No"
        w.writerow([rating, n,
                    round(p25h,1), round(medh,1), round(p75h,1),
                    round(p25c,2), round(medc,2), round(p75c,2),
                    int(p25d), int(medd), int(p75d),
                    int(medf), low])
print(f"rating norms written for: {sorted(agg.keys())}")
