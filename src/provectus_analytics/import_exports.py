"""Import the latest FSP report exports from ~/Downloads into FSP Exports/.

Used by the Phase 9 (automation) flow:
    Claude in Chrome → downloads 3 XLSX → user clicks "Import latest FSP exports"
    in the dashboard sidebar → this module picks the freshest matching file for
    each report and copies it (with the canonical name) into FSP Exports/.

Designed to be safe: it never deletes the originals, never modifies files that
don't match the report patterns, and only copies if a newer source exists.
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

# Canonical names the rest of the pipeline points at.
CANONICAL = {
    "flight_detail":   "FlightDetail_Report.xlsx",
    "invoice":         "Invoice_Report.xlsx",
}

# Match either the canonical name or the messy variants FSP itself emits.
# Examples we have observed:
#   FlightDetail_Report SG.xlsx          → flight_detail
#   2026 Flight 5:25:26.xlsx             → flight_detail
#   Invoice report SG.xlsx               → invoice
#   2026 Invoice 5:25:26.xlsx            → invoice
PATTERNS = {
    "flight_detail":   re.compile(r"(flight[_ ]?detail|flight\s).*\.xlsx$", re.I),
    "invoice":         re.compile(r"invoice.*\.xlsx$", re.I),
}


@dataclass
class ImportResult:
    report: str
    source: Path | None
    destination: Path | None
    action: str   # "copied", "skipped_no_match", "skipped_already_current"

    def line(self) -> str:
        if self.action == "copied":
            return f"  ✓ {self.report}: {self.source.name} → {self.destination.name}"
        if self.action == "skipped_already_current":
            return f"  · {self.report}: already current ({self.destination.name})"
        return f"  ✗ {self.report}: no matching file found"


def _newest_match(folder: Path, pattern: re.Pattern) -> Path | None:
    if not folder.exists():
        return None
    candidates = [p for p in folder.iterdir() if p.is_file() and pattern.search(p.name)]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def import_latest(
    downloads: Path | None = None,
    exports_dir: Path | None = None,
) -> list[ImportResult]:
    """Copy the newest matching XLSX for each report from downloads → exports_dir.

    A file is considered newer than the existing canonical file if its mtime is
    strictly greater (1s tolerance).
    """
    if downloads is None:
        downloads = Path(os.path.expanduser("~/Downloads"))
    if exports_dir is None:
        # default: <repo>/FSP Exports
        exports_dir = Path(__file__).resolve().parents[2] / "FSP Exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    results: list[ImportResult] = []
    for report, pattern in PATTERNS.items():
        canonical_name = CANONICAL[report]
        dest = exports_dir / canonical_name

        # Look in Downloads first, then exports_dir (in case user dropped files there).
        src = _newest_match(downloads, pattern)
        if src is None and exports_dir.exists():
            # Also accept a freshly-renamed file already sitting in exports_dir.
            in_exports = _newest_match(exports_dir, pattern)
            # Don't treat the canonical file as its own source.
            if in_exports and in_exports.name != canonical_name:
                src = in_exports

        if src is None:
            results.append(ImportResult(report, None, dest, "skipped_no_match"))
            continue

        if dest.exists() and src.stat().st_mtime <= dest.stat().st_mtime + 1:
            results.append(ImportResult(report, src, dest, "skipped_already_current"))
            continue

        shutil.copy2(src, dest)
        results.append(ImportResult(report, src, dest, "copied"))

    return results


def summarize(results: list[ImportResult]) -> str:
    copied = sum(1 for r in results if r.action == "copied")
    missing = sum(1 for r in results if r.action == "skipped_no_match")
    lines = [r.line() for r in results]
    header = f"Imported {copied} of {len(results)} reports"
    if missing:
        header += f" — {missing} missing"
    return header + "\n" + "\n".join(lines)
