"""
OMNI V3 - Snooze / DND Tool (Phase 5E)

Brain tool for muting notifications temporarily.
"""
from __future__ import annotations
import re
import time
from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class ToolMetadata:
    name: str = "snooze_notifications"
    category: str = "communication"
    description: str = (
        "Snooze / mute all notifications for N minutes. "
        "Use when the user wants quiet time, e.g. 'snooze for 30 minutes', "
        "'mute notifications for an hour', 'silence for 15 min', 'enable do not disturb'."
    )
    patterns: list = None
    examples: list = None

    def __post_init__(self):
        if self.patterns is None:
            self.patterns = [
                r"snooze\s+(?:notifications?|alerts?)\s+(?:for\s+)?(?P<minutes>\d+)\s*(?:min(?:ute)?s?)?",
                r"mute\s+(?:notifications?|alerts?)\s+(?:for\s+)?(?P<minutes>\d+)\s*(?:min(?:ute)?s?)?",
                r"silence\s+(?:notifications?|alerts?)?\s*(?:for\s+)?(?P<minutes>\d+)\s*(?:min(?:ute)?s?)?",
                r"(?:enable|turn\s+on)\s+(?:do\s+not\s+disturb|dnd|quiet\s+mode)\s+(?:for\s+)?(?P<minutes>\d+)?",
                r"(?:disable|turn\s+off|stop)\s+(?:do\s+not\s+disturb|dnd|quiet\s+mode|snooze)",
            ]
        if self.examples is None:
            self.examples = [
                "snooze for 30 minutes",
                "mute notifications for an hour",
                "silence for 15 min",
                "enable do not disturb",
                "stop snooze",
            ]


def execute_snooze(minutes: float = 30, action: str = "snooze", **kwargs) -> Dict[str, Any]:
    """Snooze or unsnooze notifications."""
    try:
        from omni_v2.agents.notification_prefs import get_notification_prefs
        prefs = get_notification_prefs()
        if action == "unsnooze" or minutes == 0:
            prefs.unsnooze()
            return {
                "ok": True,
                "data": {"snoozed": False, "message": "Snooze lifted. Notifications resumed."},
                "error": None,
            }
        # Clamp to 1-1440 minutes (24h)
        minutes = max(1.0, min(1440.0, float(minutes)))
        state = prefs.snooze_for(minutes=minutes, reason="user_snooze")
        until_str = time.strftime("%H:%M", time.localtime(state.until))
        return {
            "ok": True,
            "data": {
                "snoozed": True,
                "minutes": minutes,
                "until": state.until,
                "until_human": until_str,
                "message": f"🔕 Snoozed for {int(minutes)} minutes (until {until_str})",
            },
            "error": None,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "data": None}


def get_metadata() -> Dict[str, Any]:
    return {
        "name": "snooze_notifications",
        "category": "communication",
        "description": (
            "Snooze or unsnooze all notifications. Use for 'quiet time' requests. "
            "Examples: 'snooze for 30 min', 'mute for an hour', 'enable do not disturb'."
        ),
        "patterns": [
            r"snooze\s+(?:notifications?|alerts?)\s+(?:for\s+)?(?P<minutes>\d+)\s*(?:min(?:ute)?s?)?",
            r"mute\s+(?:notifications?|alerts?)\s+(?:for\s+)?(?P<minutes>\d+)\s*(?:min(?:ute)?s?)?",
            r"silence\s+(?:notifications?|alerts?)?\s*(?:for\s+)?(?P<minutes>\d+)\s*(?:min(?:ute)?s?)?",
            r"(?:enable|turn\s+on)\s+(?:do\s+not\s+disturb|dnd|quiet\s+mode)\s+(?:for\s+)?(?P<minutes>\d+)?",
            r"(?:disable|turn\s+off|stop)\s+(?:do\s+not\s+disturb|dnd|quiet\s+mode|snooze)",
        ],
        "examples": [
            "snooze for 30 minutes",
            "mute notifications for an hour",
            "silence for 15 min",
            "enable do not disturb",
            "stop snooze",
        ],
        "params": {
            "minutes": {"type": "number", "required": False, "default": 30,
                        "description": "How long to snooze (1-1440 min)"},
            "action": {"type": "string", "required": False, "default": "snooze",
                       "description": "'snooze' or 'unsnooze'"},
        },
    }


class SnoozePlugin:
    """Brain plugin: snooze / unsnooze notifications."""
    metadata = type("M", (), {
        "name": "snooze_notifications",
        "category": "communication",
        "description": get_metadata()["description"],
        "patterns": get_metadata()["patterns"],
        "examples": get_metadata()["examples"],
    })()
    SUPPORTED_ACTIONS = ["snooze_notifications", "unsnooze", "dnd", "mute_notifications"]

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> Any:
        from omni_v2.core.plugin_manager import CommandResult
        minutes = entities.get("minutes") or 0
        action = entities.get("action", "snooze")
        original = (context or {}).get("original", "")
        # Always try to extract the unit (hour vs minute) from the original text
        if original and minutes:
            m = re.search(r"(\d+)\s*(min(?:ute)?s?|hours?|hr|h)\b", original, re.IGNORECASE)
            if m:
                unit = m.group(2).lower()
                if unit.startswith("h"):
                    # The entities gave us the bare number; convert to minutes
                    minutes = int(minutes) * 60
        if not minutes and original:
            m = re.search(r"(\d+)\s*(min(?:ute)?s?|hours?|hr|h)\b", original, re.IGNORECASE)
            if m:
                n = int(m.group(1))
                unit = m.group(2).lower()
                if unit.startswith("h"):
                    n *= 60
                minutes = n
        # Check for "stop" / "disable" / "off" patterns
        if re.search(r"\b(?:stop|disable|turn\s+off|lift|resume|off)\b", original, re.IGNORECASE):
            action = "unsnooze"
            minutes = 0
        elif re.search(r"\b(?:snooze|mute|silence|quiet|dnd|do\s+not\s+disturb|enable\s+dnd)\b", original, re.IGNORECASE):
            action = "snooze"
            if not minutes:
                minutes = 30
        result = execute_snooze(minutes=minutes, action=action)
        if result["ok"]:
            return CommandResult.ok(result["data"]["message"], data=result["data"])
        return CommandResult.fail(result.get("error", "unknown error"))


def get_plugin() -> SnoozePlugin:
    return SnoozePlugin()
