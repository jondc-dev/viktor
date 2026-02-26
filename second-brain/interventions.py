#!/usr/bin/env python3
"""
Interventions Logger for Viktor

Logs proactive interventions Viktor makes on JV's behalf, and tracks
their acceptance rates to improve future behaviour.

Log file: second-brain/interventions-log.json
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN = WORKSPACE / "second-brain"
LOG_FILE = SECOND_BRAIN / "interventions-log.json"

logger = logging.getLogger(__name__)

VALID_OUTCOMES = {"accepted", "ignored", "rejected", "partial"}


# ── Internal helpers ─────────────────────────────────────────────────────────

def _load_log() -> dict:
    """Load interventions log from disk."""
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading interventions log: {e}")
    return {"version": "1.0", "interventions": []}


def _save_log(data: dict) -> bool:
    """Atomically save interventions log to disk."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = LOG_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, LOG_FILE)
        return True
    except Exception as e:
        logger.error(f"Error saving interventions log: {e}")
        return False


# ── Public API ───────────────────────────────────────────────────────────────

def log_intervention(
    intervention_type: str,
    content: str,
    trigger: str = "",
    channel: str = "chat",
) -> Optional[str]:
    """
    Log a Viktor intervention.

    Args:
        intervention_type: E.g. 'morning_brief', 'deadline_reminder', 'suggestion'.
        content:           Brief description or excerpt of the intervention.
        trigger:           What caused Viktor to intervene.
        channel:           Delivery channel ('chat', 'slack', 'whatsapp').

    Returns:
        Intervention ID string, or None on failure.
    """
    try:
        data = _load_log()
        now = datetime.now(timezone.utc).isoformat()
        iid = f"int_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(data['interventions'])}"

        data["interventions"].append(
            {
                "id": iid,
                "type": intervention_type,
                "content": content[:500],
                "trigger": trigger,
                "channel": channel,
                "timestamp": now,
                "outcome": None,
                "jv_response": None,
                "resolved_at": None,
            }
        )
        _save_log(data)
        logger.info(f"Logged intervention {iid} ({intervention_type})")
        return iid

    except Exception as e:
        logger.error(f"Error logging intervention: {e}")
        return None


def record_outcome(
    intervention_id: str,
    outcome: str,
    jv_response: str = "",
) -> bool:
    """
    Record JV's response to an intervention.

    Args:
        intervention_id: The ID returned by log_intervention().
        outcome:         One of: 'accepted', 'ignored', 'rejected', 'partial'.
        jv_response:     JV's actual response text (optional).

    Returns:
        True on success, False on failure.
    """
    if outcome not in VALID_OUTCOMES:
        logger.warning(f"Invalid outcome '{outcome}'. Must be one of {VALID_OUTCOMES}")
        return False

    try:
        data = _load_log()
        for entry in data["interventions"]:
            if entry["id"] == intervention_id:
                entry["outcome"] = outcome
                entry["jv_response"] = jv_response[:500] if jv_response else None
                entry["resolved_at"] = datetime.now(timezone.utc).isoformat()
                _save_log(data)
                logger.info(f"Recorded outcome for {intervention_id}: {outcome}")
                return True

        logger.warning(f"Intervention not found: {intervention_id}")
        return False

    except Exception as e:
        logger.error(f"Error recording outcome for {intervention_id}: {e}")
        return False


def get_effectiveness_report() -> dict:
    """
    Compute acceptance rates and effectiveness by intervention type.

    Returns:
        Dict with per-type statistics and overall rates.
    """
    try:
        data = _load_log()
        resolved = [i for i in data["interventions"] if i.get("outcome")]

        if not resolved:
            return {"total_resolved": 0, "by_type": {}, "overall": {}}

        # Aggregate by type
        by_type: dict[str, dict] = {}
        for entry in resolved:
            t = entry["type"]
            if t not in by_type:
                by_type[t] = {
                    "accepted": 0,
                    "ignored": 0,
                    "rejected": 0,
                    "partial": 0,
                    "total": 0,
                }
            by_type[t][entry["outcome"]] = by_type[t].get(entry["outcome"], 0) + 1
            by_type[t]["total"] += 1

        # Add acceptance rate per type
        for t, stats in by_type.items():
            accepted = stats["accepted"] + stats.get("partial", 0)
            stats["acceptance_rate"] = round(accepted / stats["total"], 3) if stats["total"] else 0

        # Overall stats
        total = len(resolved)
        overall_accepted = sum(
            1 for i in resolved if i["outcome"] in ("accepted", "partial")
        )
        overall_rate = round(overall_accepted / total, 3) if total else 0

        return {
            "total_resolved": total,
            "overall_acceptance_rate": overall_rate,
            "by_type": by_type,
        }

    except Exception as e:
        logger.error(f"Error generating effectiveness report: {e}")
        return {"error": str(e)}


def get_recent_interventions(hours: int = 24) -> list[dict]:
    """
    Return interventions from the last N hours.

    Args:
        hours: Lookback window in hours.

    Returns:
        List of recent intervention dicts.
    """
    try:
        data = _load_log()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        return [i for i in data["interventions"] if i.get("timestamp", "") > cutoff]
    except Exception as e:
        logger.error(f"Error getting recent interventions: {e}")
        return []


def get_pending_interventions() -> list[dict]:
    """
    Return interventions that have not yet received an outcome.

    Returns:
        List of pending intervention dicts.
    """
    try:
        data = _load_log()
        return [i for i in data["interventions"] if not i.get("outcome")]
    except Exception as e:
        logger.error(f"Error getting pending interventions: {e}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import json

    report = get_effectiveness_report()
    print(json.dumps(report, indent=2))
