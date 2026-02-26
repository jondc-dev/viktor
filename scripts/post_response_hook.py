#!/usr/bin/env python3
"""
Post-response hook for Viktor.

Parses every assistant response for:
- Commitments  : "I will", "I'll", "will do", "by tomorrow", "by end of day"
- Decisions    : "decided", "agreed", "we'll go with", "the plan is"
- Rules from JV: "never", "always", "from now on", "rule:"
- Emails sent  : "sent email", "emailed", "forwarded"

Auto-snapshots detected items to second-brain/session-state.json and logs
all activity to second-brain/auto-snapshot.log.

Usage:
    post_response_hook.py "<assistant_response_text>"

Exit code is always 0 (graceful degradation).
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path("~/clawd").expanduser()
SECOND_BRAIN_DIR = WORKSPACE_ROOT / "second-brain"
SESSION_STATE_FILE = SECOND_BRAIN_DIR / "session-state.json"
AUTO_SNAPSHOT_LOG = SECOND_BRAIN_DIR / "auto-snapshot.log"

# Pattern groups: (category, compiled_regex)
PATTERNS = [
    ("commitment", re.compile(
        r"\b(i will|i'll|will do|by tomorrow|by end of day)\b",
        re.IGNORECASE,
    )),
    ("decision", re.compile(
        r"\b(decided|agreed|we'll go with|the plan is)\b",
        re.IGNORECASE,
    )),
    ("rule", re.compile(
        r"\b(never|always|from now on|rule:)\b",
        re.IGNORECASE,
    )),
    ("email_sent", re.compile(
        r"\b(sent email|emailed|forwarded)\b",
        re.IGNORECASE,
    )),
]


def _log(message: str) -> None:
    """Append a timestamped line to the auto-snapshot log."""
    try:
        SECOND_BRAIN_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(AUTO_SNAPSHOT_LOG, "a") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass  # Never crash on logging failure


def _load_session_state() -> dict:
    """Load session-state.json, returning an empty dict on any error."""
    try:
        if SESSION_STATE_FILE.exists():
            with open(SESSION_STATE_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def _save_session_state(state: dict) -> None:
    """Persist session-state.json, logging any error."""
    try:
        SECOND_BRAIN_DIR.mkdir(parents=True, exist_ok=True)
        with open(SESSION_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as exc:
        _log(f"ERROR saving session state: {exc}")


def _extract_sentence(text: str, match_start: int, match_end: int) -> str:
    """Return the sentence that contains the match position."""
    # Walk backwards to find sentence start
    start = match_start
    while start > 0 and text[start - 1] not in ".!?\n":
        start -= 1
    # Walk forward to find sentence end
    end = match_end
    while end < len(text) and text[end] not in ".!?\n":
        end += 1
    return text[start:end].strip()


def detect_items(response_text: str) -> list[dict]:
    """
    Scan *response_text* for commitments, decisions, rules, and emails sent.
    Returns a list of dicts: {category, text, matched_phrase, detected_at}.
    """
    items: list[dict] = []
    seen_sentences: set[str] = set()
    ts = datetime.now().isoformat()

    for category, pattern in PATTERNS:
        for match in pattern.finditer(response_text):
            sentence = _extract_sentence(response_text, match.start(), match.end())
            if sentence and sentence not in seen_sentences:
                seen_sentences.add(sentence)
                items.append({
                    "category": category,
                    "text": sentence,
                    "matched_phrase": match.group(0),
                    "detected_at": ts,
                })

    return items


def snapshot_items(items: list[dict]) -> int:
    """
    Append *items* to session-state.json and log each one.
    Returns the number of items successfully saved.
    """
    if not items:
        return 0

    try:
        state = _load_session_state()
        snapshots: list = state.get("snapshots", [])
        for item in items:
            snapshots.append(item)
            _log(
                f"AUTO-SNAPSHOT [{item['category'].upper()}] "
                f"matched='{item['matched_phrase']}' | {item['text'][:120]}"
            )
        state["snapshots"] = snapshots
        state["last_updated"] = datetime.now().isoformat()
        _save_session_state(state)
        return len(items)
    except Exception as exc:
        _log(f"ERROR during snapshot: {exc}")
        return 0


def process_response(response_text: str) -> int:
    """
    Full pipeline: detect → snapshot.
    Returns number of items snapshotted.
    """
    if not response_text or not response_text.strip():
        return 0
    items = detect_items(response_text)
    if not items:
        return 0
    return snapshot_items(items)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {Path(__file__).name} \"<assistant_response>\"")
        sys.exit(0)

    response_text = sys.argv[1]
    count = process_response(response_text)
    if count:
        print(f"[post_response_hook] {count} item(s) snapshotted.")
    sys.exit(0)


if __name__ == "__main__":
    main()
