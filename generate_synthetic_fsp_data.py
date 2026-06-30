"""
Generate synthetic FSP Reporting Hub exports paired with synthetic_alumni_survey.csv.

Outputs (written next to this script):
- synthetic_fsp_clients.csv       (FSP People/Users roster)
- synthetic_fsp_reservations.csv  (Reservation Detail export)
- synthetic_fsp_invoices.csv      (Invoice Detail export — schema is a GUESS, see README)

Seeded RNG (seed=42) for reproducibility. Re-running produces identical output.
"""
import csv
import random
from datetime import date, timedelta
from calendar import monthrange

random.seed(42)

# ============= FLEET =============
SE_BASIC = [
    ("N4521P", "Cessna", "172N"),
    ("N7732K", "Cessna", "172S"),
    ("N8814M", "Piper", "PA-28-181"),
    ("N6603L", "Cessna", "172S"),
]
SE_COMPLEX = [
    ("N9923R", "Cessna", "182RG"),
    ("N1175C", "Piper", "PA-28R-201"),
]
ME = [
    ("N3340T", "Piper", "PA-44-180"),
    ("N5567W", "Piper", "PA-44-180"),
]

INSTRUCTORS = [
    "Mike Anderson",
    "Sarah Phillips",
    "Tom Reyes",
    "Jenny Park",
    "Doug Hayes",
]

# Hourly rates ($/hr wet for aircraft)
RATES = {
    "N4521P": 175, "N7732K": 185, "N8814M": 190, "N6603L": 185,
    "N9923R": 230, "N1175C": 235,
    "N3340T": 385, "N5567W": 385,
}
INSTRUCTOR_RATE = 75
GROUND_RATE = 65

# ============= ALUMNI ROSTER (mirrors synthetic_alumni_survey.csv) =============
# (survey_name, fsp_display_name, email, client_id, joined_year)
ALUMNI = [
    ("Alex Martinez",       "Alex Martinez",       "alex.martinez@gmail.com",        "C1001", 2022),
    ("Jamie Chen",          "Jamie Chen",          "jamie.chen@gmail.com",           "C1002", 2021),
    ("Sarah Williams",      "Sarah Williams",      "swilliams88@yahoo.com",          "C1003", 2023),
    ("Marcus Johnson",      "Marcus Johnson",      "marcus.j.johnson@gmail.com",     "C1004", 2022),
    ("Priya Patel",         "Priya Patel",         "priya.patel.aviation@gmail.com", "C1005", 2022),
    ("David Kim",           "David Kim",           "dkim.flies@protonmail.com",      "C1006", 2024),
    ("Emma Thompson",       "Emma Thompson",       "emma.thompson1995@gmail.com",    "C1007", 2020),
    ("Ryan O'Brien",        "Ryan O'Brien",        "ryanobrien.atl@gmail.com",       "C1008", 2020),
    ("Sofia Garcia",        "Sofia Garcia",        "sofiag.garcia@outlook.com",      "C1009", 2023),
    ("Tyler Brooks",        "Tyler Brooks",        "tylerbrooks23@gmail.com",        "C1010", 2023),
    ("Olivia Nguyen",       "Olivia Nguyen",       "olivia.nguyen@gmail.com",        "C1011", 2021),
    ("Brandon Lee",         "Brandon Lee",         "blee.cfi@gmail.com",             "C1012", 2024),
    ("Hannah Davis",        "Hannah Davis",        "hdavis.av@gmail.com",            "C1013", 2022),
    ("Christopher Wilson",  "Christopher Wilson",  "chris.wilson.atp@gmail.com",     "C1014", 2023),
    ("Isabella Rodriguez",  "Isabella Rodriguez",  "isabella.rodriguez@gmail.com",   "C1015", 2023),
    ("Noah Carter",         "Noah J. Carter",      "noah.carter@gmail.com",          "C1016", 2024),  # EDGE: name mismatch
    ("Ava Singh",           "Ava Singh",           "ava.singh@gmail.com",            "C1017", 2021),
    ("Ethan Murphy",        "Ethan Murphy",        "emurphy.flies@gmail.com",        "C1018", 2024),
    ("Mia Foster",          "Mia Foster",          "mia.foster.av@gmail.com",        "C1019", 2022),
    ("Lucas Bennett",       "Lucas Bennett",       "lucasb@gmail.com",               "C1020", 2022),
]

