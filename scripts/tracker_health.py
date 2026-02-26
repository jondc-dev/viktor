#!/usr/bin/env python3
"""
Commitment tracker health check for Viktor.

Parses COMMITMENTS_TRACKER.md for:
- Pending [ ] items
- Overdue items (past dates)
- File staleness (>24h since last modification)

Returns a dict with:
    warnings      : list of P1/P2 warning strings
    pending_count : int
    overdue_count : int
    stale         : bool

Designed to be called from the cognitive loop GATHER phase.

Usage (standalone):
    tracker_health.py [path/to/COMMITMENTS_TRACKER.md]
"""

import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

WORKSPACE_ROOT = Path("~/clawd").expanduser()
DEFAULT_TRACKER = WORKSPACE_ROOT / "COMMITMENTS_TRACKER.md"
STALE_HOURS = 24

# Regex patterns
_PENDING_RE = re.compile(r"^\s*-\s*\[\s*\]\s+(.+)$", re.MULTILINE)
_DONE_RE = re.compile(r"^\s*-\s*\[x\]\s+(.+)$", re.MULTILINE | re.IGNORECASE)
# Match dates like 2025-12-31 or 31 Dec 2025 or Dec 31 inside text
_DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),               # ISO: 2025-12-31
    re.compile(r"\b(\d{1,2}\s+\w{3,9}\s+\d{4})\b"),       # 31 December 2025
    re.compile(r"\b(\w{3,9}\s+\d{1,2},?\s+\d{4})\b"),     # December 31, 2025
]


def _parse_date(text: str) -> date | None:
    """Try to extract and parse the first recognisable date in *text*."""
    for pattern in _DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        raw = m.group(1).strip().rstrip(",")
        for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def check_tracker(tracker_path: Path | None = None) -> dict:
    """
    Analyse the commitments tracker and return a health report.

    Returns:
        {
            "warnings":      ["P1: ...", "P2: ..."],
            "pending_count": int,
            "overdue_count": int,
            "stale":         bool,
            "tracker_found": bool,
        }
    """
    if tracker_path is None:
        tracker_path = DEFAULT_TRACKER

    result: dict = {
        "warnings": [],
        "pending_count": 0,
        "overdue_count": 0,
        "stale": False,
        "tracker_found": False,
    }

    if not tracker_path.exists():
        result["warnings"].append(
            f"P1: COMMITMENTS_TRACKER.md not found at {tracker_path}"
        )
        return result

    result["tracker_found"] = True

    # Staleness check
    try:
        age = datetime.now().timestamp() - tracker_path.stat().st_mtime
        if age > STALE_HOURS * 3600:
            result["stale"] = True
            hours = age / 3600
            result["warnings"].append(
                f"P2: COMMITMENTS_TRACKER.md has not been updated in "
                f"{hours:.0f}h (threshold: {STALE_HOURS}h)"
            )
    except OSError:
        pass

    # Parse content
    try:
        content = tracker_path.read_text(encoding="utf-8")
    except OSError as exc:
        result["warnings"].append(f"P1: Could not read tracker: {exc}")
        return result

    # Count pending items
    pending_items = _PENDING_RE.findall(content)
    result["pending_count"] = len(pending_items)

    today = date.today()
    overdue: list[str] = []

    for item_text in pending_items:
        item_date = _parse_date(item_text)
        if item_date and item_date < today:
            overdue.append(item_text.strip())

    result["overdue_count"] = len(overdue)

    if overdue:
        for item in overdue:
            result["warnings"].append(f"P1: OVERDUE commitment: {item[:120]}")

    if result["pending_count"] > 10:
        result["warnings"].append(
            f"P2: High pending count ({result['pending_count']} items) — "
            "consider reviewing COMMITMENTS_TRACKER.md"
        )

    return result


def main() -> None:
    tracker_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    report = check_tracker(tracker_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
