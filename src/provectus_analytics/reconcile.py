"""Match survey respondents to FSP client roster.

Strategy (most reliable first):
    1. Email exact match (case-insensitive)
    2. Normalized full-name exact match
    3. Token-subset name match — survey tokens are a subset of FSP tokens.
       Catches middle-initial cases ("Noah Carter" ⊂ "Noah J. Carter").
    4. Unmatched — flagged for manual reconciliation, new students row created.

After matching, this also:
    - Updates students.survey_name, email (if missing), consent_marketing
    - Links surveys.student_id
    - Sets flights.student_id from client_raw → fsp_display_name
    - Sets invoices.student_id from joined flights.student_id
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass
class MatchResult:
    survey_idx: int
    survey_name: str
    survey_email: str
    student_id: int | None
    method: str            # 'email' | 'name_exact' | 'name_subset' | 'unmatched'
    notes: str


def _norm(s: str | None) -> str:
    return (s or "").strip().casefold()


def _name_tokens(s: str | None) -> set[str]:
    """Tokenize a name; drop punctuation and 1-char initial tokens for subset matching."""
    if not s:
        return set()
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in s)
    return {t.casefold() for t in cleaned.split() if len(t) > 1}


def reconcile(conn: sqlite3.Connection) -> list[MatchResult]:
    """Match survey rows to FSP clients. Returns one MatchResult per survey row."""
    students = list(conn.execute(
        "SELECT student_id, fsp_display_name, email FROM students WHERE fsp_client_id IS NOT NULL"
    ))
    by_email = {_norm(s["email"]): s for s in students if s["email"]}
    by_name = {_norm(s["fsp_display_name"]): s for s in students if s["fsp_display_name"]}

    results: list[MatchResult] = []
    surveys = list(conn.execute("SELECT survey_id, raw_response FROM surveys ORDER BY survey_id"))

    for sv in surveys:
        raw = json.loads(sv["raw_response"])
        sname = raw.get("Full name", "")
        semail = raw.get("Email", "")
        consent_yes = 1 if (raw.get("Consent", "").strip().lower() == "yes") else 0
        match: sqlite3.Row | None = None
        method = "unmatched"
        notes = ""

        # 1. Email
        if semail and _norm(semail) in by_email:
            match = by_email[_norm(semail)]
            method = "email"

        # 2. Exact name
        if match is None and _norm(sname) in by_name:
            match = by_name[_norm(sname)]
            method = "name_exact"

        # 3. Token subset (handles middle initials)
        if match is None:
            survey_tokens = _name_tokens(sname)
            if survey_tokens:
                candidates = [
                    s for s in students
                    if survey_tokens.issubset(_name_tokens(s["fsp_display_name"]))
                ]
                if len(candidates) == 1:
                    match = candidates[0]
                    method = "name_subset"
                    notes = f"FSP display name '{match['fsp_display_name']}' has extra tokens"
                elif len(candidates) > 1:
                    method = "unmatched"
                    notes = f"ambiguous: survey name '{sname}' matches multiple FSP clients: " \
                            + ", ".join(c["fsp_display_name"] for c in candidates)

        if match is not None:
            student_id = match["student_id"]
            conn.execute(
                """UPDATE students
                   SET survey_name = ?,
                       email = COALESCE(email, ?),
                       consent_marketing = ?,
                       match_status = 'matched',
                       match_notes = ?
                   WHERE student_id = ?""",
                (sname, semail, consent_yes, notes or None, student_id),
            )
        else:
            # Create a new students row for the unmatched survey respondent
            cur = conn.execute(
                """INSERT INTO students
                       (survey_name, email, consent_marketing, match_status, match_notes)
                       VALUES (?, ?, ?, 'unmatched', ?)""",
                (sname, semail, consent_yes, notes or "no FSP client match"),
            )
            student_id = cur.lastrowid

        conn.execute("UPDATE surveys SET student_id = ? WHERE survey_id = ?",
                     (student_id, sv["survey_id"]))

        results.append(MatchResult(
            survey_idx=sv["survey_id"], survey_name=sname, survey_email=semail,
            student_id=student_id, method=method, notes=notes,
        ))

    # Now link flights → students by FSP display name (the raw client field)
    conn.execute(
        """UPDATE flights
           SET student_id = (
               SELECT student_id FROM students
               WHERE students.fsp_display_name = flights.client_raw
               LIMIT 1
           )
           WHERE client_raw IS NOT NULL"""
    )
    # Link invoices → students via flights
    conn.execute(
        """UPDATE invoices
           SET student_id = (
               SELECT student_id FROM flights WHERE flights.flight_id = invoices.flight_id
           )
           WHERE flight_id IS NOT NULL"""
    )
    conn.commit()
    return results
