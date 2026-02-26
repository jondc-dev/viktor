#!/usr/bin/env python3
"""
Horizon Scan for Viktor

Generates a 60-90 day strategic outlook for JV.
Identifies upcoming strategic milestones, suggests preparation priorities,
and recommends focus areas for the coming quarter.

Runs on Sundays as part of the cognitive loop.
"""

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN = WORKSPACE / "second-brain"
HORIZON_FILE = SECOND_BRAIN / "briefings" / f"horizon-scan-{date.today().isoformat()}.md"
LAST_SCAN_MARKER = SECOND_BRAIN / "briefings" / ".last-horizon-scan"

HORIZON_DAYS_MIN = 60
HORIZON_DAYS_MAX = 90

logger = logging.getLogger(__name__)


def scan_horizon_deadlines(deadlines: list[dict]) -> dict:
    """
    Identify deadlines falling in the 60-90 day strategic horizon.

    Args:
        deadlines: Full list of deadline dicts (with 'days_left' field).

    Returns:
        Dict with 'imminent' (≤30d), 'horizon' (31–90d), 'beyond' (>90d) lists.
    """
    result: dict = {"imminent": [], "horizon": [], "beyond": []}

    for dl in deadlines:
        days = dl.get("days_left", 999)
        if dl.get("completed"):
            continue
        if days <= 30:
            result["imminent"].append(dl)
        elif days <= HORIZON_DAYS_MAX:
            result["horizon"].append(dl)
        else:
            result["beyond"].append(dl)

    return result


def generate_horizon_scan(context: Optional[dict] = None) -> str:
    """
    Generate a 60-90 day strategic horizon scan for JV.

    Args:
        context: Comprehensive context dict from context_scanner (or None to load).

    Returns:
        Formatted horizon scan string.
    """
    try:
        if context is None:
            try:
                import sys
                sys.path.insert(0, str(SECOND_BRAIN))
                from context_scanner import get_comprehensive_context
                context = get_comprehensive_context()
            except ImportError:
                context = {}

        today = date.today()
        now = datetime.now(timezone.utc)
        horizon_date = today + timedelta(days=HORIZON_DAYS_MAX)

        lines = [
            "# Horizon Scan — Strategic Outlook for JV",
            f"**Week of {today.strftime('%B %d, %Y').replace(' 0', ' ')}**  ·  60–90 Day View",
            f"*Generated {now.strftime('%Y-%m-%d %H:%M')} UTC*",
            "",
            "## Purpose",
            "What strategic priority should shape Viktor's preparation now?",
            "What decisions will JV face in the next 60-90 days?",
            "",
        ]

        deadlines = context.get("deadlines", [])
        bucketed = scan_horizon_deadlines(deadlines)

        # ── Imminent (≤30 days) ───────────────────────────────────────────
        if bucketed["imminent"]:
            lines.append("## Imminent (Next 30 Days)")
            for dl in sorted(bucketed["imminent"], key=lambda x: x.get("days_left", 0)):
                days = dl.get("days_left", "?")
                title = dl.get("title", "Unknown")
                lines.append(f"- **{days}d** — {title}")
            lines.append("")

        # ── Strategic Horizon (31–90 days) ────────────────────────────────
        if bucketed["horizon"]:
            lines.append(f"## Strategic Horizon (31–{HORIZON_DAYS_MAX} Days)")
            for dl in sorted(bucketed["horizon"], key=lambda x: x.get("days_left", 0)):
                days = dl.get("days_left", "?")
                title = dl.get("title", "Unknown")
                due = dl.get("date", "")
                lines.append(f"- **{days}d** ({due}) — {title}")
            lines.append("")
        else:
            lines += [
                f"## Strategic Horizon (31–{HORIZON_DAYS_MAX} Days)",
                "_No deadlines registered in this window._",
                "",
            ]

        # ── Team Development ──────────────────────────────────────────────
        lines += [
            "## Team Development",
            "- Review team performance metrics and development plans.",
            "- Identify any succession or capacity gaps for the quarter ahead.",
            "",
        ]

        # ── Viktor's Preparation Focus ────────────────────────────────────
        lines += [
            "## Viktor's Preparation Focus",
            "Based on the horizon above, Viktor should:",
        ]

        if bucketed["horizon"]:
            for dl in bucketed["horizon"][:3]:
                title = dl.get("title", "initiative")
                days = dl.get("days_left", "?")
                lines.append(
                    f"- Begin gathering context on *{title}* ({days} days away)"
                )
        else:
            lines.append("- No specific horizon deadlines to prep for yet.")

        lines += [
            "- Ensure decision-support materials are ready 2 weeks ahead of each deadline.",
            "- Flag any strategic decisions that require JV's input before execution.",
            "",
        ]

        # ── Calendar Window ───────────────────────────────────────────────
        lines += [
            f"## Calendar Window: {today.strftime('%b %d').replace(' 0', ' ')} → {horizon_date.strftime('%b %d, %Y').replace(' 0', ' ')}",
            "_Load calendar-events.json to populate this section with actual events._",
            "",
        ]

        lines += [
            "---",
            f"*Next horizon scan: next Sunday ({(today + timedelta(days=(6 - today.weekday()) % 7 + 7)).strftime('%B %d').replace(' 0', ' ')})*",
        ]

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating horizon scan: {e}")
        return f"# Horizon Scan\n\n_Error generating scan: {e}_"


def save_horizon_scan(content: str) -> Optional[Path]:
    """
    Save the horizon scan to the briefings directory.

    Args:
        content: The horizon scan content string.

    Returns:
        Path to saved file, or None on failure.
    """
    try:
        out_file = WORKSPACE / "second-brain" / "briefings" / f"horizon-scan-{date.today().isoformat()}.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(content, encoding="utf-8")
        # Update last-scan marker
        LAST_SCAN_MARKER.parent.mkdir(parents=True, exist_ok=True)
        LAST_SCAN_MARKER.write_text(date.today().isoformat())
        logger.info(f"Horizon scan saved to {out_file.name}")
        return out_file
    except Exception as e:
        logger.error(f"Error saving horizon scan: {e}")
        return None


def should_generate_horizon_scan() -> bool:
    """
    Return True if a horizon scan should be generated today (i.e., not yet done).

    Returns:
        True if no scan has been run today.
    """
    try:
        if LAST_SCAN_MARKER.exists():
            last = LAST_SCAN_MARKER.read_text().strip()
            return last != date.today().isoformat()
        return True
    except Exception:
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if should_generate_horizon_scan():
        scan = generate_horizon_scan()
        path = save_horizon_scan(scan)
        print(scan)
        if path:
            print(f"\nSaved to: {path}")
    else:
        print("Horizon scan already generated today.")
