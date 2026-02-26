#!/usr/bin/env python3
"""
Message Analyzer for Viktor

Scans recent memory files for behavioral signals that indicate JV's
cognitive and emotional state. Automatically records detected signals
to the JV model.

Behavioral signals detected:
  - short_reply_length     — terse responses suggest cognitive overload
  - late_night_activity    — messages after 22:00 Dubai time
  - topic_repetition       — same topic raised multiple times in short window
  - financial_language     — stress language around money/budget
  - people_frustration     — friction signals in team/relationship context
  - response_latency       — unusually long gaps before replies
"""

import json
import logging
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
MEMORY_DIR   = WORKSPACE / "memory"
sys.path.insert(0, str(SECOND_BRAIN))

try:
    from jv_model import record_signal
    _has_jv_model = True
except ImportError:
    _has_jv_model = False

# Dubai timezone
DUBAI_UTC_OFFSET = timedelta(hours=4)
LATE_NIGHT_START = 22  # 22:00
LATE_NIGHT_END   = 6   # 06:00
SHORT_REPLY_MAX  = 15  # words

# Financial stress keywords
FINANCIAL_KEYWORDS = [
    "budget", "overspend", "cash flow", "burn rate", "shortfall",
    "overrun", "deficit", "underfunded", "tight budget", "cost control",
    "revenue miss", "write-off", "bad debt",
]

# People frustration keywords
FRUSTRATION_KEYWORDS = [
    "frustrated", "disappointed", "unacceptable", "not good enough",
    "letting us down", "dropped the ball", "missed again",
    "need to talk", "serious concern", "this can't continue",
    "fed up", "at a loss", "incompetent",
]

logger = logging.getLogger(__name__)


def _read_recent_memories(days_back: int = 3) -> list[dict]:
    """Read recent daily memory files."""
    memories = []
    today = date.today()
    for i in range(days_back):
        f = MEMORY_DIR / f"{(today - timedelta(days=i)).isoformat()}.md"
        if f.exists():
            try:
                memories.append(
                    {
                        "date": (today - timedelta(days=i)).isoformat(),
                        "content": f.read_text(encoding="utf-8"),
                        "path": str(f),
                    }
                )
            except Exception as e:
                logger.warning(f"Could not read {f}: {e}")
    return memories


def detect_short_replies(memories: list[dict]) -> list[dict]:
    """
    Detect patterns of short (≤15 word) JV replies in memory files.

    Returns:
        List of {date, line, word_count} matches.
    """
    matches = []
    # Look for patterns like "JV:" or "Jon:" followed by a short line
    jv_reply_pattern = re.compile(
        r"(?:JV|Jon)[:\s]+([^\n]{1,200})", re.IGNORECASE
    )
    for mem in memories:
        for m in jv_reply_pattern.finditer(mem["content"]):
            reply = m.group(1).strip()
            word_count = len(reply.split())
            if 1 <= word_count <= SHORT_REPLY_MAX:
                matches.append(
                    {"date": mem["date"], "line": reply, "word_count": word_count}
                )
    return matches


def detect_late_night_activity(memories: list[dict]) -> list[dict]:
    """
    Detect timestamps in memory files that fall in late-night hours (22:00–06:00 Dubai).

    Returns:
        List of {date, time_str, context} matches.
    """
    matches = []
    time_pattern = re.compile(r"\b(\d{1,2}:\d{2})\b")

    for mem in memories:
        for line in mem["content"].splitlines():
            for m in time_pattern.finditer(line):
                time_str = m.group(1)
                try:
                    hour = int(time_str.split(":")[0])
                    if hour >= LATE_NIGHT_START or hour < LATE_NIGHT_END:
                        matches.append(
                            {
                                "date": mem["date"],
                                "time": time_str,
                                "context": line.strip()[:150],
                            }
                        )
                except ValueError:
                    pass
    return matches


def detect_topic_repetition(memories: list[dict]) -> list[dict]:
    """
    Detect the same topic appearing multiple times across recent memories.

    Returns:
        List of {topic, count, dates} for topics seen ≥3 times.
    """
    topic_dates: dict = {}
    keywords = {
        "budget": "financial_review",
        "strategy": "strategy",
        "team": "team_management",
        "client": "client_relationship",
        "deadline": "operations",
        "compliance": "risk_compliance",
        "growth": "growth",
    }
    for mem in memories:
        content_lower = mem["content"].lower()
        for kw, topic in keywords.items():
            count = content_lower.count(kw)
            if count >= 2:
                if topic not in topic_dates:
                    topic_dates[topic] = {"count": 0, "dates": []}
                topic_dates[topic]["count"] += count
                if mem["date"] not in topic_dates[topic]["dates"]:
                    topic_dates[topic]["dates"].append(mem["date"])

    return [
        {"topic": topic, **data}
        for topic, data in topic_dates.items()
        if len(data["dates"]) >= 2
    ]