# Noise clients — current students + non-students in FSP but not in survey
NOISE_CLIENTS = [
    # (display_name, client_id, email, joined_year, note)
    ("Henry Walsh",        "C1021", "henry.walsh@gmail.com",        2025, "current student (mid PPL)"),
    ("Grace Liu",          "C1022", "grace.liu@gmail.com",          2025, "current student (early PPL)"),
    ("Daniel Park",        "C1023", "daniel.park@gmail.com",        2024, "current student (IFR phase)"),
    ("Priya Nair",         "C1028", "priya.nair@gmail.com",         2025, "current student (PPL, near checkride)"),
    ("Marcus Bell",        "C1029", "marcus.bell@gmail.com",        2026, "current student (PPL, just started)"),
    ("Diana Cho",          "C1030", "diana.cho@gmail.com",          2025, "current student (PPL, steady)"),
    ("Michael Sanders",    "C1024", "msanders@yahoo.com",           2024, "discovery flight only"),
    ("Karen Yoshida",      "C1025", "kyoshida@gmail.com",           2025, "discovery flight only"),
    ("Robert Klein",       "C1026", "rklein.flies@gmail.com",       2019, "aircraft owner"),
    ("Patricia O'Donnell", "C1027", "pat.odonnell@outlook.com",     2018, "aircraft owner"),
]

# ============= RATING WINDOWS (sourced from survey) =============
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
        "AMEL":{"start": "2023-06", "end": "2023-08"},  # EDGE: concurrent with COM
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
    "Noah J. Carter": {  # FSP name; survey form says "Noah Carter" — name reconciliation edge case
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

# Per-rating training-hours target ranges (rough industry averages, not Provectus-specific)
RATING_HOURS = {
    "PPL":  (55, 70),
    "IFR":  (40, 55),
    "COM":  (20, 35),
    "AMEL": (10, 16),
    "CFI":  (25, 38),
    "CFII": (10, 16),
    "MEI":  (8, 14),
}

# ============= Helpers =============
def parse_ym(s):
    y, m = s.split("-")
    return int(y), int(m)

def ym_to_date_range(start_ym, end_ym):
    sy, sm = parse_ym(start_ym)
    ey, em = parse_ym(end_ym)
    return date(sy, sm, 1), date(ey, em, monthrange(ey, em)[1])

def random_date_between(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

def pick_aircraft(rating):
    if rating in ("AMEL", "MEI"):
        return random.choice(ME)
    if rating == "COM":
        return random.choice(SE_COMPLEX) if random.random() < 0.7 else random.choice(SE_BASIC)
    return random.choice(SE_BASIC)

def get_primary_instructor(client_name):
    return INSTRUCTORS[sum(ord(c) for c in client_name) % len(INSTRUCTORS)]

def pick_instructor(primary):
    return primary if random.random() < 0.8 else random.choice([i for i in INSTRUCTORS if i != primary])

# ============= Flight generation =============
def gen_rating_flights(client_name, rating, window, res_counter, flight_counter):
    flights = []
    start, end = ym_to_date_range(window["start"], window["end"])
    primary = get_primary_instructor(client_name)
    target_hours = random.uniform(*RATING_HOURS[rating])
    hours_logged = 0.0

    has_solo = rating == "PPL" and "solo" in window
    solo_start = xc_complete = None
    if has_solo:
        sy, sm = parse_ym(window["solo"])
        solo_start = date(sy, sm, random.randint(5, 25))
        xy, xm = parse_ym(window["xc"])
        xc_complete = date(xy, xm, monthrange(xy, xm)[1])

    checkride_date = random_date_between(date(end.year, end.month, 1), end)
    training_end = checkride_date - timedelta(days=3)
    if training_end < start:
        training_end = checkride_date - timedelta(days=1)

    while hours_logged < target_hours - 1.5:
        d = random_date_between(start, training_end)
        length = round(random.uniform(1.2, 2.4), 1)
        aircraft = pick_aircraft(rating)

        is_solo = (has_solo and solo_start <= d <= xc_complete and random.random() < 0.30)

        if random.random() < 0.04:
            # canceled
            flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num="",
                                date=d, length=0,
                                type="Student Solo" if is_solo else "Dual Flight Training",
                                status="Canceled", client=client_name,
                                tail=aircraft[0], make=aircraft[1], model=aircraft[2],
                                instructor="" if is_solo else pick_instructor(primary),
                                rating_hint=rating))
            res_counter[0] += 1
            continue

        if is_solo:
            res_type = "Student Solo"
            instructor = ""
        else:
            res_type = "Dual Flight Training"
            instructor = pick_instructor(primary)

        flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num=f"F{flight_counter[0]:06d}",
                            date=d, length=length, type=res_type, status="Completed",
                            client=client_name, tail=aircraft[0], make=aircraft[1], model=aircraft[2],
                            instructor=instructor, rating_hint=rating))
        res_counter[0] += 1
        flight_counter[0] += 1
        hours_logged += length

    # Checkride
    ca = pick_aircraft(rating)
    flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num=f"F{flight_counter[0]:06d}",
                        date=checkride_date, length=round(random.uniform(1.5, 2.5), 1),
                        type="Check Ride", status="Completed", client=client_name,
                        tail=ca[0], make=ca[1], model=ca[2], instructor="",
                        rating_hint=rating))
    res_counter[0] += 1
    flight_counter[0] += 1
    return flights

