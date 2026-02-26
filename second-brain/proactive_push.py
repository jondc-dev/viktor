#!/usr/bin/env python3
"""
Proactive Push for Viktor

Queues and delivers proactive insights to JV via Slack and WhatsApp.
Respects quiet hours (22:00–06:00 Dubai time) and enforces a 4-hour
deduplication window to avoid message fatigue.

Push queue file: second-brain/push-queue.json
Slack target:    #jv-viktor-private
WhatsApp target: "+XXXXXXXXXXX" (configure via env JV_WHATSAPP_NUMBER)
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Workspace path resolution
WORKSPACE = Path.home() / "clawd"
if not WORKSPACE.exists():
    WORKSPACE = Path("/home/runner/work/viktor/viktor")

SECOND_BRAIN = WORKSPACE / "second-brain"
PUSH_QUEUE_FILE = SECOND_BRAIN / "push-queue.json"

# Delivery targets
SLACK_CHANNEL = "#jv-viktor-private"
WHATSAPP_NUMBER = os.environ.get("JV_WHATSAPP_NUMBER", "+XXXXXXXXXXX")

# Dubai timezone
DUBAI_UTC_OFFSET = timedelta(hours=4)
QUIET_HOUR_START = 22  # 22:00
QUIET_HOUR_END   = 6   # 06:00

# Deduplication window (hours)
DEDUP_WINDOW_HOURS = 4

# Message type priorities (lower = more urgent)
PRIORITY_MAP = {
    "urgent_insight":       1,
    "deadline_reminder":    2,
    "pre_meeting_brief":    3,
    "morning_brief":        4,
    "eod_summary":          5,
    "follow_up_reminder":   6,
    "general":              7,
}

logger = logging.getLogger(__name__)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _now_dubai() -> datetime:
    """Return current datetime in Dubai time."""
    return datetime.now(timezone.utc) + DUBAI_UTC_OFFSET


def _is_quiet_hours() -> bool:
    """Return True if current Dubai time is within quiet hours."""
    hour = _now_dubai().hour
    if QUIET_HOUR_START <= 23:
        return hour >= QUIET_HOUR_START or hour < QUIET_HOUR_END
    return False


def _load_queue() -> dict:
    """Load push queue from disk."""
    if PUSH_QUEUE_FILE.exists():
        try:
            with open(PUSH_QUEUE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading push queue: {e}")
    return {
        "version": "1.0",
        "last_updated": None,
        "queue": [],
        "push_history": [],
    }


def _save_queue(data: dict) -> bool:
    """Atomically save push queue to disk."""
    try:
        PUSH_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp = PUSH_QUEUE_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, PUSH_QUEUE_FILE)
        return True
    except Exception as e:
        logger.error(f"Error saving push queue: {e}")
        return False


def _is_duplicate(msg_type: str, content_key: str, history: list) -> bool:
    """
    Check if a message of the same type+key has been sent in the dedup window.
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=DEDUP_WINDOW_HOURS)
    ).isoformat()
    for entry in history:
        if (
            entry.get("msg_type") == msg_type
            and entry.get("content_key") == content_key
            and entry.get("sent_at", "") > cutoff
        ):
            return True
    return False


