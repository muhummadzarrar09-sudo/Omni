"""
OMNI V3 - Send to Phone Tool (Phase 5D)

Brain tool that pushes a notification to all connected mobile devices.

Usage from the brain (via natural language or tool call):
  - "send to my phone: 'remind me to call mom'"
  - "notify my phone that the build finished"
  - "ping my devices: server is back up"

Implements the standard OMNI V3 tool interface so it's auto-registered.
"""
from __future__ import annotations
from typing import Any, Dict
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SendToPhone")


@dataclass
class ToolMetadata:
    name: str = "send_to_phone"
    category: str = "communication"
    description: str = (
        "Sends a push notification to all connected mobile devices (phone, tablet). "
        "Use this when the user wants to be notified on their phone, or when OMNI "
        "completes a long task and the user is away from the laptop. "
        "Examples: 'send to my phone: build complete', 'notify phone: meeting in 5 min', "
        "'ping my phone with this message'."
    )
    patterns: list = None
    examples: list = None

    def __post_init__(self):
        if self.patterns is None:
            self.patterns = [
                r"send to (?:my )?(?:phone|device|tablet|phones|devices)\b[:\s]+(?P<message>.+)",
                r"notify (?:my )?(?:phone|device|tablet|phones|devices)\b[:\s]+(?P<message>.+)",
                r"ping (?:my )?(?:phone|device|tablet|phones|devices)\b[:\s]*(?P<message>.*)",
                r"alert (?:my )?(?:phone|device|tablet)\b[:\s]+(?P<message>.+)",
                r"text (?:me|my phone)[:\s]+(?P<message>.+)",
                r"send notification[:\s]+(?P<message>.+)",
            ]
        if self.examples is None:
            self.examples = [
                "send to my phone: build complete, deploy is ready",
                "notify my devices: meeting in 5 minutes",
                "ping my phone",
                "text me: don't forget the milk",
            ]


def execute(message: str, title: str = "OMNI", priority: int = 1,
            category: str = "info", **kwargs: Any) -> Dict[str, Any]:
    """
    Send a push notification to all connected devices.

    Args:
        message: The body of the notification
        title: Title (default "OMNI")
        priority: 0=low, 1=normal, 2=high, 3=urgent
        category: info/success/warn/error/action_required
    """
    if not message or not message.strip():
        return {"ok": False, "error": "message is required", "data": None}

    try:
        from omni_v2.agents.notifications import get_notification_center, CAT_INFO
        if category not in ("info", "success", "warn", "error", "action_required",
                            "geofence", "proactive", "schedule", "wake", "tool"):
            category = CAT_INFO
        center = get_notification_center()
        notif = center.notify(
            title=title or "OMNI",
            body=message.strip(),
            category=category,
            priority=priority,
            icon="📱" if category == "info" else "🔔",
        )
        devices = center.list_devices()
        return {
            "ok": True,
            "data": {
                "notification_id": notif.id,
                "title": notif.title,
                "body": notif.body,
                "category": notif.category,
                "priority": notif.priority,
                "device_count": len(devices),
                "ts": notif.ts,
            },
            "error": None,
        }
    except Exception as e:
        logger.error(f"send_to_phone failed: {e}")
        return {"ok": False, "error": str(e), "data": None}


def get_metadata() -> Dict[str, Any]:
    return {
        "name": "send_to_phone",
        "category": "communication",
        "description": (
            "Sends a push notification to all connected mobile devices (phone, tablet). "
            "Use when the user wants to be notified on their phone, or when OMNI completes "
            "a long task and the user is away from the laptop. Examples: 'send to my "
            "phone: build complete', 'notify phone: meeting in 5 min'."
        ),
        "patterns": [
            r"send to (?:my )?(?:phone|device|tablet|phones|devices)\b[:\s]+(?P<message>.+)",
            r"notify (?:my )?(?:phone|device|tablet|phones|devices)\b[:\s]+(?P<message>.+)",
            r"ping (?:my )?(?:phone|device|tablet|phones|devices)\b[:\s]*(?P<message>.*)",
            r"alert (?:my )?(?:phone|device|tablet)\b[:\s]+(?P<message>.+)",
            r"text (?:me|my phone)[:\s]+(?P<message>.+)",
            r"send notification[:\s]+(?P<message>.+)",
        ],
        "examples": [
            "send to my phone: build complete, deploy is ready",
            "notify my devices: meeting in 5 minutes",
            "ping my phone",
            "text me: don't forget the milk",
        ],
        "params": {
            "message": {"type": "string", "required": True,
                        "description": "The body of the notification"},
            "title": {"type": "string", "required": False, "default": "OMNI",
                      "description": "Notification title"},
            "priority": {"type": "int", "required": False, "default": 1,
                         "description": "0=low, 1=normal, 2=high, 3=urgent"},
            "category": {"type": "string", "required": False, "default": "info"},
        },
    }


# ---------- Plugin wrapper for the brain ----------
# This makes send_to_phone a discoverable CommandPlugin that the
# brain can register and route to via the standard plugin system.

class SendToPhonePlugin:
    """OMNI V3 plugin: send a push notification to connected mobile devices."""
    metadata = type("M", (), {
        "name": "send_to_phone",
        "category": "communication",
        "description": get_metadata()["description"],
        "patterns": get_metadata()["patterns"],
        "examples": get_metadata()["examples"],
    })()
    SUPPORTED_ACTIONS = [
        "send_to_phone",
        "notify_phone",
        "ping_phone",
        "text_me",
        "alert_phone",
    ]

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> Any:
        from omni_v2.core.plugin_manager import CommandResult
        # Pull the message from multiple possible arg names
        message = (
            entities.get("message")
            or entities.get("text")
            or entities.get("body")
            or entities.get("note")
            or entities.get("content")
        )
        if not message:
            # Try to extract from the original command text
            original = (context or {}).get("original", "")
            for pat in get_metadata()["patterns"]:
                import re
                m = re.search(pat, original, re.IGNORECASE)
                if m:
                    message = m.group("message") if "message" in m.groupdict() else m.group(0)
                    if message:
                        message = message.strip()
                    break
        if not message:
            # "ping my phone" with no message — use a default
            message = "👋 OMNI is checking in"
        result = execute(
            message=message,
            title=entities.get("title", "OMNI"),
            priority=int(entities.get("priority", 1)),
            category=entities.get("category", "info"),
        )
        if result["ok"]:
            return CommandResult.ok(result["data"].get("body", ""), data=result["data"])
        return CommandResult.fail(result.get("error", "unknown error"))


def get_plugin() -> SendToPhonePlugin:
    """Factory for the plugin manager."""
    return SendToPhonePlugin()
