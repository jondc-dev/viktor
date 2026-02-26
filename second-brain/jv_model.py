#!/usr/bin/env python3
"""
JV Model — Cognitive State Tracker for Viktor

Tracks JV's cognitive and emotional state across 6 dimensions using
9 behavioral signals observed through communication patterns.
This module is observe-only — never guess, never assume.

State persisted to: second-brain/jv-state.json
"""

import json
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

STATE_FILE = WORKSPACE / "second-brain" / "jv-state.json"

# 6 cognitive/emotional dimensions tracked for JV
DIMENSIONS = [
    "decision_bandwidth",
    "strategic_focus",
    "operational_control",
    "emotional_reserves",
    "physical_wellbeing",
    "relationship_capital",
]

# 9 behavioral signals observable from communication patterns
BEHAVIORAL_SIGNALS = [
    "short_reply_length",
    "late_night_activity",
    "response_latency_spike",
    "topic_repetition",
    "delegation_spike",
    "financial_language",
    "meeting_cancellations",
    "people_frustration",
    "message_ignored",
]

# Signal → dimension impact mappings
SIGNAL_IMPACTS = {
    "short_reply_length":      {"decision_bandwidth": -5, "emotional_reserves": -3},
    "late_night_activity":     {"physical_wellbeing": -8, "decision_bandwidth": -4},
    "response_latency_spike":  {"decision_bandwidth": -6, "strategic_focus": -4},
    "topic_repetition":        {"strategic_focus": -5, "operational_control": -3},
    "delegation_spike":        {"decision_bandwidth": -8, "operational_control": -5},
    "financial_language":      {"strategic_focus": -5, "decision_bandwidth": -3},
    "meeting_cancellations":   {"operational_control": -6, "relationship_capital": -4},
    "people_frustration":      {"relationship_capital": -8, "emotional_reserves": -5},
    "message_ignored":         {"relationship_capital": -5, "operational_control": -3},
}

# Dimension status thresholds
STATUS_THRESHOLDS = {
    "critical": 30,
    "low":      50,
    "stable":   70,
    "high":     85,
}

logger = logging.getLogger(__name__)


def create_default_state() -> dict:
    """Create a fresh default JV state with all dimensions at baseline."""
    dimensions = {}
    for dim in DIMENSIONS:
        dimensions[dim] = {
            "value": 70,
            "status": "stable",
            "signals": [],
            "trend": "stable",
        }

    return {
        "version": "1.0",
        "last_updated": None,
        "dimensions": dimensions,
        "decision_patterns": {},
        "stress_indicators": {"behavioral_signals": {}},
        "intervention_effectiveness": {},
        "historical_observations": [],
    }


def load_jv_state() -> dict:
    """
    Load JV's cognitive state from disk.
    Returns default state if file does not exist or is corrupt.
    """
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            # Back-fill any missing dimensions
            for dim in DIMENSIONS:
                if dim not in state.get("dimensions", {}):
                    state["dimensions"][dim] = {
                        "value": 70,
                        "status": "stable",
                        "signals": [],
                        "trend": "stable",
                    }
            return state
        except Exception as e:
            logger.error(f"Error loading JV state: {e}")

    return create_default_state()


def save_jv_state(state: dict) -> bool:
    """
    Atomically save JV's cognitive state to disk.
    Uses .tmp + os.replace() pattern for safety.
    """
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp_path = STATE_FILE.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, STATE_FILE)
        return True
    except Exception as e:
        logger.error(f"Error saving JV state: {e}")
        return False


def _dimension_status(value: float) -> str:
    """Map a numeric dimension value to a status label."""
    if value <= STATUS_THRESHOLDS["critical"]:
        return "critical"
    if value <= STATUS_THRESHOLDS["low"]:
        return "low"
    if value <= STATUS_THRESHOLDS["stable"]:
        return "stable"
    return "high"


def record_signal(signal: str, intensity: float = 1.0, notes: str = "") -> bool:
    """
    Record a behavioral signal observation and apply its dimension impacts.

    Args:
        signal: One of the 9 BEHAVIORAL_SIGNALS.
        intensity: Multiplier for impact (0.5 = mild, 1.0 = normal, 2.0 = severe).
        notes: Optional context notes.

    Returns:
        True on success, False on failure.
    """
    if signal not in BEHAVIORAL_SIGNALS:
        logger.warning(f"Unknown signal: {signal}")
        return False

    try:
        state = load_jv_state()
        now = datetime.now(timezone.utc).isoformat()

        # Record in stress_indicators
        sig_tracker = state.setdefault("stress_indicators", {}).setdefault(
            "behavioral_signals", {}
        )
        if signal not in sig_tracker:
            sig_tracker[signal] = {"count": 0, "last_seen": None, "notes": []}
        sig_tracker[signal]["count"] = sig_tracker[signal].get("count", 0) + 1
        sig_tracker[signal]["last_seen"] = now
        if notes:
            sig_tracker[signal].setdefault("notes", []).append(
                {"timestamp": now, "text": notes}
            )

        # Apply dimension impacts
        impacts = SIGNAL_IMPACTS.get(signal, {})
        for dim, delta in impacts.items():
            adjusted = delta * intensity
            dim_data = state["dimensions"][dim]
            old_val = dim_data["value"]
            new_val = max(0.0, min(100.0, old_val + adjusted))
            dim_data["value"] = round(new_val, 1)
            dim_data["status"] = _dimension_status(new_val)
            dim_data.setdefault("signals", []).append(
                {"signal": signal, "delta": adjusted, "timestamp": now}
            )
            # Keep only last 20 signals per dimension
            dim_data["signals"] = dim_data["signals"][-20:]

        return save_jv_state(state)

    except Exception as e:
        logger.error(f"Error recording signal {signal}: {e}")
        return False