def gen_tyler_incomplete(res_counter, flight_counter):
    flights = []
    start, end = ym_to_date_range("2023-08", "2024-01")
    primary = get_primary_instructor("Tyler Brooks")
    hours = 0
    while hours < 25:
        d = random_date_between(start, end)
        length = round(random.uniform(1.2, 2.0), 1)
        aircraft = pick_aircraft("PPL")
        if random.random() < 0.05:
            flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num="",
                                date=d, length=0, type="Dual Flight Training",
                                status="Canceled", client="Tyler Brooks",
                                tail=aircraft[0], make=aircraft[1], model=aircraft[2],
                                instructor="", rating_hint="PPL (incomplete)"))
            res_counter[0] += 1
            continue
        flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num=f"F{flight_counter[0]:06d}",
                            date=d, length=length, type="Dual Flight Training",
                            status="Completed", client="Tyler Brooks",
                            tail=aircraft[0], make=aircraft[1], model=aircraft[2],
                            instructor=pick_instructor(primary), rating_hint="PPL (incomplete)"))
        res_counter[0] += 1
        flight_counter[0] += 1
        hours += length
    return flights

def gen_noise(res_counter, flight_counter):
    flights = []
    overall_start, overall_end = date(2020, 1, 1), date(2026, 5, 1)

    # Maintenance
    for _ in range(35):
        d = random_date_between(overall_start, overall_end)
        a = random.choice(SE_BASIC + SE_COMPLEX + ME)
        flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num="",
                            date=d, length=round(random.uniform(0.5, 4.0), 1),
                            type="Maintenance", status="Completed", client="",
                            tail=a[0], make=a[1], model=a[2], instructor="", rating_hint=""))
        res_counter[0] += 1

    # Owner flights
    owners = ["Robert Klein", "Patricia O'Donnell"]
    for _ in range(20):
        d = random_date_between(overall_start, overall_end)
        a = random.choice(SE_BASIC + SE_COMPLEX)
        flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num=f"F{flight_counter[0]:06d}",
                            date=d, length=round(random.uniform(1.0, 3.5), 1),
                            type="Owner Flight", status="Completed",
                            client=random.choice(owners),
                            tail=a[0], make=a[1], model=a[2], instructor="", rating_hint=""))
        res_counter[0] += 1
        flight_counter[0] += 1

    # Discovery / introductory flights
    discovery = ["Michael Sanders", "Karen Yoshida"]
    for _ in range(12):
        d = random_date_between(date(2023, 1, 1), overall_end)
        a = random.choice(SE_BASIC)
        flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num=f"F{flight_counter[0]:06d}",
                            date=d, length=round(random.uniform(0.8, 1.3), 1),
                            type="Introductory Flight", status="Completed",
                            client=random.choice(discovery),
                            tail=a[0], make=a[1], model=a[2],
                            instructor=random.choice(INSTRUCTORS), rating_hint=""))
        res_counter[0] += 1
        flight_counter[0] += 1

    # Current students (in FSP, not in survey — should NOT appear in alumni norms).
    # A spread of in-progress profiles for the completion-forecast: near-done,
    # steady-mid, slow, brand-new, over-hours, stalled.
    current = [
        ("Henry Walsh", date(2025, 5, 1), date(2026, 5, 15), 35),
        ("Grace Liu", date(2025, 9, 1), date(2026, 5, 15), 22),
        ("Daniel Park", date(2024, 11, 1), date(2026, 5, 15), 45),
        ("Priya Nair", date(2025, 10, 1), date(2026, 6, 18), 30),   # ~50h, on track, near done
        ("Marcus Bell", date(2026, 3, 15), date(2026, 6, 18), 14),  # ~22h, just started
        ("Diana Cho", date(2025, 6, 1), date(2026, 6, 15), 26),     # ~42h, steady mid
    ]
    for name, s, e, n in current:
        primary = get_primary_instructor(name)
        for _ in range(n):
            d = random_date_between(s, e)
            length = round(random.uniform(1.2, 2.2), 1)
            a = pick_aircraft("PPL")
            if random.random() < 0.06:
                flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num="",
                                    date=d, length=0, type="Dual Flight Training",
                                    status="Canceled", client=name,
                                    tail=a[0], make=a[1], model=a[2],
                                    instructor="", rating_hint="current student"))
                res_counter[0] += 1
                continue
            flights.append(dict(res_num=f"R{res_counter[0]:06d}", flight_num=f"F{flight_counter[0]:06d}",
                                date=d, length=length, type="Dual Flight Training",
                                status="Completed", client=name,
                                tail=a[0], make=a[1], model=a[2],
                                instructor=pick_instructor(primary), rating_hint="current student"))
            res_counter[0] += 1
            flight_counter[0] += 1
    return flights