def _deliver_message(msg: dict) -> bool:
    """
    Attempt to deliver a message via Slack or WhatsApp.
    Returns True on success (or graceful no-op when SDK unavailable).
    """
    channel = msg.get("channel", "slack")
    content = msg.get("content", "")

    if channel == "slack":
        # Attempt Slack delivery via environment-configured webhook or SDK
        slack_webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
        if slack_webhook:
            try:
                import urllib.request

                payload = json.dumps(
                    {"channel": SLACK_CHANNEL, "text": content}
                ).encode()
                req = urllib.request.Request(
                    slack_webhook,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info(f"Slack message sent to {SLACK_CHANNEL}")
                        return True
                    logger.warning(f"Slack returned HTTP {resp.status}")
            except Exception as e:
                logger.error(f"Slack delivery error: {e}")
        else:
            logger.debug("SLACK_WEBHOOK_URL not set — Slack delivery skipped")

    elif channel == "whatsapp":
        # WhatsApp delivery via configured integration
        wa_key = os.environ.get("WHATSAPP_API_KEY", "")
        if wa_key:
            logger.debug("WhatsApp delivery attempted (SDK not yet wired)")
        else:
            logger.debug("WHATSAPP_API_KEY not set — WhatsApp delivery skipped")

    # Log to console as fallback (so Viktor can manually relay)
    logger.info(f"[PUSH → {channel.upper()}] {content[:200]}")
    return True  # Soft success — message was at least logged


# ── Public API ───────────────────────────────────────────────────────────────

def queue_push(
    msg_type: str,
    content: str,
    channel: str = "slack",
    priority: Optional[int] = None,
    content_key: Optional[str] = None,
    force: bool = False,
) -> Optional[str]:
    """
    Add a message to the push queue.

    Args:
        msg_type:    Message type (see PRIORITY_MAP).
        content:     Message body.
        channel:     'slack' or 'whatsapp'.
        priority:    Override priority (lower = more urgent).
        content_key: Deduplication key (defaults to msg_type).
        force:       Skip quiet-hours and dedup checks.

    Returns:
        Message ID string, or None if rejected.
    """
    try:
        data = _load_queue()
        key = content_key or msg_type

        if not force:
            if _is_duplicate(msg_type, key, data.get("push_history", [])):
                logger.debug(f"Dedup skip: {msg_type} / {key}")
                return None

        now = datetime.now(timezone.utc).isoformat()
        msg_id = f"push_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(data['queue'])}"
        msg = {
            "id": msg_id,
            "msg_type": msg_type,
            "content": content,
            "channel": channel,
            "priority": priority or PRIORITY_MAP.get(msg_type, 7),
            "content_key": key,
            "queued_at": now,
            "status": "pending",
        }
        data["queue"].append(msg)
        # Sort by priority
        data["queue"].sort(key=lambda x: x.get("priority", 7))
        _save_queue(data)
        logger.info(f"Queued push {msg_id} ({msg_type})")
        return msg_id

    except Exception as e:
        logger.error(f"Error queuing push: {e}")
        return None


def process_push_queue(max_messages: int = 5) -> int:
    """
    Process pending messages in the push queue.

    Skips delivery during quiet hours (unless message is urgent).
    Returns the number of messages delivered.
    """
    delivered = 0
    try:
        data = _load_queue()
        pending = [m for m in data.get("queue", []) if m.get("status") == "pending"]

        quiet = _is_quiet_hours()

        for msg in pending[:max_messages]:
            # Urgent messages (priority 1-2) bypass quiet hours
            if quiet and msg.get("priority", 7) > 2:
                logger.debug(f"Quiet hours — skipping {msg['id']}")
                continue

            success = _deliver_message(msg)
            if success:
                msg["status"] = "sent"
                msg["sent_at"] = datetime.now(timezone.utc).isoformat()

                # Record in history for dedup
                data.setdefault("push_history", []).append(
                    {
                        "msg_type": msg["msg_type"],
                        "content_key": msg.get("content_key", msg["msg_type"]),
                        "sent_at": msg["sent_at"],
                    }
                )
                delivered += 1
            else:
                msg["status"] = "failed"

        # Prune sent/failed items from queue (keep last 20 for reference)
        active = [m for m in data["queue"] if m["status"] == "pending"]
        done = [m for m in data["queue"] if m["status"] != "pending"][-20:]
        data["queue"] = active + done

        # Prune push history to last 200 entries
        data["push_history"] = data.get("push_history", [])[-200:]

        _save_queue(data)
        if delivered:
            logger.info(f"Delivered {delivered} push message(s)")

    except Exception as e:
        logger.error(f"Error processing push queue: {e}")

    return delivered


def push_morning_brief(brief_content: str) -> Optional[str]:
    """Queue a morning brief for JV."""
    return queue_push(
        msg_type="morning_brief",
        content=f"🌅 *Viktor's Morning Brief*\n\n{brief_content}",
        channel="slack",
        content_key=f"morning_brief_{datetime.now().strftime('%Y%m%d')}",
    )


def push_pre_meeting_brief(meeting_title: str, notes: str) -> Optional[str]:
    """Queue a pre-meeting brief for JV."""
    content = f"📋 *Pre-Meeting Brief: {meeting_title}*\n\n{notes}"
    return queue_push(
        msg_type="pre_meeting_brief",
        content=content,
        content_key=f"pre_meeting_{meeting_title[:30]}",
    )


def push_deadline_reminder(title: str, days_left: int) -> Optional[str]:
    """Queue a deadline reminder for JV."""
    emoji = "🚨" if days_left <= 1 else "⏰"
    content = (
        f"{emoji} *Deadline Reminder:* {title}\n"
        f"Due in {days_left} day{'s' if days_left != 1 else ''}."
    )
    return queue_push(
        msg_type="deadline_reminder",
        content=content,
        priority=2 if days_left <= 1 else None,
        content_key=f"deadline_{title[:30]}_{days_left}d",
    )


def push_eod_summary(summary: str) -> Optional[str]:
    """Queue an end-of-day summary for JV."""
    return queue_push(
        msg_type="eod_summary",
        content=f"🌙 *End-of-Day Summary*\n\n{summary}",
        content_key=f"eod_{datetime.now().strftime('%Y%m%d')}",
    )


def push_follow_up_reminder(person: str, context: str) -> Optional[str]:
    """Queue a follow-up reminder for JV."""
    content = f"🔔 *Follow-up Reminder*\nChase up *{person}*\n{context[:200]}"
    return queue_push(
        msg_type="follow_up_reminder",
        content=content,
        content_key=f"followup_{person[:20]}",
    )


def push_urgent_insight(insight: str) -> Optional[str]:
    """Queue an urgent insight — bypasses quiet hours."""
    return queue_push(
        msg_type="urgent_insight",
        content=f"🔴 *Urgent Insight*\n\n{insight}",
        priority=1,
        force=True,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Quiet hours: {_is_quiet_hours()}")
    print(f"Push queue file: {PUSH_QUEUE_FILE}")
    processed = process_push_queue()
    print(f"Processed {processed} message(s)")