def update_dimension(dimension: str, value: float, reason: str = "") -> bool:
    """
    Directly set a dimension value (from explicit observation).

    Args:
        dimension: One of the 6 DIMENSIONS.
        value: New value in range [0, 100].
        reason: Optional reason for the update.

    Returns:
        True on success, False on failure.
    """
    if dimension not in DIMENSIONS:
        logger.warning(f"Unknown dimension: {dimension}")
        return False

    try:
        state = load_jv_state()
        value = max(0.0, min(100.0, float(value)))
        now = datetime.now(timezone.utc).isoformat()

        dim_data = state["dimensions"][dimension]
        old_val = dim_data["value"]
        dim_data["value"] = round(value, 1)
        dim_data["status"] = _dimension_status(value)

        # Record in history
        state.setdefault("historical_observations", []).append(
            {
                "timestamp": now,
                "dimension": dimension,
                "old_value": old_val,
                "new_value": value,
                "reason": reason,
            }
        )
        # Keep last 100 observations
        state["historical_observations"] = state["historical_observations"][-100:]

        return save_jv_state(state)

    except Exception as e:
        logger.error(f"Error updating dimension {dimension}: {e}")
        return False


def record_intervention(
    intervention_type: str, content: str, trigger: str = ""
) -> Optional[str]:
    """
    Record a Viktor intervention in the JV state.

    Args:
        intervention_type: Type of intervention (e.g. 'morning_brief', 'reminder').
        content: Brief description of the intervention.
        trigger: What triggered it.

    Returns:
        Intervention ID string, or None on failure.
    """
    try:
        state = load_jv_state()
        now = datetime.now(timezone.utc).isoformat()
        iid = f"int_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        state.setdefault("intervention_effectiveness", {})[iid] = {
            "type": intervention_type,
            "content": content,
            "trigger": trigger,
            "timestamp": now,
            "outcome": None,
            "jv_response": None,
        }
        save_jv_state(state)
        return iid

    except Exception as e:
        logger.error(f"Error recording intervention: {e}")
        return None


def record_intervention_outcome(
    intervention_id: str, outcome: str, jv_response: str = ""
) -> bool:
    """
    Record the outcome of a Viktor intervention.

    Args:
        intervention_id: The ID returned by record_intervention().
        outcome: 'accepted', 'ignored', 'rejected', or 'partial'.
        jv_response: JV's actual response (optional).

    Returns:
        True on success, False on failure.
    """
    try:
        state = load_jv_state()
        interventions = state.get("intervention_effectiveness", {})

        if intervention_id not in interventions:
            logger.warning(f"Intervention not found: {intervention_id}")
            return False

        interventions[intervention_id]["outcome"] = outcome
        interventions[intervention_id]["jv_response"] = jv_response
        interventions[intervention_id]["resolved_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        return save_jv_state(state)

    except Exception as e:
        logger.error(f"Error recording outcome for {intervention_id}: {e}")
        return False


def get_jv_state_summary() -> dict:
    """
    Return a concise summary of JV's current cognitive state.

    Returns:
        Dict with dimension summaries, stress signals, and overall health score.
    """
    try:
        state = load_jv_state()
        dimensions = state.get("dimensions", {})

        # Compute overall health as average of all dimension values
        values = [d["value"] for d in dimensions.values()]
        overall = round(sum(values) / len(values), 1) if values else 70.0

        # Identify dimensions under stress
        under_stress = [
            {"dimension": dim, "value": data["value"], "status": data["status"]}
            for dim, data in dimensions.items()
            if data["status"] in ("critical", "low")
        ]

        # Active behavioral signals (seen in last 24 hours)
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        active_signals = [
            sig
            for sig, data in state.get("stress_indicators", {})
            .get("behavioral_signals", {})
            .items()
            if data.get("last_seen", "") > cutoff
        ]

        return {
            "overall_health": overall,
            "overall_status": _dimension_status(overall),
            "dimensions": {
                dim: {
                    "value": data["value"],
                    "status": data["status"],
                    "trend": data.get("trend", "stable"),
                }
                for dim, data in dimensions.items()
            },
            "under_stress": under_stress,
            "active_signals": active_signals,
            "last_updated": state.get("last_updated"),
        }

    except Exception as e:
        logger.error(f"Error generating JV state summary: {e}")
        return {"overall_health": 70, "overall_status": "stable", "error": str(e)}


def calculate_trends() -> bool:
    """
    Recalculate trend directions for all dimensions based on recent signal history.
    Trends: 'improving', 'declining', 'stable'.

    Returns:
        True on success, False on failure.
    """
    try:
        state = load_jv_state()

        for dim, data in state["dimensions"].items():
            signals = data.get("signals", [])
            if len(signals) < 3:
                data["trend"] = "stable"
                continue

            # Use last 10 signals
            recent = signals[-10:]
            total_delta = sum(s.get("delta", 0) for s in recent)

            if total_delta > 5:
                data["trend"] = "improving"
            elif total_delta < -5:
                data["trend"] = "declining"
            else:
                data["trend"] = "stable"

        return save_jv_state(state)

    except Exception as e:
        logger.error(f"Error calculating trends: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    summary = get_jv_state_summary()
    print(json.dumps(summary, indent=2))