# ============= Cadence demo cohort (PPL completers) =============
# A batch of completed Private-Pilot students with a DELIBERATE training-cadence
# signal, so the "cadence vs cost" insight has something to show. Higher weekly
# cadence → fewer total hours (massed-practice retention effect) → lower cost and
# fewer calendar days. Non-survey, so they flow through guesstimate as PPL
# completers. CLEARLY SYNTHETIC — illustrative of a real, studied effect, not
# measured from real alumni. (name, cadence flights/wk, email, client_id)
CADENCE_COMPLETERS = [
    ("Olivia Brennan",  1.2, "olivia.brennan@gmail.com",  "C1401", "2024"),
    ("Liam Foster",     1.7, "liam.foster@gmail.com",     "C1402", "2024"),
    ("Sophia Reyes",    2.2, "sophia.reyes@gmail.com",    "C1403", "2024"),
    ("Noah Whitfield",  2.6, "noah.whitfield@gmail.com",  "C1404", "2024"),
    ("Emma Caldwell",   3.0, "emma.caldwell@gmail.com",   "C1405", "2024"),
    ("Mason Trent",     3.3, "mason.trent@gmail.com",     "C1406", "2024"),
    ("Ava Donovan",     3.6, "ava.donovan@gmail.com",     "C1407", "2025"),
    ("Lucas Hartman",   3.9, "lucas.hartman@gmail.com",   "C1408", "2025"),
    ("Mia Sutton",      4.2, "mia.sutton@gmail.com",      "C1409", "2025"),
    ("Ethan Bauer",     4.5, "ethan.bauer@gmail.com",     "C1410", "2025"),
    ("Chloe Marsh",     4.8, "chloe.marsh@gmail.com",     "C1411", "2025"),
    ("Jack Holloway",   5.2, "jack.holloway@gmail.com",   "C1412", "2025"),
    ("Ruby Vance",      5.6, "ruby.vance@gmail.com",      "C1413", "2025"),
    ("Owen Pratt",      6.0, "owen.pratt@gmail.com",      "C1414", "2025"),
    ("Isla Romero",     6.5, "isla.romero@gmail.com",     "C1415", "2025"),
    # a few more in the lower brackets so "≤2.5×" isn't only legacy alumni
    ("Caleb Ford",      1.4, "caleb.ford@gmail.com",      "C1416", "2024"),
    ("Nora Quinn",      2.0, "nora.quinn@gmail.com",      "C1417", "2024"),
    ("Theo Walsh",      2.4, "theo.walsh@gmail.com",      "C1418", "2024"),
    # extra density for the mid brackets (2.5–4×)
    ("Gabriel Stone",   3.4, "gabriel.stone@gmail.com",   "C1419", "2024"),
    ("Hazel Webb",      3.7, "hazel.webb@gmail.com",      "C1420", "2024"),
    ("Adrian Cole",     4.0, "adrian.cole@gmail.com",     "C1421", "2025"),
    ("Lila Hayes",      4.3, "lila.hayes@gmail.com",      "C1422", "2025"),
    ("Felix Moreno",    4.6, "felix.moreno@gmail.com",    "C1423", "2025"),
]


