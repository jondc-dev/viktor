#!/usr/bin/env python3
"""
Anticipation Engine for Viktor

Detects JV's behavioral habits, infers next steps from context,
and predicts questions JV will likely ask so Viktor can prepare answers.

Habits file:      second-brain/jv-habits.json
Next-steps file:  second-brain/next-steps-queue.json
Deadlines file:   second-brain/deadlines.json
"""

import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN = WORKSPACE / "second-brain"
HABITS_FILE   = SECOND_BRAIN / "jv-habits.json"
NEXT_STEPS_FILE = SECOND_BRAIN / "next-steps-queue.json"
DEADLINES_FILE  = SECOND_BRAIN / "deadlines.json"

# Confidence threshold for habit detection
DEFAULT_CONFIDENCE = 0.6

# General business topic keywords (not company-specific)
TOPIC_KEYWORDS = {
    "financial_review": [
        "budget", "revenue", "p&l", "forecast", "cash flow",
        "quarterly", "annual review", "financials", "expenses",
    ],
    "team_management": [
        "team", "performance", "review", "hiring", "onboarding",
        "feedback", "one-on-one", "1:1", "promotion", "salary",
    ],
    "strategy": [
        "strategy", "roadmap", "priorities", "goals", "okr",
        "kpi", "planning", "vision", "initiative", "pivot",
    ],
    "operations": [
        "operations", "process", "workflow", "bottleneck", "efficiency",
        "system", "vendor", "contract", "sla", "compliance",
    ],
    "client_relationship": [
        "client", "customer", "proposal", "deal", "pitch",
        "negotiation", "agreement", "partnership", "renewal",
    ],
    "risk_compliance": [
        "risk", "compliance", "legal", "audit", "regulation",
        "policy", "governance", "liability", "exposure",
    ],
    "growth": [
        "growth", "expansion", "new market", "opportunity", "acquisition",
        "launch", "scale", "investment", "funding",
    ],
}

logger = logging.getLogger(__name__)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _load_habits() -> dict:
    """Load habits from disk, returning a default structure if missing."""
    if HABITS_FILE.exists():
        try:
            with open(HABITS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading habits: {e}")
    return {
        "version": "1.0",
        "last_updated": None,
        "last_scan_date": None,
        "habits": {},
        "monthly_patterns": {"month_start": [], "month_end": [], "mid_month": []},
        "topic_cycles": [],
        "confidence_threshold": DEFAULT_CONFIDENCE,
    }


def _save_habits(data: dict) -> bool:
    """Atomically save habits to disk."""
    try:
        HABITS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp = HABITS_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, HABITS_FILE)
        return True
    except Exception as e:
        logger.error(f"Error saving habits: {e}")
        return False


def _load_next_steps() -> dict:
    """Load next-steps queue from disk."""
    if NEXT_STEPS_FILE.exists():
        try:
            with open(NEXT_STEPS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading next steps: {e}")
    return {
        "version": "1.0",
        "last_updated": None,
        "pending_steps": [],
        "completed_steps": [],
    }


def _save_next_steps(data: dict) -> bool:
    """Atomically save next-steps queue to disk."""
    try:
        NEXT_STEPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp = NEXT_STEPS_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, NEXT_STEPS_FILE)
        return True
    except Exception as e:
        logger.error(f"Error saving next steps: {e}")
        return False


def _load_deadlines() -> list:
    """Load deadlines list from disk."""
    if DEADLINES_FILE.exists():
        try:
            with open(DEADLINES_FILE, "r") as f:
                data = json.load(f)
            return data.get("deadlines", [])
        except Exception as e:
            logger.error(f"Error loading deadlines: {e}")
    return []


# ── Public API ───────────────────────────────────────────────────────────────

def detect_habits(memory_texts: list[str]) -> dict:
    """
    Analyse memory texts to detect recurring topic patterns and habits.

    Args:
        memory_texts: List of raw memory file content strings.

    Returns:
        Dict of detected habits with confidence scores.
    """
    topic_counts: dict[str, int] = {}

    for text in memory_texts:
        text_lower = text.lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

    total = max(len(memory_texts), 1)
    habits = {}
    for topic, count in topic_counts.items():
        confidence = round(count / total, 3)
        if confidence >= DEFAULT_CONFIDENCE:
            habits[topic] = {
                "confidence": confidence,
                "occurrences": count,
                "last_detected": datetime.now(timezone.utc).isoformat(),
            }

    # Persist detected habits
    try:
        data = _load_habits()
        data["habits"].update(habits)
        data["last_scan_date"] = date.today().isoformat()
        _save_habits(data)
    except Exception as e:
        logger.error(f"Error persisting detected habits: {e}")

    return habits


def get_todays_habits() -> list[dict]:
    """
    Return habits that are likely relevant today based on confidence scores.

    Returns:
        List of habit dicts sorted by confidence descending.
    """
    try:
        data = _load_habits()
        habits = data.get("habits", {})
        threshold = data.get("confidence_threshold", DEFAULT_CONFIDENCE)

        relevant = [
            {"topic": topic, **details}
            for topic, details in habits.items()
            if details.get("confidence", 0) >= threshold
        ]
        relevant.sort(key=lambda x: x["confidence"], reverse=True)
        return relevant

    except Exception as e:
        logger.error(f"Error getting today's habits: {e}")
        return []


