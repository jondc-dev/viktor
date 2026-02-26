#!/usr/bin/env python3
"""
Calendar Scanner for Viktor

Scans JV's calendar events to detect meeting patterns,
identify preparation needs, and surface scheduling risks.

Calendar file: calendar-events.json (in workspace root)
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

CALENDAR_FILE = WORKSPACE / "calendar-events.json"

# Dubai timezone
DUBAI_UTC_OFFSET = timedelta(hours=4)

# Pattern detection thresholds
BACK_TO_BACK_GAP_MINS  = 15   # meetings with ≤15 min gap = back-to-back
HEAVY_DAY_COUNT        = 5    # ≥5 meetings = heavy day
LONG_MEETING_MINS      = 90   # meetings ≥90 min = long
LATE_MEETING_HOUR      = 18   # meetings starting at or after 18:00 = late
NO_LUNCH_START         = 12   # 12:00
NO_LUNCH_END           = 14   # 14:00
PREP_NEEDED_KEYWORDS   = [
    "board", "presentation", "pitch", "review", "investor",
    "client", "demo", "interview", "annual", "quarterly",
]

logger = logging.getLogger(__name__)


def _now_dubai() -> datetime:
    return datetime.now(timezone.utc) + DUBAI_UTC_OFFSET


def _parse_time(time_str: str) -> Optional[int]:
    """Parse 'HH:MM' into minutes since midnight, or None."""
    try:
        h, m = map(int, time_str.strip().split(":"))
        return h * 60 + m
    except Exception:
        return None


def _load_calendar_events(for_date: Optional[str] = None) -> list[dict]:
    """
    Load calendar events for a given date (default: today).

    Args:
        for_date: ISO date string (YYYY-MM-DD), defaults to today.

    Returns:
        List of event dicts for that date.
    """
    if not CALENDAR_FILE.exists():
        return []

    target = for_date or date.today().isoformat()

    try:
        with open(CALENDAR_FILE, "r") as f:
            cal_data = json.load(f)

        if isinstance(cal_data, list):
            return [e for e in cal_data if e.get("date", "") == target]
        elif isinstance(cal_data, dict):
            return cal_data.get(target, [])
        return []

    except Exception as e:
        logger.error(f"Error loading calendar: {e}")
        return []


def scan_calendar(for_date: Optional[str] = None) -> dict:
    """
    Scan JV's calendar and return raw event data with metadata.

    Args:
        for_date: ISO date string to scan (defaults to today).

    Returns:
        Dict with events list and basic metadata.
    """
    events = _load_calendar_events(for_date)
    target = for_date or date.today().isoformat()

    return {
        "date": target,
        "events": events,
        "count": len(events),
        "has_calendar": CALENDAR_FILE.exists(),
    }


def detect_meeting_patterns(events: list[dict]) -> dict:
    """
    Detect scheduling patterns that Viktor should flag for JV.

    Detects:
      - back-to-back meetings (≤15 min gap)
      - heavy meeting day (≥5 meetings)
      - no lunch break (12:00–14:00 blocked)
      - late meetings (starting ≥18:00)
      - long meetings (≥90 min)

    Args:
        events: List of event dicts with 'time' and 'duration_mins' fields.

    Returns:
        Dict of pattern flags and relevant event lists.
    """
    patterns: dict = {
        "back_to_back": [],
        "is_heavy_day": False,
        "no_lunch_break": False,
        "late_meetings": [],
        "long_meetings": [],
    }

    if not events:
        return patterns

    # Sort events by start time
    timed_events = []
    for ev in events:
        start = _parse_time(ev.get("time", ""))
        duration = ev.get("duration_mins", 60)
        if start is not None:
            timed_events.append({**ev, "_start_mins": start, "_end_mins": start + duration})
    timed_events.sort(key=lambda x: x["_start_mins"])

    # Heavy day
    if len(timed_events) >= HEAVY_DAY_COUNT:
        patterns["is_heavy_day"] = True

    # Back-to-back and late meetings
    for i, ev in enumerate(timed_events):
        # Back-to-back: gap between this event's end and next event's start
        if i + 1 < len(timed_events):
            gap = timed_events[i + 1]["_start_mins"] - ev["_end_mins"]
            if 0 <= gap <= BACK_TO_BACK_GAP_MINS:
                patterns["back_to_back"].append(
                    {
                        "first": ev.get("title", ev.get("summary", "Meeting")),
                        "second": timed_events[i + 1].get("title", timed_events[i + 1].get("summary", "Meeting")),
                        "gap_mins": gap,
                    }
                )

        # Late meeting
        if ev["_start_mins"] >= LATE_MEETING_HOUR * 60:
            patterns["late_meetings"].append(ev.get("title", ev.get("summary", "Meeting")))

        # Long meeting
        duration = ev.get("duration_mins", 60)
        if duration >= LONG_MEETING_MINS:
            patterns["long_meetings"].append(
                {
                    "title": ev.get("title", ev.get("summary", "Meeting")),
                    "duration_mins": duration,
                }
            )

    # No lunch break: check if 12:00–14:00 window is fully blocked
    lunch_start = NO_LUNCH_START * 60
    lunch_end   = NO_LUNCH_END   * 60
    lunch_free = True
    for ev in timed_events:
        if ev["_start_mins"] < lunch_end and ev["_end_mins"] > lunch_start:
            lunch_free = False
            break
    if timed_events and not lunch_free:
        patterns["no_lunch_break"] = True

    return patterns


def identify_prep_needed(events: list[dict]) -> list[dict]:
    """
    Identify events that require advance preparation by Viktor.

    Args:
        events: List of event dicts.

    Returns:
        List of {event, prep_type, priority} dicts.
    """
    prep_items = []
    for ev in events:
        title = ev.get("title", ev.get("summary", "")).lower()
        if any(kw in title for kw in PREP_NEEDED_KEYWORDS):
            prep_items.append(
                {
                    "event": ev.get("title", ev.get("summary", "Meeting")),
                    "time": ev.get("time", ""),
                    "prep_type": "brief_and_materials",
                    "priority": "high",
                }
            )
    return prep_items


def get_calendar_summary(for_date: Optional[str] = None) -> dict:
    """
    Return a full calendar summary for JV including patterns and prep needs.

    Args:
        for_date: ISO date string (defaults to today).

    Returns:
        Comprehensive calendar summary dict.
    """
    try:
        scan = scan_calendar(for_date)
        events = scan["events"]
        patterns = detect_meeting_patterns(events)
        prep = identify_prep_needed(events)

        # Build human-readable flags
        flags = []
        if patterns["is_heavy_day"]:
            flags.append(f"Heavy meeting day ({scan['count']} meetings)")
        if patterns["back_to_back"]:
            flags.append(f"{len(patterns['back_to_back'])} back-to-back slot(s)")
        if patterns["no_lunch_break"]:
            flags.append("No lunch break — 12:00–14:00 fully blocked")
        if patterns["late_meetings"]:
            flags.append(f"Late meeting(s): {', '.join(patterns['late_meetings'][:2])}")
        if patterns["long_meetings"]:
            lm = patterns["long_meetings"]
            flags.append(f"Long meeting: {lm[0]['title']} ({lm[0]['duration_mins']} min)")

        return {
            "date": scan["date"],
            "events": events,
            "event_count": scan["count"],
            "patterns": patterns,
            "prep_needed": prep,
            "flags": flags,
            "has_calendar": scan["has_calendar"],
        }

    except Exception as e:
        logger.error(f"Error generating calendar summary: {e}")
        return {"error": str(e), "events": [], "flags": []}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    summary = get_calendar_summary()
    import json
    print(json.dumps(summary, indent=2, default=str))