def gen_cadence_completers(res_counter, flight_counter):
    flights = []
    for name, cadence, _email, _cid, _yr in CADENCE_COMPLETERS:
        primary = get_primary_instructor(name)
        # retention effect: denser schedule → fewer hours. Intercept tuned so the
        # cadence cohort's hours sit around/just below the existing PPL alumni and
        # decline monotonically across the low/med/high cadence buckets.
        target_hours = max(46.0, min(80.0, 66.0 - 2.8 * (cadence - 0.9) + random.uniform(-1.5, 1.5)))
        n_flights = max(18, round(target_hours / 1.8))
        per_flight = target_hours / n_flights
        interval_days = 7.0 / cadence
        span_days = int(n_flights * interval_days)
        # finish (checkride) somewhere in the last ~2 years
        checkride_date = random_date_between(date(2024, 3, 1), date(2026, 4, 15))
        start = checkride_date - timedelta(days=span_days + 5)
        solo_every = max(4, n_flights // 4)
        for i in range(n_flights):
            d = start + timedelta(days=int(i * interval_days) + random.randint(0, 1))
            if d >= checkride_date:
                d = checkride_date - timedelta(days=2)
            length = round(max(1.0, min(2.6, per_flight + random.uniform(-0.3, 0.3))), 1)
            a = random.choice(SE_BASIC)
            is_solo = (i > solo_every and i % solo_every == 0)
            flights.append(dict(
                res_num=f"R{res_counter[0]:06d}",
                flight_num=f"F{flight_counter[0]:06d}",
                date=d, length=length,
                type="Student Solo" if is_solo else "Dual Flight Training",
                status="Completed", client=name,
                tail=a[0], make=a[1], model=a[2],
                instructor="" if is_solo else pick_instructor(primary),
                rating_hint="PPL (cadence cohort)"))
            res_counter[0] += 1
            flight_counter[0] += 1
        # checkride
        a = random.choice(SE_BASIC)
        flights.append(dict(
            res_num=f"R{res_counter[0]:06d}", flight_num=f"F{flight_counter[0]:06d}",
            date=checkride_date, length=round(random.uniform(1.5, 2.2), 1),
            type="Check Ride", status="Completed", client=name,
            tail=a[0], make=a[1], model=a[2], instructor="",
            rating_hint="PPL (cadence cohort)"))
        res_counter[0] += 1
        flight_counter[0] += 1
    return flights


# ============= Main =============
res_counter = [100000]
flight_counter = [50000]
all_flights = []

for fsp_name, ratings in WINDOWS.items():
    for rating, window in ratings.items():
        all_flights.extend(gen_rating_flights(fsp_name, rating, window, res_counter, flight_counter))

all_flights.extend(gen_tyler_incomplete(res_counter, flight_counter))
all_flights.extend(gen_noise(res_counter, flight_counter))
# Appended LAST so existing students' RNG draws (incl. the ground-truth alum) are
# untouched. These are the cadence-vs-cost demo completers.
all_flights.extend(gen_cadence_completers(res_counter, flight_counter))
all_flights.sort(key=lambda f: f["date"])

# --- Write reservations ---
with open("synthetic_fsp_reservations.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Reservation #", "Flight #", "Date", "Length (hrs)", "Reservation Type",
                "Status", "Client", "Aircraft Tail", "Aircraft Make", "Aircraft Model",
                "Instructor", "Rating Hint (synthetic answer key)"])
    for fl in all_flights:
        w.writerow([fl["res_num"], fl["flight_num"], fl["date"].isoformat(), fl["length"],
                    fl["type"], fl["status"], fl["client"], fl["tail"], fl["make"], fl["model"],
                    fl["instructor"], fl["rating_hint"]])
