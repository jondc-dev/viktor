#!/usr/bin/env python3
"""
Pre-response memory recall hook for Viktor — called by the gateway before every LLM response.

Responsibilities:
1. Run FAISS-based recall via pre_response_recall.py.
2. Check for ~/clawd/CONTEXT_RECOVERY.md on EVERY call (not just session start).
   If found, inject its contents as high-priority context and delete the file.
   This closes the mid-session amnesia gap (GAP 4).
3. On the first hook call of each day, check whether today's morning brief
   exists in ~/clawd/morning-briefs/ and hasn't been presented yet.
   If so, inject it as priority context alongside recall results (GAP 6).

Python importable interface (gateway integration):

    import sys, os
    sys.path.insert(0, os.path.expanduser("~/clawd/scripts"))
    from memory_recall_hook import process_text_message

    def handle_message(user_message, session_id=None):
        memory_context = process_text_message(user_message, session_id=session_id)
        if memory_context:
            system_prompt = memory_context + "\\n\\n" + base_system_prompt
        else:
            system_prompt = base_system_prompt
        # ... proceed with LLM call
"""

import sys
from datetime import date
from pathlib import Path

# Resolve workspace root relative to this file: scripts/ -> parent -> workspace root
_WORKSPACE_ROOT = Path(__file__).parent.parent
_VECTOR_MEMORY_DIR = _WORKSPACE_ROOT / "vector-memory"
_SECOND_BRAIN_DIR = _WORKSPACE_ROOT / "second-brain"
_MORNING_BRIEFS_DIR = _WORKSPACE_ROOT / "morning-briefs"
_CONTEXT_RECOVERY_FILE = _WORKSPACE_ROOT / "CONTEXT_RECOVERY.md"
_BRIEF_PRESENTED_FILE = _SECOND_BRAIN_DIR / ".brief-presented-date"


def _consume_context_recovery() -> str:
    """
    If CONTEXT_RECOVERY.md exists, read it, delete it, and return its contents
    wrapped in a priority header.  Returns empty string when file is absent.
    """
    if not _CONTEXT_RECOVERY_FILE.exists():
        return ""
    try:
        content = _CONTEXT_RECOVERY_FILE.read_text(encoding="utf-8").strip()
        _CONTEXT_RECOVERY_FILE.unlink(missing_ok=True)
        if content:
            return (
                "[CONTEXT RECOVERY — Read this first. Your context was recently "
                "compacted. Restore your understanding before responding.]\n\n"
                + content
                + "\n[END CONTEXT RECOVERY]"
            )
    except Exception:
        pass
    return ""


def _get_morning_brief_context() -> str:
    """
    On the first hook call of each day, inject today's morning brief if it
    exists and has not been presented yet.  Tracks presentation via
    second-brain/.brief-presented-date.
    """
    today = date.today().isoformat()  # "YYYY-MM-DD"

    # Check if already presented today
    try:
        if _BRIEF_PRESENTED_FILE.exists():
            presented = _BRIEF_PRESENTED_FILE.read_text().strip()
            if presented == today:
                return ""
    except Exception:
        pass

    # Look for today's brief
    brief_file = _MORNING_BRIEFS_DIR / f"brief-{today}.html"
    if not brief_file.exists():
        return ""

    try:
        content = brief_file.read_text(encoding="utf-8").strip()
        if not content:
            return ""

        # Mark as presented
        try:
            _SECOND_BRAIN_DIR.mkdir(parents=True, exist_ok=True)
            _BRIEF_PRESENTED_FILE.write_text(today)
        except Exception:
            pass

        return (
            f"[MORNING BRIEF — {today}. Read and acknowledge this at the start "
            "of today's session.]\n\n"
            + content
            + "\n[END MORNING BRIEF]"
        )
    except Exception:
        return ""


def process_text_message(message: str, session_id: str = None, agent_id: str = "viktor") -> str:
    """
    Run pre-response memory recall for the given user message.

    Args:
        message:    The incoming user message text.
        session_id: Unused for Viktor (kept for interface compatibility).
        agent_id:   Unused; present for interface compatibility.

    Returns:
        A formatted context string to prepend to the system prompt.
        Always includes the [RECALL STATUS: ...] header from pre_response_recall.
        May include CONTEXT_RECOVERY and/or MORNING_BRIEF sections.
        Returns empty string only when all sections are empty/failed.
    """
    sections: list[str] = []

    # Priority 1: compaction recovery (inject and delete immediately)
    recovery = _consume_context_recovery()
    if recovery:
        sections.append(recovery)

    # Priority 2: morning brief (first call of the day only)
    brief = _get_morning_brief_context()
    if brief:
        sections.append(brief)

    # Priority 3: FAISS recall
    try:
        vm_dir = str(_VECTOR_MEMORY_DIR)
        if vm_dir not in sys.path:
            sys.path.insert(0, vm_dir)

        from pre_response_recall import recall_for_message  # noqa: PLC0415

        recall_result = recall_for_message(message)
        if recall_result:
            sections.append(recall_result)
    except Exception:
        pass

    return "\n\n".join(sections)


if __name__ == "__main__":
    _msg = sys.argv[1] if len(sys.argv) > 1 else ""
    _result = process_text_message(_msg)
    if _result:
        print(_result)
    sys.exit(0)

