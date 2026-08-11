"""
OMNI WAKE ROUTINE (Phase 14, #7) — the "Good morning Zarrar" scripted flow.

Ties identity + briefing + voice + guardian into one morning moment. When
triggered it:
  1. Greets the user by name (identity core).
  2. Pulls today's events (calendar) + open goals.
  3. Builds a morning briefing (reusing the MorningBriefing agent).
  4. Optionally SPEAKS the greeting via TTS and/or PUSHES it via messenger.
  5. Warms up the guardian.

Fully local + headless-testable (fakes for calendar/identity/briefing/tts).
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("WakeRoutine")


class WakeRoutine:
    """Runs the scripted morning flow."""

    def __init__(
        self,
        identity=None,        # IdentityCore (name)
        calendar=None,        # CalendarParser (today's events)
        briefing=None,        # MorningBriefing (build + deliver)
        tts=None,             # speak(text) -> bool (optional)
        messenger=None,       # send_text(text) (optional)
        guardian=None,        # Guardian (warm up, optional)
    ):
        self.identity = identity
        self.calendar = calendar
        self.briefing = briefing
        self.tts = tts
        self.messenger = messenger
        self.guardian = guardian

    def user_name(self) -> str:
        if self.identity is not None:
            try:
                return self.identity.user.name or ""
            except Exception:
                return ""
        return ""

    def build_greeting(self) -> str:
        """Compose the spoken/pushed morning greeting."""
        name = self.user_name()
        now = datetime.now()
        hour = now.hour
        if hour < 12:
            greet = "Good morning"
        elif hour < 17:
            greet = "Good afternoon"
        else:
            greet = "Good evening"
        base = f"{greet}{f', {name}' if name else ''}."
        lines = [base]

        # today's events
        if self.calendar is not None:
            try:
                events = self.calendar.events_today()
                if events:
                    ev = events[0]
                    lines.append(f"Your next event is {ev['summary']} at {ev['start']}.")
            except Exception as e:
                logger.warning(f"wake calendar: {e}")
        # open goals
        if self.briefing is not None and hasattr(self.briefing, "goals") and self.briefing.goals:
            try:
                goals = self.briefing.goals.active_goals()
                if goals:
                    lines.append(f"You have {len(goals)} active goal(s).")
            except Exception:
                pass
        return " ".join(lines)

    def run(self, speak: bool = True, push: bool = True) -> Dict[str, Any]:
        """Execute the wake routine. Returns a result dict."""
        greeting = self.build_greeting()
        result = {"greeting": greeting, "spoken": False, "pushed": False}

        # build + optionally deliver the full briefing
        briefing_md = ""
        if self.briefing is not None:
            try:
                data = self.briefing.build(research_topic="")
                briefing_md = data.get("markdown", "")
            except Exception as e:
                logger.warning(f"wake briefing build: {e}")

        if speak and self.tts is not None:
            try:
                self.tts.speak(greeting)
                result["spoken"] = True
            except Exception as e:
                logger.warning(f"wake tts: {e}")

        if push and self.messenger is not None:
            try:
                self.messenger.send_text(greeting + "\n\n" + (briefing_md[:1500] if briefing_md else ""))
                result["pushed"] = True
            except Exception as e:
                logger.warning(f"wake push: {e}")

        if self.guardian is not None:
            try:
                if not self.guardian.running:
                    self.guardian.start()
                result["guardian_warmed"] = True
            except Exception:
                result["guardian_warmed"] = False

        logger.info(f"🌅 wake routine: {greeting[:60]}")
        return result

    def status(self) -> Dict[str, Any]:
        return {
            "has_identity": self.identity is not None,
            "has_calendar": self.calendar is not None,
            "has_briefing": self.briefing is not None,
            "has_tts": self.tts is not None,
            "has_messenger": self.messenger is not None,
            "user_name": self.user_name(),
        }


def get_wake_routine(**kwargs) -> WakeRoutine:
    return WakeRoutine(**kwargs)
