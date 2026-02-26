#!/usr/bin/env python3
"""
Response Advisor for Viktor

Injects butler guidance before Viktor responds to JV, based on JV's
current cognitive state, pending next steps, and predicted questions.

Returns a [BUTLER GUIDANCE] block that Viktor prepends to his context.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN = WORKSPACE / "second-brain"
sys.path.insert(0, str(SECOND_BRAIN))

try:
    from jv_model import get_jv_state_summary
except ImportError:
    get_jv_state_summary = None

try:
    from anticipation_engine import get_predicted_questions, get_pending_next_steps
except ImportError:
    get_predicted_questions = None
    get_pending_next_steps = None

logger = logging.getLogger(__name__)

# ── Adaptive rules ────────────────────────────────────────────────────────────
# Each rule: condition function + guidance text.
# Rules are evaluated in order; all matching rules are included.

ADAPTIVE_RULES = [
    {
        "id": "low_decision_bandwidth",
        "condition": lambda s: (
            s.get("dimensions", {})
            .get("decision_bandwidth", {})
            .get("status") in ("critical", "low")
        ),
        "guidance": (
            "JV's decision bandwidth is low. Keep responses concise — use bullets, "
            "not paragraphs. Offer clear options rather than open questions. "
            "Avoid adding new tasks unless urgent."
        ),
    },
    {
        "id": "low_emotional_reserves",
        "condition": lambda s: (
            s.get("dimensions", {})
            .get("emotional_reserves", {})
            .get("status") in ("critical", "low")
        ),
        "guidance": (
            "JV's emotional reserves appear depleted. Be warm and supportive. "
            "Prioritise solutions over analysis. Don't pile on problems."
        ),
    },
    {
        "id": "low_physical_wellbeing",
        "condition": lambda s: (
            s.get("dimensions", {})
            .get("physical_wellbeing", {})
            .get("status") in ("critical", "low")
        ),
        "guidance": (
            "Signs of physical fatigue detected. Keep responses brief. "
            "If relevant, gently suggest taking a break."
        ),
    },
    {
        "id": "declining_strategic_focus",
        "condition": lambda s: (
            s.get("dimensions", {})
            .get("strategic_focus", {})
            .get("trend") == "declining"
        ),
        "guidance": (
            "JV's strategic focus has been declining. If the conversation involves "
            "multiple competing priorities, help JV anchor to the most important one."
        ),
    },
    {
        "id": "relationship_capital_low",
        "condition": lambda s: (
            s.get("dimensions", {})
            .get("relationship_capital", {})
            .get("status") in ("critical", "low")
        ),
        "guidance": (
            "Relationship capital signals are low. If JV mentions team or partner "
            "friction, encourage constructive framing before action."
        ),
    },
    {
        "id": "high_overall_health",
        "condition": lambda s: s.get("overall_health", 70) >= 85,
        "guidance": (
            "JV is operating at high capacity today. Good time to tackle complex "
            "decisions or strategic conversations."
        ),
    },
]


def _keyword_overlap(user_message: str, items: list[str]) -> list[str]:
    """Return items whose key words appear in user_message."""
    msg_words = set(user_message.lower().split())
    matched = []
    for item in items:
        item_words = set(item.lower().split())
        # At least 2 meaningful words overlap
        overlap = msg_words & item_words - {"the", "a", "an", "is", "on", "to", "for", "of"}
        if len(overlap) >= 2:
            matched.append(item)
    return matched


def advise_on_response(user_message: str) -> str:
    """
    Generate a [BUTLER GUIDANCE] block for Viktor to prepend to his context.

    Args:
        user_message: JV's latest message/request.

    Returns:
        A formatted guidance string, or empty string if no guidance needed.
    """
    guidance_lines = []

    # ── JV state-based rules ──────────────────────────────────────────────
    try:
        if get_jv_state_summary:
            state = get_jv_state_summary()
            for rule in ADAPTIVE_RULES:
                try:
                    if rule["condition"](state):
                        guidance_lines.append(f"• {rule['guidance']}")
                except Exception:
                    pass
        else:
            guidance_lines.append("• JV model unavailable — using default response approach.")
    except Exception as e:
        logger.warning(f"Error evaluating JV state rules: {e}")

    # ── Predicted questions match ─────────────────────────────────────────
    try:
        if get_predicted_questions:
            # Use a minimal context dict for quick prediction
            predicted = get_predicted_questions({"deadlines": [], "open_items": [], "calendar": {}})
            matched_questions = _keyword_overlap(user_message, predicted)
            if matched_questions:
                guidance_lines.append(
                    "• JV may be asking about predicted topics. "
                    "Have answers ready: " + "; ".join(matched_questions[:2])
                )
    except Exception as e:
        logger.debug(f"Predicted questions unavailable: {e}")

    # ── Pending next steps match ──────────────────────────────────────────
    try:
        if get_pending_next_steps:
            pending = get_pending_next_steps()
            step_texts = [s.get("step", "") for s in pending[:10]]
            matched_steps = _keyword_overlap(user_message, step_texts)
            if matched_steps:
                guidance_lines.append(
                    "• Related pending steps: " + "; ".join(matched_steps[:2])
                )
    except Exception as e:
        logger.debug(f"Pending next steps unavailable: {e}")

    if not guidance_lines:
        return ""

    timestamp = datetime.now(timezone.utc).strftime("%H:%M UTC")
    block = [f"[BUTLER GUIDANCE — {timestamp}]"]
    block.extend(guidance_lines)
    block.append("[END BUTLER GUIDANCE]")

    return "\n".join(block)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_msg = "What deadlines are coming up this week?"
    guidance = advise_on_response(test_msg)
    if guidance:
        print(guidance)
    else:
        print("(no guidance generated)")
