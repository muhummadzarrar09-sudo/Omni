"""
OMNI AUTOMATION TRIGGERS (Phase 13, #5) — external events wake OMNI.

Webhook / schedule / file triggers that fire automations (start a goal, run
research, notify, queue an away task). Fully local, headless-testable.
"""
from omni_v2.automation.triggers import (
    TriggerManager, Automation, make_runner, get_trigger_manager,
    ACTION_GOAL, ACTION_RESEARCH, ACTION_NOTIFY, ACTION_AWAY,
)

__all__ = [
    "TriggerManager", "Automation", "make_runner", "get_trigger_manager",
    "ACTION_GOAL", "ACTION_RESEARCH", "ACTION_NOTIFY", "ACTION_AWAY",
]
