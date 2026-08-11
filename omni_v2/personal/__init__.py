"""
OMNI PERSONAL CONTEXT (Phase 14, #5) — local calendar + contacts.

Makes OMNI aware of your real schedule and people. Headless-testable.
"""
from omni_v2.personal.calendar_contacts import (
    CalendarParser, ContactStore, get_calendar, get_contacts,
)

__all__ = ["CalendarParser", "ContactStore", "get_calendar", "get_contacts"]
