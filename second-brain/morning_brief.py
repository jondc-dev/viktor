#!/usr/bin/env python3
"""
Morning Brief Generator for Viktor

Generates structured daily briefings for JV:
- Morning brief: deadlines, open items, predicted questions, recommendations
- Evening brief: EOD summary and next-day prep

Briefings dir: second-brain/briefings/
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN = WORKSPACE / "second-brain"
BRIEFINGS_DIR = SECOND_BRAIN / "briefings"
sys.path.insert(0, str(SECOND_BRAIN))

try:
    from context_scanner import get_comprehensive_context
except ImportError:
    get_comprehensive_context = None

try:
    from jv_model import get_jv_state_summary
except ImportError:
    get_jv_state_summary = None

try:
    from anticipation_engine import get_predicted_questions, get_todays_habits
except ImportError:
    get_predicted_questions = None
    get_todays_habits = None

logger = logging.getLogger(__name__)

# Deadline urgency thresholds (days)
CRITICAL_DAYS = 2
HIGH_DAYS     = 7
NORMAL_DAYS   = 14


# ── Formatting helpers ────────────────────────────────────────────────────────

def categorize_deadlines(deadlines: list[dict]) -> dict:
    """
    Bucket deadlines into critical / high / normal categories.

    Returns:
        Dict with 'critical', 'high', 'normal' lists.
    """
    categories: dict = {"critical": [], "high": [], "normal": []}
    for dl in deadlines:
        days_left = dl.get("days_left", 99)
        if days_left < 0:
            categories["critical"].append({**dl, "_overdue": True})
        elif days_left <= CRITICAL_DAYS:
            categories["critical"].append(dl)
        elif days_left <= HIGH_DAYS:
            categories["high"].append(dl)
        elif days_left <= NORMAL_DAYS:
            categories["normal"].append(dl)
    return categories


def format_deadline(dl: dict) -> str:
    """Format a single deadline entry as a brief string."""
    title = dl.get("title", "Unknown")
    days_left = dl.get("days_left", 0)
    due_date = dl.get("date", "")

    if dl.get("_overdue"):
        return f"⚠️  OVERDUE: {title} (was {abs(days_left)} days ago)"
    elif days_left == 0:
        return f"🚨 TODAY: {title}"
    elif days_left == 1:
        return f"🔴 TOMORROW: {title}"
    elif days_left <= CRITICAL_DAYS:
        return f"🔴 {title} — {days_left} days left"
    elif days_left <= HIGH_DAYS:
        return f"🟡 {title} — {days_left} days left ({due_date})"
    else:
        return f"⚪ {title} — {days_left} days ({due_date})"


def generate_recommendations(context: dict, jv_state: dict) -> list[str]:
    """
    Generate actionable recommendations based on context and JV's state.

    Args:
        context:  Comprehensive context from context_scanner.
        jv_state: JV state summary from jv_model.

    Returns:
        List of recommendation strings.
    """
    recs = []

    # Overdue items
    overdue = context.get("overdue_deadlines", [])
    if overdue:
        for dl in overdue[:2]:
            recs.append(
                f"Address overdue item immediately: {dl.get('title', 'Unknown')}"
            )

    # Critical upcoming deadlines
    cats = categorize_deadlines(context.get("deadlines", []))
    for dl in cats["critical"][:2]:
        if not dl.get("_overdue"):
            recs.append(
                f"Prioritise today: {dl.get('title', 'Unknown')} "
                f"(due in {dl.get('days_left')} days)"
            )

    # Low dimensions
    under_stress = jv_state.get("under_stress", [])
    for dim in under_stress[:1]:
        dim_name = dim["dimension"].replace("_", " ").title()
        recs.append(
            f"⚠️ {dim_name} is {dim['status']} — consider lighter workload today."
        )

    # People waiting
    people = context.get("people_waiting", [])
    if people:
        names = [p.get("person", "someone") for p in people[:2]]
        recs.append(f"Follow up with: {', '.join(names)}")

    # Heavy calendar
    if context.get("calendar", {}).get("is_heavy_day"):
        recs.append(
            "Heavy meeting day — block 30 min to process action items before EOD."
        )

    return recs[:6]


def generate_morning_brief(context: Optional[dict] = None) -> str:
    """
    Generate Viktor's Morning Brief for JV.

    Args:
        context: Pre-loaded context (or None to auto-load).

    Returns:
        Formatted morning brief string.
    """
    try:
        if context is None and get_comprehensive_context:
            context = get_comprehensive_context()
        if context is None:
            context = {}

        jv_state = {}
        if get_jv_state_summary:
            try:
                jv_state = get_jv_state_summary()
            except Exception:
                pass

        now = datetime.now(timezone.utc)
        today = date.today()
        day_name = today.strftime("%A, %B %d").replace(" 0", " ")

        lines = [
            f"# Viktor's Morning Brief",
            f"**{day_name}**  ·  Generated {now.strftime('%H:%M')} UTC",
            "",
        ]

        # ── JV State ─────────────────────────────────────────────────────
        if jv_state:
            overall = jv_state.get("overall_health", 70)
            status = jv_state.get("overall_status", "stable")
            lines += [
                f"## JV State: {status.upper()} ({overall:.0f}/100)",
            ]
            under_stress = jv_state.get("under_stress", [])
            if under_stress:
                for d in under_stress:
                    lines.append(
                        f"- {d['dimension'].replace('_',' ').title()}: "
                        f"{d['status']} ({d['value']:.0f})"
                    )
            lines.append("")

        # ── Deadlines ─────────────────────────────────────────────────────
        deadlines = context.get("deadlines", [])
        if deadlines:
            lines.append("## Upcoming Deadlines")
            cats = categorize_deadlines(deadlines)
            for dl in cats["critical"] + cats["high"] + cats["normal"]:
                lines.append(f"- {format_deadline(dl)}")
            lines.append("")
        else:
            lines += ["## Upcoming Deadlines", "_No deadlines in the next 14 days._", ""]

        # ── Open Items ────────────────────────────────────────────────────
        open_items = context.get("open_items", [])
        if open_items:
            lines.append("## Open Items")
            for item in open_items[:5]:
                lines.append(f"- {item.get('item', '')[:120]}")
            lines.append("")

        # ── Calendar ──────────────────────────────────────────────────────
        calendar = context.get("calendar", {})
        events = calendar.get("events", [])
        if events:
            lines.append("## Today's Calendar")
            for ev in events[:8]:
                time_str = ev.get("time", "")
                title = ev.get("title", ev.get("summary", "Meeting"))
                lines.append(f"- {time_str}  {title}" if time_str else f"- {title}")
            lines.append("")

        # ── Recommendations ───────────────────────────────────────────────
        recs = generate_recommendations(context, jv_state)
        if recs:
            lines.append("## Recommendations")
            for rec in recs:
                lines.append(f"- {rec}")
            lines.append("")

        # ── What JV Will Probably Ask Today ──────────────────────────────
        predicted = []
        if get_predicted_questions:
            try:
                predicted = get_predicted_questions(context)
            except Exception:
                pass
        if predicted:
            lines.append("## What JV Will Probably Ask Today")
            for q in predicted[:5]:
                lines.append(f"- {q}")
            lines.append("")

        # ── Habit Check ───────────────────────────────────────────────────
        habits = []
        if get_todays_habits:
            try:
                habits = get_todays_habits()
            except Exception:
                pass
        if habits:
            lines.append("## JV's Likely Focus Areas Today")
            for h in habits[:3]:
                topic = h["topic"].replace("_", " ").title()
                conf = h.get("confidence", 0)
                lines.append(f"- {topic} (confidence: {conf:.0%})")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating morning brief: {e}")
        return f"# Viktor's Morning Brief\n\n_Error generating brief: {e}_"


def save_morning_brief(content: str) -> Optional[Path]:
    """
    Save a morning brief to the briefings directory.

    Args:
        content: The brief content string.

    Returns:
        Path to the saved file, or None on failure.
    """
    try:
        BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
        filename = BRIEFINGS_DIR / f"morning-brief-{date.today().isoformat()}.md"
        filename.write_text(content, encoding="utf-8")
        logger.info(f"Morning brief saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving morning brief: {e}")
        return None


def generate_evening_brief(context: Optional[dict] = None) -> str:
    """
    Generate an end-of-day summary brief for JV.

    Args:
        context: Pre-loaded context (or None to auto-load).

    Returns:
        Formatted evening brief string.
    """
    try:
        if context is None and get_comprehensive_context:
            context = get_comprehensive_context()
        if context is None:
            context = {}

        now = datetime.now(timezone.utc)
        today = date.today()
        tomorrow = today + timedelta(days=1)

        lines = [
            "# Viktor's Evening Brief",
            f"**{today.strftime('%A, %B %d').replace(' 0', ' ')}** — End of Day  ·  {now.strftime('%H:%M')} UTC",
            "",
        ]

        # ── Deadlines tomorrow ────────────────────────────────────────────
        deadlines = context.get("deadlines", [])
        tomorrow_deadlines = [
            d for d in deadlines if d.get("days_left") == 1
        ]
        if tomorrow_deadlines:
            lines.append("## Due Tomorrow ⚠️")
            for dl in tomorrow_deadlines:
                lines.append(f"- {dl.get('title', 'Unknown')}")
            lines.append("")

        # ── Outstanding open items ────────────────────────────────────────
        open_items = context.get("open_items", [])
        if open_items:
            lines.append("## Still Open Today")
            for item in open_items[:4]:
                lines.append(f"- {item.get('item', '')[:120]}")
            lines.append("")

        # ── People still waiting ──────────────────────────────────────────
        people = context.get("people_waiting", [])
        if people:
            names = [p.get("person", "?") for p in people[:3]]
            lines += [
                "## Waiting on Response",
                f"- {', '.join(names)} still waiting.",
                "",
            ]

        lines += [
            "## Tomorrow's Prep",
            f"- Review calendar for {tomorrow.strftime('%A')}",
            "- Check any overnight messages from global contacts",
            "- Prioritise top 3 tasks before first meeting",
            "",
        ]

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating evening brief: {e}")
        return f"# Viktor's Evening Brief\n\n_Error: {e}_"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    brief = generate_morning_brief()
    print(brief)
    path = save_morning_brief(brief)
    if path:
        print(f"\nSaved to: {path}")
