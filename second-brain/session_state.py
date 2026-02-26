#!/usr/bin/env python3
"""
Session State Manager for Viktor

Provides continuous structured state persistence to survive context compaction.
Snapshots the current session state and restores it on recovery.

State file:  second-brain/session-state.json
Archive dir: second-brain/session-state-archive/
Memory file: MEMORY.md
"""

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN    = WORKSPACE / "second-brain"
STATE_FILE      = SECOND_BRAIN / "session-state.json"
ARCHIVE_DIR     = SECOND_BRAIN / "session-state-archive"
MEMORY_FILE     = WORKSPACE / "MEMORY.md"

logger = logging.getLogger(__name__)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _default_state() -> dict:
    """Return a fresh empty session state."""
    return {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": None,
        "session_id": None,
        "active_tasks": [],
        "pending_items": [],
        "recent_decisions": [],
        "context_notes": [],
        "jv_requests": [],
        "snapshot_count": 0,
    }


# ── Public API ───────────────────────────────────────────────────────────────

def load_state() -> dict:
    """
    Load the current session state from disk.

    Returns:
        Session state dict, or fresh default if file not found or corrupt.
    """
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session state: {e}")
    return _default_state()


def save_state(state: dict) -> bool:
    """
    Atomically save session state to disk.

    Args:
        state: Session state dict.

    Returns:
        True on success, False on failure.
    """
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp = STATE_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, STATE_FILE)
        return True
    except Exception as e:
        logger.error(f"Error saving session state: {e}")
        return False


def snapshot(
    active_tasks: Optional[list] = None,
    pending_items: Optional[list] = None,
    recent_decisions: Optional[list] = None,
    context_notes: Optional[list] = None,
    jv_requests: Optional[list] = None,
) -> bool:
    """
    Take a snapshot of the current session state.

    All arguments are optional — only provided fields are updated.

    Args:
        active_tasks:     List of in-progress task strings.
        pending_items:    List of items waiting on response/action.
        recent_decisions: List of key decisions made this session.
        context_notes:    Additional context notes.
        jv_requests:      JV's explicit requests from this session.

    Returns:
        True on success, False on failure.
    """
    try:
        state = load_state()

        if active_tasks is not None:
            state["active_tasks"] = active_tasks
        if pending_items is not None:
            state["pending_items"] = pending_items
        if recent_decisions is not None:
            state["recent_decisions"] = recent_decisions
        if context_notes is not None:
            state["context_notes"] = context_notes
        if jv_requests is not None:
            state["jv_requests"] = jv_requests

        state["snapshot_count"] = state.get("snapshot_count", 0) + 1
        return save_state(state)

    except Exception as e:
        logger.error(f"Error taking snapshot: {e}")
        return False


def get_recovery_summary() -> str:
    """
    Generate a human-readable recovery summary from the last saved state.

    Returns:
        Formatted string suitable for injecting at session start.
    """
    try:
        state = load_state()

        if not state.get("last_updated"):
            return "No previous session state found."

        lines = [
            "## Session State Recovery",
            f"*Last snapshot: {state.get('last_updated', 'unknown')}*",
            "",
        ]

        active = state.get("active_tasks", [])
        if active:
            lines.append("### Active Tasks")
            for t in active:
                lines.append(f"- {t}")
            lines.append("")

        pending = state.get("pending_items", [])
        if pending:
            lines.append("### Pending Items")
            for p in pending:
                lines.append(f"- {p}")
            lines.append("")

        decisions = state.get("recent_decisions", [])
        if decisions:
            lines.append("### Recent Decisions")
            for d in decisions:
                lines.append(f"- {d}")
            lines.append("")

        jv_reqs = state.get("jv_requests", [])
        if jv_reqs:
            lines.append("### JV's Requests This Session")
            for r in jv_reqs:
                lines.append(f"- {r}")
            lines.append("")

        notes = state.get("context_notes", [])
        if notes:
            lines.append("### Context Notes")
            for n in notes:
                lines.append(f"- {n}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating recovery summary: {e}")
        return f"Session state recovery failed: {e}"


def archive_and_reset() -> bool:
    """
    Archive the current session state and reset to a fresh state.

    Archives the current state file to second-brain/session-state-archive/
    with a timestamp suffix, then creates a fresh state.

    Returns:
        True on success, False on failure.
    """
    try:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        if STATE_FILE.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = ARCHIVE_DIR / f"session-state-{timestamp}.json"
            shutil.copy2(STATE_FILE, archive_path)
            logger.info(f"Session state archived to {archive_path.name}")

        # Also append recovery summary to MEMORY.md if it exists
        if MEMORY_FILE.exists():
            try:
                summary = get_recovery_summary()
                with open(MEMORY_FILE, "a") as f:
                    f.write(f"\n\n---\n{summary}\n")
                logger.info("Recovery summary appended to MEMORY.md")
            except Exception as e:
                logger.warning(f"Could not update MEMORY.md: {e}")

        # Save fresh state
        fresh = _default_state()
        return save_state(fresh)

    except Exception as e:
        logger.error(f"Error archiving and resetting session state: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(get_recovery_summary())
