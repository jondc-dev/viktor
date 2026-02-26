#!/usr/bin/env python3
"""
Context Scanner for Viktor

Scans Viktor's workspace to build a comprehensive picture of JV's current
context: open items, upcoming deadlines, calendar events, people waiting,
memory files, and needs state.

Workspace: ~/clawd/ (falls back to /home/runner/work/viktor/viktor for CI)
Business hours: Sun-Thu 07:00–19:00 Dubai time (UTC+4, no DST)
"""

import json
import logging
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN = WORKSPACE / "second-brain"
MEMORY_DIR = WORKSPACE / "memory"
DEADLINES_FILE = SECOND_BRAIN / "deadlines.json"
NEEDS_STATE_FILE = SECOND_BRAIN / "needs-state.json"
CALENDAR_EVENTS_FILE = WORKSPACE / "calendar-events.json"

# Optional: JV Diary (if it exists)
JV_DIARY_FILE = WORKSPACE / "JV_Diary.md"

# Dubai timezone offset (UTC+4, no DST)
DUBAI_UTC_OFFSET = timedelta(hours=4)
BUSINESS_DAYS = {6, 0, 1, 2, 3}  # Sun=6, Mon=0, Tue=1, Wed=2, Thu=3
BUSINESS_START = 7   # 07:00
BUSINESS_END   = 19  # 19:00

logger = logging.getLogger(__name__)


def _now_dubai() -> datetime:
    """Return the current datetime in Dubai time."""
    return datetime.now(timezone.utc) + DUBAI_UTC_OFFSET


def get_day_context() -> dict:
    """
    Return basic day-of-week and time context for Dubai timezone.
    """
    try:
        now = _now_dubai()
        weekday = now.weekday()  # Mon=0 … Sun=6
        is_business_day = weekday in BUSINESS_DAYS
        is_business_hours = (
            is_business_day
            and BUSINESS_START <= now.hour < BUSINESS_END
        )

        day_name = now.strftime("%A")
        is_monday = weekday == 0
        is_sunday = weekday == 6
        is_friday = weekday == 4

        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "day_name": day_name,
            "weekday": weekday,
            "is_business_day": is_business_day,
            "is_business_hours": is_business_hours,
            "is_monday": is_monday,
            "is_sunday": is_sunday,
            "is_friday": is_friday,
            "is_weekend": not is_business_day,
        }
    except Exception as e:
        logger.error(f"Error getting day context: {e}")
        return {}


