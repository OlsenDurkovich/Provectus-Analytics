"""SQLite schema for Provectus Analytics (ROADMAP Phase 5).

Tables:
    students      one row per surveyed alum (or current FSP client we want to track)
    ratings       lookup of 7 ratings (PPL, IFR, COM, AMEL, CFI, CFII, MEI)
    enrollments   one row per (student, rating) reported via survey — the rating window
    flights       one row per FSP reservation (rating attribution via enrollment_id)
    invoices      one row per FSP invoice line item
    milestones    computed: cumulative metrics at each milestone date
    surveys       raw survey responses (audit trail)
"""

DDL = [
    """
    CREATE TABLE IF NOT EXISTS ratings (
        rating_id   INTEGER PRIMARY KEY,
        code        TEXT NOT NULL UNIQUE,    -- PPL, IFR, COM, AMEL, CFI, CFII, MEI
        display     TEXT NOT NULL,           -- Private Pilot, etc.
        sort_order  INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS students (
        student_id        INTEGER PRIMARY KEY,
        fsp_client_id     TEXT UNIQUE,        -- nullable: alum may not be matched yet
        fsp_display_name  TEXT,
        survey_name       TEXT,
        email             TEXT,
        consent_marketing INTEGER NOT NULL DEFAULT 0,  -- 0/1
        match_status      TEXT NOT NULL DEFAULT 'unmatched',  -- matched | unmatched | ambiguous
        match_notes       TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS enrollments (
        enrollment_id          INTEGER PRIMARY KEY,
        student_id             INTEGER NOT NULL REFERENCES students(student_id),
        rating_id              INTEGER NOT NULL REFERENCES ratings(rating_id),
        instance_num           INTEGER NOT NULL DEFAULT 0,  -- 0 for survey/normal; increments for OTHER recheck periods
        start_date             TEXT NOT NULL,         -- YYYY-MM-01 (month precision from survey); exact date for guesstimate
        checkride_date         TEXT NOT NULL,         -- YYYY-MM-LAST_DAY; '2099-12-31' sentinel for partial
        first_solo_date        TEXT,                  -- PPL only
        xc_solos_complete_date TEXT,                  -- PPL only
        xc_pic_complete_date   TEXT,                  -- IFR only
        source                 TEXT NOT NULL DEFAULT 'survey',   -- 'survey' | 'guesstimate'
        is_partial             INTEGER NOT NULL DEFAULT 0,       -- 1 if no checkride found yet
        UNIQUE (student_id, rating_id, instance_num)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS flights (
        flight_id        INTEGER PRIMARY KEY,
        fsp_reservation  TEXT NOT NULL UNIQUE,
        fsp_flight_num   TEXT,
        flight_date      TEXT NOT NULL,        -- YYYY-MM-DD
        length_hrs       REAL NOT NULL,
        reservation_type TEXT NOT NULL,         -- Dual Flight Training, Check Ride, Student Solo, ...
        status           TEXT NOT NULL,         -- Completed, Canceled
        student_id       INTEGER REFERENCES students(student_id),  -- nullable (maintenance has no student)
        client_raw       TEXT,                  -- FSP client string as imported, for traceability
        aircraft_tail    TEXT,
        aircraft_make    TEXT,
        aircraft_model   TEXT,
        aircraft_class   TEXT,                  -- SE_BASIC, SE_COMPLEX, ME (derived)
        instructor       TEXT,
        hobbs_hours      REAL,                  -- actual Hobbs hours (null = ground lesson or synthetic data)
        billing_category TEXT,                  -- AMEL|MEI|CFI|CFII|PRIMARY|MISC|NONE (null = synthetic/unknown)
        is_ground_lesson INTEGER NOT NULL DEFAULT 0,  -- 1 if no aircraft + no Hobbs
        enrollment_id    INTEGER REFERENCES enrollments(enrollment_id),  -- set by partitioner; null = unattributed
        partition_notes  TEXT,                  -- e.g. 'resolved via SE/ME tiebreaker'
        rating_label     TEXT                   -- optional FSP-native or manual rating tag (PPL/IFR/COM/AMEL/CFI/CFII/MEI); when set, partition uses this directly
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_line_id   INTEGER PRIMARY KEY,
        fsp_invoice       TEXT NOT NULL,
        invoice_date      TEXT NOT NULL,
        student_id        INTEGER REFERENCES students(student_id),
        flight_id         INTEGER REFERENCES flights(flight_id),
        description       TEXT,
        category          TEXT,            -- Aircraft, Instructor, Ground
        qty               REAL,
        rate              REAL,
        amount            REAL NOT NULL,
        status            TEXT             -- Paid, Outstanding
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS milestones (
        milestone_id            INTEGER PRIMARY KEY,
        enrollment_id           INTEGER NOT NULL REFERENCES enrollments(enrollment_id),
        milestone_name          TEXT NOT NULL,    -- first_solo, xc_solos_complete, xc_pic_complete, checkride
        milestone_date          TEXT NOT NULL,
        days_from_rating_start  INTEGER NOT NULL,
        cumulative_flights      INTEGER NOT NULL,
        cumulative_hours        REAL NOT NULL,
        cumulative_cost         REAL NOT NULL,
        UNIQUE (enrollment_id, milestone_name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS surveys (
        survey_id      INTEGER PRIMARY KEY,
        student_id     INTEGER REFERENCES students(student_id),
        submitted_at   TEXT,
        raw_response   TEXT NOT NULL    -- JSON dump of the full row
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS flight_overrides (
        override_id    INTEGER PRIMARY KEY,
        flight_id      INTEGER NOT NULL REFERENCES flights(flight_id) ON DELETE CASCADE,
        field_name     TEXT NOT NULL,       -- e.g. 'is_ground_lesson', 'billing_category'
        value          TEXT,                -- stored as TEXT, cast at apply time
        note           TEXT,
        set_at         TEXT NOT NULL,       -- ISO timestamp
        UNIQUE (flight_id, field_name)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_flights_student      ON flights(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_flights_date         ON flights(flight_date)",
    "CREATE INDEX IF NOT EXISTS idx_flights_enrollment   ON flights(enrollment_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_flight      ON invoices(flight_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_student     ON invoices(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_milestones_enrollment ON milestones(enrollment_id)",
    "CREATE INDEX IF NOT EXISTS idx_overrides_flight     ON flight_overrides(flight_id)",
]

# Rating lookup seed data
RATING_SEED = [
    (1, "PPL",   "Private Pilot",                  1),
    (2, "IFR",   "Instrument Rating",              2),
    (3, "COM",   "Commercial Single-Engine",       3),
    (4, "AMEL",  "Multi-Engine (AMEL)",            4),
    (5, "CFI",   "Certificated Flight Instructor", 5),
    (6, "CFII",  "Instrument Instructor",          6),
    (7, "MEI",   "Multi-Engine Instructor",        7),
    (8, "OTHER", "Other Training",                 8),  # recheck prep / unclassified training
]
