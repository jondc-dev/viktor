#!/usr/bin/env python3
"""
Cognitive Loop for Viktor — 5-Phase Butler Brain Orchestrator

Phases:
  1. GATHER    — Collect context signals from all sources
  2. ANALYSE   — Detect patterns, gaps, and risks
  3. RECOMMEND — Generate actionable recommendations
  4. DELIVER   — Push briefs and queue proactive messages
  5. LEARN     — Record outcomes and update JV model

Runs every 30 minutes during business hours (Sun-Thu 07:00–19:00 Dubai).
Log:       second-brain/cognitive-loop.log
Dashboard: second-brain/cognitive-dashboard-state.json
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

SECOND_BRAIN = WORKSPACE / "second-brain"
LOG_FILE       = SECOND_BRAIN / "cognitive-loop.log"
DASHBOARD_FILE = SECOND_BRAIN / "cognitive-dashboard-state.json"

sys.path.insert(0, str(SECOND_BRAIN))

# Core imports (required)
from context_scanner import get_comprehensive_context
from jv_model import get_jv_state_summary, record_signal, calculate_trends
from interventions import log_intervention, get_recent_interventions
from morning_brief import generate_morning_brief, save_morning_brief, generate_evening_brief

# Optional imports — degrade gracefully
try:
    from anticipation_engine import (
        infer_next_steps,
        get_predicted_questions,
        detect_habits,
    )
    _has_anticipation = True
except ImportError:
    _has_anticipation = False

try:
    from proactive_push import (
        queue_push,
        process_push_queue,
        push_morning_brief,
        push_eod_summary,
        push_deadline_reminder,
    )
    _has_push = True
except ImportError:
    _has_push = False

# Optional: scripts/ modules
SCRIPTS_DIR = WORKSPACE / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from message_analyzer import run_analysis_and_record
    _has_message_analyzer = True
except ImportError:
    _has_message_analyzer = False

try:
    from horizon_scan import generate_horizon_scan, save_horizon_scan, should_generate_horizon_scan
    _has_horizon = True
except ImportError:
    try:
        sys.path.insert(0, str(SECOND_BRAIN))
        from horizon_scan import generate_horizon_scan, save_horizon_scan, should_generate_horizon_scan
        _has_horizon = True
    except ImportError:
        _has_horizon = False

# Dubai timezone
DUBAI_UTC_OFFSET = timedelta(hours=4)
BUSINESS_DAYS = {6, 0, 1, 2, 3}  # Sun=6, Mon=0 … Thu=3
BUSINESS_START = 7
BUSINESS_END   = 19

# Pattern thresholds
OVERDUE_THRESHOLD     = 1    # flag if any deadlines overdue
DEADLINE_CLUSTER_DAYS = 3    # flag if ≥3 deadlines in N days
COMM_GAP_HOURS        = 48   # flag if no memory update in N hours
WORKLOAD_HIGH_COUNT   = 5    # flag if ≥N deadlines in next 7 days


def _setup_logging():
    """Configure logging for the cognitive loop."""
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


def _now_dubai() -> datetime:
    return datetime.now(timezone.utc) + DUBAI_UTC_OFFSET


def _is_business_hours() -> bool:
    now = _now_dubai()
    return now.weekday() in BUSINESS_DAYS and BUSINESS_START <= now.hour < BUSINESS_END


def _load_dashboard() -> dict:
    if DASHBOARD_FILE.exists():
        try:
            with open(DASHBOARD_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"version": "1.0", "last_cycle": None, "cycle_count": 0}


def _save_dashboard(data: dict) -> None:
    try:
        DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["last_cycle"] = datetime.now(timezone.utc).isoformat()
        tmp = DASHBOARD_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, DASHBOARD_FILE)
    except Exception as e:
        logging.error(f"Error saving dashboard: {e}")


# ── Phase 1: GATHER ───────────────────────────────────────────────────────────

def phase_gather(logger) -> dict:
    """Collect all context signals."""
    logger.info("Phase 1: GATHER")
    signals = {}

    try:
        signals["context"] = get_comprehensive_context()
        logger.info("  ✓ Comprehensive context loaded")
    except Exception as e:
        logger.error(f"  ✗ Context scan failed: {e}")
        signals["context"] = {}

    try:
        signals["jv_state"] = get_jv_state_summary()
        logger.info(
            f"  ✓ JV state: {signals['jv_state'].get('overall_status', 'unknown')}"
        )
    except Exception as e:
        logger.error(f"  ✗ JV state load failed: {e}")
        signals["jv_state"] = {}

    if _has_message_analyzer:
        try:
            run_analysis_and_record()
            logger.info("  ✓ Message analysis complete")
        except Exception as e:
            logger.warning(f"  ✗ Message analysis failed: {e}")

    if _has_anticipation:
        try:
            ctx = signals["context"]
            signals["predicted_questions"] = get_predicted_questions(ctx)
            logger.info(
                f"  ✓ {len(signals.get('predicted_questions', []))} predicted questions"
            )
        except Exception as e:
            logger.warning(f"  ✗ Predicted questions failed: {e}")

    return signals


# ── Phase 2: ANALYSE ──────────────────────────────────────────────────────────

def phase_analyse(signals: dict, logger) -> dict:
    """Detect patterns, gaps, and risks."""
    logger.info("Phase 2: ANALYSE")
    findings = {}

    ctx = signals.get("context", {})
    jv_state = signals.get("jv_state", {})
    today = date.today()

    # Overdue deadlines
    overdue = ctx.get("overdue_deadlines", [])
    if overdue:
        findings["overdue"] = overdue
        logger.info(f"  ⚠ {len(overdue)} overdue deadline(s) detected")

    # Deadline clustering
    deadlines = ctx.get("deadlines", [])
    cluster_window = [d for d in deadlines if 0 <= d.get("days_left", 99) <= DEADLINE_CLUSTER_DAYS]
    if len(cluster_window) >= 3:
        findings["deadline_cluster"] = cluster_window
        logger.info(f"  ⚠ Deadline cluster: {len(cluster_window)} items in {DEADLINE_CLUSTER_DAYS} days")

    # High workload
    near_deadlines = [d for d in deadlines if d.get("days_left", 99) <= 7]
    if len(near_deadlines) >= WORKLOAD_HIGH_COUNT:
        findings["high_workload"] = near_deadlines
        logger.info(f"  ⚠ High workload: {len(near_deadlines)} deadlines in next 7 days")

    # JV dimension stress
    under_stress = jv_state.get("under_stress", [])
    if under_stress:
        findings["dimension_stress"] = under_stress
        dims = [d["dimension"] for d in under_stress]
        logger.info(f"  ⚠ JV dimensions under stress: {', '.join(dims)}")

    # Active behavioral signals
    active_signals = jv_state.get("active_signals", [])
    if active_signals:
        findings["behavioral_signals"] = active_signals
        logger.info(f"  ⚠ Active signals: {', '.join(active_signals)}")

    # People waiting
    people_waiting = ctx.get("people_waiting", [])
    if people_waiting:
        findings["people_waiting"] = people_waiting

    # Compound pattern: stress + deadline cluster
    if under_stress and cluster_window:
        findings["compound_risk"] = True
        logger.warning("  🚨 Compound risk: JV under stress AND deadline cluster")

    logger.info(f"  ✓ Analysis complete — {len(findings)} finding(s)")
    return findings


# ── Phase 3: RECOMMEND ────────────────────────────────────────────────────────

def phase_recommend(signals: dict, findings: dict, logger) -> list[dict]:
    """Generate actionable recommendations."""
    logger.info("Phase 3: RECOMMEND")
    recommendations = []

    # Overdue items → immediate action
    for dl in findings.get("overdue", [])[:2]:
        recommendations.append(
            {
                "type": "urgent",
                "action": f"Address overdue item: {dl.get('title', 'Unknown')}",
                "trigger": "overdue_deadline",
            }
        )

    # Deadline cluster → heads-up
    if findings.get("deadline_cluster"):
        recommendations.append(
            {
                "type": "warning",
                "action": f"{len(findings['deadline_cluster'])} deadlines clustering in the next {DEADLINE_CLUSTER_DAYS} days — review priorities",
                "trigger": "deadline_cluster",
            }
        )

    # High workload → delegation reminder
    if findings.get("high_workload") and not findings.get("deadline_cluster"):
        recommendations.append(
            {
                "type": "info",
                "action": "Heavy workload ahead — consider delegating lower-priority items",
                "trigger": "high_workload",
            }
        )

    # Compound risk → escalate
    if findings.get("compound_risk"):
        recommendations.append(
            {
                "type": "escalate",
                "action": "Compound risk detected: JV is under cognitive stress AND facing deadline cluster. Simplify today's agenda.",
                "trigger": "compound_risk",
            }
        )

    # People waiting → follow-up prompt
    for person in findings.get("people_waiting", [])[:2]:
        recommendations.append(
            {
                "type": "follow_up",
                "action": f"Follow up with {person.get('person', 'contact')}: {person.get('context', '')[:80]}",
                "trigger": "people_waiting",
            }
        )

    logger.info(f"  ✓ {len(recommendations)} recommendation(s) generated")
    return recommendations


# ── Phase 4: DELIVER ──────────────────────────────────────────────────────────

def phase_deliver(signals: dict, recommendations: list[dict], logger) -> None:
    """Generate and queue briefs; push proactive messages."""
    logger.info("Phase 4: DELIVER")
    now = _now_dubai()
    ctx = signals.get("context", {})

    # Morning brief (07:00–09:00)
    if 7 <= now.hour < 9:
        try:
            brief = generate_morning_brief(ctx)
            path = save_morning_brief(brief)
            if path:
                logger.info(f"  ✓ Morning brief saved: {path.name}")
            if _has_push:
                push_morning_brief(brief[:2000])
                logger.info("  ✓ Morning brief queued for push")
        except Exception as e:
            logger.error(f"  ✗ Morning brief delivery failed: {e}")

    # Evening brief (17:00–19:00)
    if 17 <= now.hour < 19:
        try:
            eod = generate_evening_brief(ctx)
            if _has_push:
                push_eod_summary(eod[:2000])
                logger.info("  ✓ EOD brief queued for push")
        except Exception as e:
            logger.error(f"  ✗ Evening brief delivery failed: {e}")

    # Deadline reminders
    if _has_push:
        for dl in ctx.get("deadlines", []):
            days_left = dl.get("days_left", 99)
            if days_left in (0, 1, 3, 7):
                try:
                    push_deadline_reminder(dl.get("title", "Deadline"), days_left)
                except Exception as e:
                    logger.warning(f"  ✗ Deadline push failed: {e}")

    # Log interventions for urgent recommendations
    for rec in recommendations:
        if rec.get("type") in ("urgent", "escalate"):
            try:
                log_intervention(
                    intervention_type=rec["trigger"],
                    content=rec["action"],
                    trigger="cognitive_loop",
                )
            except Exception as e:
                logger.warning(f"  ✗ Intervention log failed: {e}")

    # Horizon scan on Sundays
    if now.weekday() == 6 and _has_horizon:  # Sunday = 6
        try:
            if should_generate_horizon_scan():
                scan = generate_horizon_scan(ctx)
                save_horizon_scan(scan)
                logger.info("  ✓ Horizon scan generated (Sunday)")
        except Exception as e:
            logger.warning(f"  ✗ Horizon scan failed: {e}")

    # Process push queue
    if _has_push:
        try:
            delivered = process_push_queue()
            if delivered:
                logger.info(f"  ✓ Delivered {delivered} push message(s)")
        except Exception as e:
            logger.error(f"  ✗ Push queue processing failed: {e}")

    logger.info("  ✓ Delivery phase complete")


# ── Phase 5: LEARN ────────────────────────────────────────────────────────────

def phase_learn(signals: dict, logger) -> None:
    """Update JV model trends; record intervention outcomes."""
    logger.info("Phase 5: LEARN")

    try:
        calculate_trends()
        logger.info("  ✓ JV model trends recalculated")
    except Exception as e:
        logger.warning(f"  ✗ Trend calculation failed: {e}")

    try:
        recent = get_recent_interventions(hours=2)
        logger.info(f"  ✓ {len(recent)} recent intervention(s) on record")
    except Exception as e:
        logger.warning(f"  ✗ Intervention review failed: {e}")

    if _has_anticipation:
        try:
            mem_dir = WORKSPACE / "memory"
            if mem_dir.exists():
                texts = []
                today = date.today()
                for i in range(3):
                    f = mem_dir / f"{(today - timedelta(days=i)).isoformat()}.md"
                    if f.exists():
                        texts.append(f.read_text(encoding="utf-8"))
                if texts:
                    detect_habits(texts)
                    logger.info("  ✓ Habits updated from memory files")
        except Exception as e:
            logger.warning(f"  ✗ Habit detection failed: {e}")

    logger.info("  ✓ Learn phase complete")


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run_cognitive_loop() -> dict:
    """
    Execute one full 5-phase cognitive loop cycle.

    Returns:
        Summary dict with cycle metadata.
    """
    logger = _setup_logging()
    dashboard = _load_dashboard()

    cycle_num = dashboard.get("cycle_count", 0) + 1
    logger.info(f"═══ Cognitive Loop Cycle #{cycle_num} ═══")

    if not _is_business_hours():
        logger.info("Outside business hours — skipping cycle")
        return {"skipped": True, "reason": "outside_business_hours"}

    result = {"cycle": cycle_num, "phases": {}}

    try:
        # Phase 1: GATHER
        signals = phase_gather(logger)
        result["phases"]["gather"] = "ok"

        # Phase 2: ANALYSE
        findings = phase_analyse(signals, logger)
        result["phases"]["analyse"] = "ok"
        result["findings_count"] = len(findings)

        # Phase 3: RECOMMEND
        recommendations = phase_recommend(signals, findings, logger)
        result["phases"]["recommend"] = "ok"
        result["recommendations_count"] = len(recommendations)

        # Phase 4: DELIVER
        phase_deliver(signals, recommendations, logger)
        result["phases"]["deliver"] = "ok"

        # Phase 5: LEARN
        phase_learn(signals, logger)
        result["phases"]["learn"] = "ok"

    except Exception as e:
        logger.error(f"Cognitive loop error: {e}")
        result["error"] = str(e)

    # Update dashboard
    dashboard["cycle_count"] = cycle_num
    dashboard["last_findings"] = result.get("findings_count", 0)
    dashboard["last_recommendations"] = result.get("recommendations_count", 0)
    _save_dashboard(dashboard)

    logger.info(f"═══ Cycle #{cycle_num} complete ═══")
    return result


if __name__ == "__main__":
    result = run_cognitive_loop()
    print(json.dumps(result, indent=2, default=str))