def scan_memory_files(days_back: int = 3) -> list[dict]:
    """
    Scan recent daily memory files for actionable context.

    Args:
        days_back: Number of days back to scan.

    Returns:
        List of {date, path, content, word_count} dicts.
    """
    results = []
    try:
        if not MEMORY_DIR.exists():
            return results

        today = date.today()
        for i in range(days_back):
            target_date = today - timedelta(days=i)
            fname = MEMORY_DIR / f"{target_date.isoformat()}.md"
            if fname.exists():
                try:
                    content = fname.read_text(encoding="utf-8")
                    results.append(
                        {
                            "date": target_date.isoformat(),
                            "path": str(fname),
                            "content": content,
                            "word_count": len(content.split()),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Could not read {fname}: {e}")
    except Exception as e:
        logger.error(f"Error scanning memory files: {e}")
    return results


def scan_open_items() -> list[dict]:
    """
    Scan recent memory files for open action items (lines with TODO, ACTION, ☐, etc.).

    Returns:
        List of {date, item, source} dicts.
    """
    open_items = []
    patterns = [
        r"(?i)^\s*[-*]\s*(TODO|ACTION|FOLLOW[\s-]?UP|PENDING|OPEN ITEM)[:\s]+(.+)$",
        r"(?i)^\s*☐\s*(.+)$",
        r"(?i)^\s*\[\s*\]\s*(.+)$",
    ]
    compiled = [re.compile(p, re.MULTILINE) for p in patterns]

    try:
        memories = scan_memory_files(days_back=7)
        for mem in memories:
            content = mem["content"]
            for pattern in compiled:
                for match in pattern.finditer(content):
                    item_text = (match.group(2) if match.lastindex >= 2 else match.group(1)).strip()
                    if item_text:
                        open_items.append(
                            {
                                "date": mem["date"],
                                "item": item_text,
                                "source": mem["path"],
                            }
                        )
    except Exception as e:
        logger.error(f"Error scanning open items: {e}")
    return open_items


def extract_people_waiting() -> list[dict]:
    """
    Scan memory files for people who are waiting on JV or Viktor.

    Returns:
        List of {person, context, date} dicts.
    """
    waiting = []
    pattern = re.compile(
        r"(?i)(waiting\s+(?:for|on)\s+(?:JV|Jon|a\s+response|reply)|"
        r"JV\s+(?:to\s+)?(?:reply|respond|confirm|approve|review)|"
        r"(?:needs?|need\s+to)\s+(?:follow\s+up\s+with|get\s+back\s+to)\s+([\w\s]+))"
    )
    name_pattern = re.compile(
        r"(?i)(?:waiting\s+for|following\s+up\s+with|pending\s+response\s+from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
    )

    try:
        memories = scan_memory_files(days_back=5)
        for mem in memories:
            for line in mem["content"].splitlines():
                m = name_pattern.search(line)
                if m:
                    waiting.append(
                        {
                            "person": m.group(1).strip(),
                            "context": line.strip()[:200],
                            "date": mem["date"],
                        }
                    )
    except Exception as e:
        logger.error(f"Error extracting people waiting: {e}")
    return waiting


def get_upcoming_deadlines(days_ahead: int = 14) -> list[dict]:
    """
    Load upcoming deadlines from deadlines.json within the specified window.

    Args:
        days_ahead: How many days ahead to look.

    Returns:
        List of deadline dicts sorted by date.
    """
    try:
        if not DEADLINES_FILE.exists():
            return []

        with open(DEADLINES_FILE, "r") as f:
            data = json.load(f)

        deadlines = data.get("deadlines", [])
        today = date.today()
        cutoff = today + timedelta(days=days_ahead)

        upcoming = []
        for dl in deadlines:
            if dl.get("completed"):
                continue
            try:
                dl_date = date.fromisoformat(dl["date"])
                if today <= dl_date <= cutoff:
                    days_left = (dl_date - today).days
                    upcoming.append({**dl, "days_left": days_left})
            except (KeyError, ValueError):
                pass

        upcoming.sort(key=lambda x: x["days_left"])
        return upcoming

    except Exception as e:
        logger.error(f"Error loading deadlines: {e}")
        return []


def scan_journal_recent() -> Optional[str]:
    """
    Read the most recent entry from JV's diary/journal if it exists.

    Returns:
        The most recent journal entry text, or None.
    """
    try:
        if not JV_DIARY_FILE.exists():
            return None

        content = JV_DIARY_FILE.read_text(encoding="utf-8")
        # Return the last ~500 characters as the "recent" entry
        return content[-500:].strip() if content else None

    except Exception as e:
        logger.error(f"Error reading JV diary: {e}")
        return None


def scan_calendar_context() -> dict:
    """
    Load today's calendar events and detect meeting patterns.

    Returns:
        Dict with today's events and flags for heavy meeting days.
    """
    try:
        if not CALENDAR_EVENTS_FILE.exists():
            return {"events": [], "has_calendar": False}

        with open(CALENDAR_EVENTS_FILE, "r") as f:
            cal_data = json.load(f)

        today_str = date.today().isoformat()
        events = []

        # Support both flat list and dict-by-date format
        if isinstance(cal_data, list):
            events = [e for e in cal_data if e.get("date", "") == today_str]
        elif isinstance(cal_data, dict):
            events = cal_data.get(today_str, [])

        return {
            "events": events,
            "count": len(events),
            "has_calendar": True,
            "is_heavy_day": len(events) >= 5,
        }

    except Exception as e:
        logger.error(f"Error scanning calendar: {e}")
        return {"events": [], "has_calendar": False}


def scan_needs_state() -> dict:
    """
    Load Viktor's current needs state from needs-state.json.

    Returns:
        Needs state dict, or empty dict if file not found.
    """
    try:
        if not NEEDS_STATE_FILE.exists():
            return {}

        with open(NEEDS_STATE_FILE, "r") as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"Error reading needs state: {e}")
        return {}


def get_comprehensive_context() -> dict:
    """
    Gather a full workspace context snapshot for use by the cognitive loop.

    Returns:
        Dict containing all context signals.
    """
    try:
        day = get_day_context()
        deadlines = get_upcoming_deadlines(days_ahead=14)
        open_items = scan_open_items()
        people_waiting = extract_people_waiting()
        calendar = scan_calendar_context()
        needs = scan_needs_state()
        journal = scan_journal_recent()

        # Urgency signals
        urgent_deadlines = [d for d in deadlines if d.get("days_left", 99) <= 2]
        overdue_deadlines = [d for d in deadlines if d.get("days_left", 1) < 0]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "day_context": day,
            "deadlines": deadlines,
            "urgent_deadlines": urgent_deadlines,
            "overdue_deadlines": overdue_deadlines,
            "open_items": open_items[:20],
            "people_waiting": people_waiting[:10],
            "calendar": calendar,
            "needs_state": needs,
            "journal_recent": journal,
            "summary": {
                "total_deadlines": len(deadlines),
                "urgent_count": len(urgent_deadlines),
                "overdue_count": len(overdue_deadlines),
                "open_items_count": len(open_items),
                "people_waiting_count": len(people_waiting),
            },
        }

    except Exception as e:
        logger.error(f"Error building comprehensive context: {e}")
        return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ctx = get_comprehensive_context()
    print(json.dumps(ctx, indent=2, default=str))