def detect_financial_language(memories: list[dict]) -> list[dict]:
    """
    Detect financial stress language in memory files.

    Returns:
        List of {date, keyword, context} matches.
    """
    matches = []
    for mem in memories:
        content_lower = mem["content"].lower()
        for kw in FINANCIAL_KEYWORDS:
            if kw in content_lower:
                # Extract context line
                for line in mem["content"].splitlines():
                    if kw in line.lower():
                        matches.append(
                            {"date": mem["date"], "keyword": kw, "context": line.strip()[:200]}
                        )
                        break
    return matches


def detect_people_frustration(memories: list[dict]) -> list[dict]:
    """
    Detect people frustration signals in memory files.

    Returns:
        List of {date, keyword, context} matches.
    """
    matches = []
    for mem in memories:
        for kw in FRUSTRATION_KEYWORDS:
            if kw in mem["content"].lower():
                for line in mem["content"].splitlines():
                    if kw in line.lower():
                        matches.append(
                            {"date": mem["date"], "keyword": kw, "context": line.strip()[:200]}
                        )
                        break
    return matches


def detect_response_latency(memories: list[dict]) -> list[dict]:
    """
    Detect unusually long gaps between entries in memory files (>8 hours).

    Returns:
        List of {date, gap_description} entries.
    """
    gaps = []
    time_pattern = re.compile(r"\b(\d{1,2}:\d{2})\b")

    for mem in memories:
        times = []
        for line in mem["content"].splitlines():
            for m in time_pattern.finditer(line):
                try:
                    h, mi = map(int, m.group(1).split(":"))
                    times.append(h * 60 + mi)
                except ValueError:
                    pass

        if len(times) >= 2:
            times.sort()
            for i in range(1, len(times)):
                gap_mins = times[i] - times[i - 1]
                if gap_mins >= 480:  # 8 hours
                    gaps.append(
                        {
                            "date": mem["date"],
                            "gap_description": f"{gap_mins // 60}h{gap_mins % 60:02d}m gap detected",
                        }
                    )

    return gaps


def auto_record_signals(analysis: dict) -> None:
    """
    Automatically record detected signals to the JV model.

    Args:
        analysis: The result dict from analyze_message_patterns().
    """
    if not _has_jv_model:
        logger.warning("JV model not available — signals not recorded")
        return

    signal_map = {
        "short_replies": ("short_reply_length", 1.0),
        "late_night":    ("late_night_activity", 1.0),
        "financial":     ("financial_language", 0.8),
        "frustration":   ("people_frustration", 1.2),
        "latency":       ("response_latency_spike", 0.8),
    }
    topic_rep = analysis.get("topic_repetition", [])
    if topic_rep:
        try:
            record_signal("topic_repetition", intensity=min(len(topic_rep) * 0.5, 2.0))
            logger.debug(f"Recorded topic_repetition signal")
        except Exception as e:
            logger.warning(f"Error recording topic_repetition: {e}")

    for key, (signal, base_intensity) in signal_map.items():
        items = analysis.get(key, [])
        if items:
            intensity = min(base_intensity * (len(items) / 3), 2.0)
            try:
                record_signal(signal, intensity=intensity)
                logger.debug(f"Recorded signal {signal} (intensity {intensity:.2f})")
            except Exception as e:
                logger.warning(f"Error recording signal {signal}: {e}")


def analyze_message_patterns(days_back: int = 3) -> dict:
    """
    Run full behavioral signal analysis on recent memory files.

    Args:
        days_back: Number of days back to analyse.

    Returns:
        Dict with all detected signals.
    """
    memories = _read_recent_memories(days_back)
    if not memories:
        logger.info("No memory files found for analysis")
        return {}

    return {
        "analysed_dates": [m["date"] for m in memories],
        "short_replies":     detect_short_replies(memories),
        "late_night":        detect_late_night_activity(memories),
        "topic_repetition":  detect_topic_repetition(memories),
        "financial":         detect_financial_language(memories),
        "frustration":       detect_people_frustration(memories),
        "latency":           detect_response_latency(memories),
    }


def run_analysis_and_record(days_back: int = 3) -> dict:
    """
    Run analysis and automatically record signals to JV model.

    Args:
        days_back: Days of memory to analyse.

    Returns:
        Analysis result dict.
    """
    analysis = analyze_message_patterns(days_back)
    if analysis:
        auto_record_signals(analysis)
    return analysis


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_analysis_and_record()
    print(json.dumps(
        {k: len(v) if isinstance(v, list) else v for k, v in result.items()},
        indent=2,
    ))