def infer_next_steps(open_items: list[dict], deadlines: list[dict]) -> list[dict]:
    """
    Infer likely next steps from open items and upcoming deadlines.

    Args:
        open_items: Open action items from context_scanner.
        deadlines:  Upcoming deadlines from context_scanner.

    Returns:
        List of inferred next-step dicts.
    """
    inferred = []
    now = datetime.now(timezone.utc).isoformat()

    # From open items
    for item in open_items[:10]:
        inferred.append(
            {
                "id": f"ns_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(inferred)}",
                "step": item.get("item", ""),
                "source": "open_item",
                "source_date": item.get("date", ""),
                "inferred_at": now,
                "completed": False,
                "priority": "normal",
            }
        )

    # From deadline deadlines
    for dl in deadlines[:5]:
        if dl.get("days_left", 99) <= 7:
            inferred.append(
                {
                    "id": f"ns_dl_{dl.get('id', len(inferred))}",
                    "step": f"Prepare for deadline: {dl.get('title', 'Unknown')}",
                    "source": "deadline",
                    "deadline_date": dl.get("date", ""),
                    "days_left": dl.get("days_left"),
                    "inferred_at": now,
                    "completed": False,
                    "priority": "high" if dl.get("days_left", 99) <= 3 else "normal",
                }
            )

    # Merge into queue (avoid duplicates by step text)
    if inferred:
        try:
            queue = _load_next_steps()
            existing_steps = {s["step"] for s in queue.get("pending_steps", [])}
            new_steps = [s for s in inferred if s["step"] not in existing_steps]
            queue["pending_steps"].extend(new_steps)
            # Keep last 50 pending steps
            queue["pending_steps"] = queue["pending_steps"][-50:]
            _save_next_steps(queue)
        except Exception as e:
            logger.error(f"Error merging inferred steps: {e}")

    return inferred


def get_pending_next_steps() -> list[dict]:
    """
    Return all pending (incomplete) next steps from the queue.

    Returns:
        List of pending step dicts.
    """
    try:
        queue = _load_next_steps()
        return [s for s in queue.get("pending_steps", []) if not s.get("completed")]
    except Exception as e:
        logger.error(f"Error getting pending next steps: {e}")
        return []


def mark_step_done(step_id: str) -> bool:
    """
    Mark a next step as completed.

    Args:
        step_id: The step's 'id' field.

    Returns:
        True if found and marked done, False otherwise.
    """
    try:
        queue = _load_next_steps()
        for step in queue.get("pending_steps", []):
            if step.get("id") == step_id:
                step["completed"] = True
                step["completed_at"] = datetime.now(timezone.utc).isoformat()
                # Move to completed list
                queue.setdefault("completed_steps", []).append(step)
                queue["pending_steps"] = [
                    s for s in queue["pending_steps"] if s.get("id") != step_id
                ]
                return _save_next_steps(queue)
        logger.warning(f"Step not found: {step_id}")
        return False
    except Exception as e:
        logger.error(f"Error marking step done: {e}")
        return False


def get_predicted_questions(context: dict) -> list[str]:
    """
    Predict questions JV will likely ask today based on context signals.

    Args:
        context: The comprehensive context dict from context_scanner.

    Returns:
        List of predicted question strings.
    """
    questions = []
    try:
        deadlines = context.get("deadlines", [])
        open_items = context.get("open_items", [])
        calendar = context.get("calendar", {})
        day_ctx = context.get("day_context", {})

        # Deadline-driven questions
        for dl in deadlines[:3]:
            if dl.get("days_left", 99) <= 7:
                questions.append(
                    f"What's the status on '{dl.get('title', 'this deadline')}'? "
                    f"({dl.get('days_left')} days left)"
                )

        # Open items questions
        for item in open_items[:2]:
            questions.append(f"Any update on: {item.get('item', '')[:80]}?")

        # Calendar-driven questions
        if calendar.get("is_heavy_day"):
            questions.append(
                "With so many meetings today, what should I prioritise?"
            )
        elif calendar.get("count", 0) == 0:
            questions.append("Any important tasks I should focus on today?")

        # Day-of-week questions
        if day_ctx.get("is_monday"):
            questions.append("What are the top priorities for this week?")
        if day_ctx.get("is_friday"):
            questions.append("What needs to be wrapped up before the weekend?")

        # Habit-driven questions
        habits = get_todays_habits()
        for habit in habits[:2]:
            topic = habit["topic"].replace("_", " ").title()
            questions.append(f"Can you give me a quick {topic} update?")

    except Exception as e:
        logger.error(f"Error predicting questions: {e}")

    return questions[:8]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys

    sys.path.insert(0, str(WORKSPACE / "second-brain"))
    try:
        from context_scanner import get_comprehensive_context

        ctx = get_comprehensive_context()
        questions = get_predicted_questions(ctx)
        print("Predicted questions:")
        for q in questions:
            print(f"  • {q}")
    except ImportError:
        print("context_scanner not available")
        print(json.dumps(get_todays_habits(), indent=2))
