#!/usr/bin/env python3
"""
Viktor's Proactive Thought Loop

Monitors Viktor's internal needs, decays stale needs over time,
checks thresholds for proactive action, and updates the heartbeat.

Needs state:     second-brain/needs-state.json
Proactive state: second-brain/proactive-state.json
Heartbeat:       HEARTBEAT.md
Log:             second-brain/thought-loop.log
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN      = WORKSPACE / "second-brain"
NEEDS_STATE_FILE  = SECOND_BRAIN / "needs-state.json"
PROACTIVE_FILE    = SECOND_BRAIN / "proactive-state.json"
HEARTBEAT_FILE    = WORKSPACE / "HEARTBEAT.md"
LOG_FILE          = SECOND_BRAIN / "thought-loop.log"

# Decay rate: needs decay by this fraction per hour
DECAY_RATE = 0.05

# Default need thresholds (0–100 scale; above threshold = action needed)
DEFAULT_THRESHOLDS = {
    "morning_brief":     80,
    "deadline_check":    70,
    "memory_recall":     60,
    "follow_up":         75,
    "habit_scan":        65,
    "horizon_scan":      90,
}

# Default initial need values (on first run)
DEFAULT_NEEDS = {
    "morning_brief":     0,
    "deadline_check":    50,
    "memory_recall":     40,
    "follow_up":         30,
    "habit_scan":        35,
    "horizon_scan":      20,
}

logger = logging.getLogger(__name__)


def _setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


def _load_needs() -> dict:
    """Load needs state from disk."""
    if NEEDS_STATE_FILE.exists():
        try:
            with open(NEEDS_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading needs state: {e}")
    return {
        "version": "1.0",
        "last_updated": None,
        "needs": dict(DEFAULT_NEEDS),
        "thresholds": dict(DEFAULT_THRESHOLDS),
    }


def _save_needs(data: dict) -> bool:
    """Atomically save needs state to disk."""
    try:
        NEEDS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp = NEEDS_STATE_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, NEEDS_STATE_FILE)
        return True
    except Exception as e:
        logger.error(f"Error saving needs state: {e}")
        return False


def _load_proactive_state() -> dict:
    """Load the proactive run-state (date + run count)."""
    if PROACTIVE_FILE.exists():
        try:
            with open(PROACTIVE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"date": "", "runs_today": 0}


def _save_proactive_state(data: dict) -> None:
    try:
        PROACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = PROACTIVE_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, PROACTIVE_FILE)
    except Exception as e:
        logger.error(f"Error saving proactive state: {e}")


# ── Core functions ────────────────────────────────────────────────────────────

def decay_needs(hours_elapsed: float = 1.0) -> dict:
    """
    Decay all needs by DECAY_RATE per hour elapsed.

    Args:
        hours_elapsed: Hours since last decay run.

    Returns:
        Updated needs dict.
    """
    data = _load_needs()
    needs = data.get("needs", {})

    for need in needs:
        current = needs[need]
        decay = current * DECAY_RATE * hours_elapsed
        needs[need] = max(0.0, round(current - decay, 2))

    data["needs"] = needs
    _save_needs(data)
    return needs


def check_thresholds() -> list[str]:
    """
    Check which needs have exceeded their thresholds.

    Returns:
        List of need names that need attention.
    """
    data = _load_needs()
    needs = data.get("needs", {})
    thresholds = data.get("thresholds", DEFAULT_THRESHOLDS)

    triggered = [
        need
        for need, value in needs.items()
        if value >= thresholds.get(need, 80)
    ]
    return triggered


def update_heartbeat(status: str = "OK", notes: str = "") -> bool:
    """
    Update HEARTBEAT.md with the current thought-loop status.

    Args:
        status: Status string (e.g. 'OK', 'ACTIVE', 'IDLE').
        notes:  Additional notes to append.

    Returns:
        True on success.
    """
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = f"# Viktor Heartbeat\n\n**Status:** {status}  \n**Last Update:** {now}\n"
        if notes:
            content += f"\n**Notes:** {notes}\n"
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Error updating heartbeat: {e}")
        return False


def update_manifest(triggered_needs: list[str]) -> None:
    """
    Log triggered needs and attempt to service them.

    Args:
        triggered_needs: List of need names that exceeded thresholds.
    """
    if not triggered_needs:
        return

    data = _load_needs()
    needs = data.get("needs", {})

    for need in triggered_needs:
        logger.info(f"Need triggered: {need} (value: {needs.get(need, 0):.1f})")

        # Service the need by running the relevant module
        if need == "morning_brief":
            try:
                sys.path.insert(0, str(SECOND_BRAIN))
                from morning_brief import generate_morning_brief, save_morning_brief
                brief = generate_morning_brief()
                save_morning_brief(brief)
                needs[need] = 0  # Reset need after servicing
                logger.info(f"  ✓ morning_brief generated")
            except Exception as e:
                logger.warning(f"  ✗ morning_brief failed: {e}")

        elif need == "deadline_check":
            try:
                from context_scanner import get_upcoming_deadlines
                dls = get_upcoming_deadlines(days_ahead=7)
                needs[need] = 0
                logger.info(f"  ✓ deadline_check: {len(dls)} deadlines scanned")
            except Exception as e:
                logger.warning(f"  ✗ deadline_check failed: {e}")

        elif need == "habit_scan":
            try:
                from anticipation_engine import get_todays_habits
                habits = get_todays_habits()
                needs[need] = 0
                logger.info(f"  ✓ habit_scan: {len(habits)} habits retrieved")
            except Exception as e:
                logger.warning(f"  ✗ habit_scan failed: {e}")

        else:
            # Generic reset for unhandled needs
            needs[need] = max(0, needs[need] - 20)

    data["needs"] = needs
    _save_needs(data)


def run_thought_loop() -> dict:
    """
    Execute one thought-loop iteration.

    Returns:
        Summary dict.
    """
    logger_inst = _setup_logging()

    # Track runs today
    pro_state = _load_proactive_state()
    today_str = date.today().isoformat()
    if pro_state.get("date") != today_str:
        pro_state = {"date": today_str, "runs_today": 0}
    pro_state["runs_today"] += 1
    _save_proactive_state(pro_state)

    logger_inst.info(
        f"Thought loop run #{pro_state['runs_today']} for {today_str}"
    )

    # Decay needs (assume ~30 min since last run = 0.5 hours)
    needs = decay_needs(hours_elapsed=0.5)

    # Boost time-sensitive needs based on current hour
    now_hour = (datetime.now(timezone.utc) + timedelta(hours=4)).hour  # Dubai time
    data = _load_needs()
    if 7 <= now_hour < 9:
        data["needs"]["morning_brief"] = max(data["needs"].get("morning_brief", 0), 85)
    if 9 <= now_hour < 18:
        data["needs"]["deadline_check"] = max(data["needs"].get("deadline_check", 0), 75)
    _save_needs(data)

    # Check thresholds
    triggered = check_thresholds()

    # Update manifest (service triggered needs)
    update_manifest(triggered)

    # Update heartbeat
    status = "ACTIVE" if triggered else "IDLE"
    notes = f"Triggered: {', '.join(triggered)}" if triggered else ""
    update_heartbeat(status=status, notes=notes)

    return {
        "runs_today": pro_state["runs_today"],
        "triggered_needs": triggered,
        "status": status,
    }


if __name__ == "__main__":
    result = run_thought_loop()
    print(json.dumps(result, indent=2))