print(f"Reservations written: {len(all_flights)}")

# --- Write clients ---
with open("synthetic_fsp_clients.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Client ID", "Display Name", "First Name", "Last Name", "Email",
                "Status", "Date Added", "Notes (synthetic)"])
    for survey_name, fsp_name, email, cid, joined in ALUMNI:
        parts = fsp_name.split(" ", 1)
        note = "alum"
        if survey_name != fsp_name:
            note = f"alum — survey name differs ('{survey_name}')"
        w.writerow([cid, fsp_name, parts[0], parts[1] if len(parts) > 1 else "",
                    email, "Active", f"{joined}-01-15", note])
    for fsp_name, cid, email, joined, note in NOISE_CLIENTS:
        parts = fsp_name.split(" ", 1)
        w.writerow([cid, fsp_name, parts[0], parts[1] if len(parts) > 1 else "",
                    email, "Active", f"{joined}-01-15", note])
    for fsp_name, _cad, email, cid, joined in CADENCE_COMPLETERS:
        parts = fsp_name.split(" ", 1)
        w.writerow([cid, fsp_name, parts[0], parts[1] if len(parts) > 1 else "",
                    email, "Active", f"{joined}-01-15", "PPL completer (cadence cohort)"])
print(f"Clients written: {len(ALUMNI) + len(NOISE_CLIENTS) + len(CADENCE_COMPLETERS)}")

# --- Write invoices (schema is a GUESS, see README) ---
invoice_rows = []
inv_counter = [200000]
billable_types = {"Dual Flight Training", "Check Ride", "Student Solo", "Introductory Flight"}

for fl in all_flights:
    if fl["status"] != "Completed" or fl["type"] not in billable_types or not fl["client"]:
        continue
    inv_num = f"INV{inv_counter[0]:06d}"
    inv_counter[0] += 1
    # Per-flight RNG seeded on the reservation number: a flight's invoice (dates,
    # instructor add-on hours, ground lines, paid status) depends ONLY on itself,
    # so adding/removing other students never perturbs an existing alum's cost.
    inv_rng = random.Random(fl["res_num"])
    inv_date = fl["date"] + timedelta(days=inv_rng.randint(0, 3))
    status = "Paid" if inv_rng.random() < 0.92 else "Outstanding"
    ac_rate = RATES.get(fl["tail"], 200)

    invoice_rows.append(dict(inv=inv_num, date=inv_date, client=fl["client"], res=fl["res_num"],
                             desc=f"Aircraft rental - {fl['tail']} ({fl['make']} {fl['model']})",
                             category="Aircraft", qty=fl["length"], rate=ac_rate,
                             amount=round(fl["length"] * ac_rate, 2), status=status))

    if fl["instructor"]:
        instr_hrs = round(fl["length"] + inv_rng.choice([0.0, 0.0, 0.3, 0.5]), 1)
        invoice_rows.append(dict(inv=inv_num, date=inv_date, client=fl["client"], res=fl["res_num"],
                                 desc=f"Instructor time - {fl['instructor']}",
                                 category="Instructor", qty=instr_hrs, rate=INSTRUCTOR_RATE,
                                 amount=round(instr_hrs * INSTRUCTOR_RATE, 2), status=status))
        if inv_rng.random() < 0.25:
            gh = round(inv_rng.uniform(0.5, 1.5), 1)
            invoice_rows.append(dict(inv=inv_num, date=inv_date, client=fl["client"], res=fl["res_num"],
                                     desc="Ground instruction / briefing",
                                     category="Ground", qty=gh, rate=GROUND_RATE,
                                     amount=round(gh * GROUND_RATE, 2), status=status))

with open("synthetic_fsp_invoices.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Invoice #", "Invoice Date", "Client", "Reservation #",
                "Line Item Description", "Category", "Quantity (hrs/units)",
                "Rate ($)", "Amount ($)", "Status"])
    for r in invoice_rows:
        w.writerow([r["inv"], r["date"].isoformat(), r["client"], r["res"], r["desc"],
                    r["category"], r["qty"], r["rate"], r["amount"], r["status"]])
print(f"Invoice lines written: {len(invoice_rows)}")
