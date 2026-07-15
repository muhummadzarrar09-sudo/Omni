"""
OMNI V3 - PROACTIVE AGENT V2 - The "Actually Does Stuff" Engine

This is what makes OMNI an AGI, not a chatbot.
Monitors the user's context and INTERRUPTS with helpful, personalized suggestions.

Triggers:
  - Time-of-day patterns (morning routine, lunch, end of day)
  - Calendar awareness (meetings coming up)
  - Inbox awareness (unread important emails)
  - Activity patterns (coding for 2hrs+ → break reminder)
  - System health (battery low, disk full, high CPU)
  - Code status (test failures, git dirty)
  - Idle time (haven't said anything in 30 min → check in)
  - Local context (weather, news)

The brain doesn't wait to be asked. It SEES you need help and offers.
"""
from __future__ import annotations
import time
import threading
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ProactiveV2")


@dataclass
class ProactiveSuggestion:
    """A suggestion the AGI makes to the user."""
    id: str
    title: str           # "Meeting in 5 min"
    body: str            # "Your standup with Sarah starts at 2pm. Want me to prep the notes?"
    priority: int        # 0=info, 1=useful, 2=urgent
    category: str        # "calendar", "health", "code", "inbox", "system", "time"
    actions: List[Dict[str, str]] = field(default_factory=list)  # [{"label": "Open", "command": "..."}]
    timestamp: float = field(default_factory=time.time)
    dismissed: bool = False
    acted_on: bool = False

    def to_dict(self):
        return asdict(self)


class ProactiveEngineV2:
    """
    The brain that watches. Uses context signals to generate helpful interruptions.
    Singleton. Thread-safe.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, interval_sec: float = 60.0, data_dir: Optional[Path] = None):
        if self._initialized:
            return
        self.interval_sec = interval_sec
        self.data_dir = data_dir or (Path.cwd() / "data" / "proactive")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.suggestions_file = self.data_dir / "suggestions.json"

        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._suggestions: List[ProactiveSuggestion] = []
        self._context: Dict[str, Any] = {}
        self._last_user_activity: float = time.time()
        self._last_user_message: str = ""
        self._coding_start_time: Optional[float] = None
        self._last_suggestion_at: float = 0.0
        self._daily_suggestion_count: int = 0
        self._last_reset_date: str = datetime.now().strftime("%Y-%m-%d")

        # Load persistent state
        self._load_state()

        # Hooks
        self.on_suggestion: Optional[Callable[[ProactiveSuggestion], None]] = None
        self.brain_ref = None  # set externally to the LLM brain

        self._initialized = True
        logger.info(f"✨ ProactiveEngine V2 initialized (interval: {interval_sec}s, data: {self.data_dir})")

    def set_brain(self, brain):
        """Wire the LLM brain so we can rephrase suggestions naturally."""
        self.brain_ref = brain

    def record_user_activity(self, text: str = ""):
        """Call this whenever the user says or does something."""
        self._last_user_activity = time.time()
        if text:
            self._last_user_message = text
        # Reset coding session if they were just coding
        if any(w in text.lower() for w in ["code", "build", "fix", "test", "debug", "compile"]):
            if self._coding_start_time is None:
                self._coding_start_time = time.time()

    def record_idle(self):
        """Call when user hasn't done anything for a while."""
        pass  # we use _last_user_activity directly

    def update_context(self, **kwargs):
        """Push context signals (screen, calendar, etc)."""
        self._context.update(kwargs)

    def _load_state(self):
        try:
            if self.suggestions_file.exists():
                with open(self.suggestions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._suggestions = [ProactiveSuggestion(**s) for s in data.get("suggestions", [])]
                    self._daily_suggestion_count = data.get("daily_count", 0)
                    self._last_reset_date = data.get("reset_date", self._last_reset_date)
        except Exception as e:
            logger.debug(f"Load proactive state: {e}")

    def _save_state(self):
        try:
            # Prune dismissed/old suggestions (> 7 days)
            cutoff = time.time() - 7 * 86400
            self._suggestions = [s for s in self._suggestions if s.timestamp > cutoff]
            data = {
                "suggestions": [s.to_dict() for s in self._suggestions[-50:]],
                "daily_count": self._daily_suggestion_count,
                "reset_date": self._last_reset_date,
            }
            with open(self.suggestions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Save proactive state: {e}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="ProactiveV2", daemon=True)
        self._thread.start()
        logger.info("🟢 ProactiveEngine V2 daemon started")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._save_state()
        logger.info("🔴 ProactiveEngine V2 daemon stopped")

    def _loop(self):
        # Reset daily counter if new day
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._last_reset_date:
            self._daily_suggestion_count = 0
            self._last_reset_date = today
            logger.info(f"🔄 Proactive: new day, reset daily counter")

        while self._running:
            try:
                time.sleep(self.interval_sec)
                if not self._running:
                    break
                self._tick()
            except Exception as e:
                logger.debug(f"Proactive tick error: {e}")

    def _tick(self):
        """One pass of proactive monitoring."""
        now = time.time()
        # Cap to max 1 suggestion per 5 min, max 20/day
        if now - self._last_suggestion_at < 300:
            return
        if self._daily_suggestion_count >= 20:
            return

        # Run all rules; first hit wins
        rules = [
            self._check_meeting_soon,
            self._check_coding_too_long,
            self._check_idle_too_long,
            self._check_morning_routine,
            self._check_welcome_back,
            self._check_end_of_day,
            self._check_test_failures,
            self._check_unread_important,
            self._check_system_health,
            self._check_weekly_review,
        ]

        for rule in rules:
            try:
                suggestion = rule()
                if suggestion and not self._is_dismissed(suggestion.id):
                    self._emit(suggestion)
                    return
            except Exception as e:
                logger.debug(f"Rule {rule.__name__} error: {e}")

    def _is_dismissed(self, sid: str) -> bool:
        return any(s.id == sid and s.dismissed for s in self._suggestions)

    def _emit(self, suggestion: ProactiveSuggestion):
        self._suggestions.append(suggestion)
        self._last_suggestion_at = time.time()
        self._daily_suggestion_count += 1
        logger.info(f"✨ Proactive: [{suggestion.priority}] {suggestion.title} | {suggestion.body[:80]}")
        if self.on_suggestion:
            try:
                self.on_suggestion(suggestion)
            except Exception:
                pass
        self._save_state()

    # ===== RULES =====

    def _check_meeting_soon(self) -> Optional[ProactiveSuggestion]:
        """Calendar-aware: meeting in <10 min"""
        calendar = self._context.get("calendar")
        if not calendar:
            return None
        try:
            next_event = calendar.get("next_event")
            if not next_event:
                return None
            start_time = next_event.get("start_timestamp", 0)
            now = time.time()
            minutes_until = (start_time - now) / 60
            if 0 < minutes_until <= 10:
                return ProactiveSuggestion(
                    id=f"meeting_{int(start_time)}",
                    title=f"Meeting in {int(minutes_until)} min",
                    body=f"{next_event.get('title', 'Untitled meeting')} starts at {next_event.get('start_time', '')}. Want me to prep notes or open the link?",
                    priority=2,
                    category="calendar",
                    actions=[
                        {"label": "Open meeting", "command": f"open {next_event.get('url', 'calendar')}"},
                        {"label": "Prep notes", "command": "open my notes for this meeting"},
                        {"label": "Snooze 5 min", "command": "_snooze"},
                    ],
                )
        except Exception as e:
            logger.debug(f"meeting check: {e}")
        return None

    def _check_coding_too_long(self) -> Optional[ProactiveSuggestion]:
        """2+ hours of continuous coding → break reminder"""
        if self._coding_start_time is None:
            return None
        elapsed = time.time() - self._coding_start_time
        if elapsed < 2 * 3600:  # 2 hours
            return None
        if elapsed > 4 * 3600:  # give up after 4hrs
            return None
        # Only suggest once per session
        sid = f"break_{int(self._coding_start_time)}"
        if self._is_dismissed(sid):
            return None
        hours = int(elapsed / 3600)
        return ProactiveSuggestion(
            id=sid,
            title=f"You've been coding for {hours}+ hours",
            body="Time for a break. Want me to lock the screen for 15 min, or queue up a focus playlist?",
            priority=1,
            category="health",
            actions=[
                {"label": "Lock 15 min", "command": "_lock 15"},
                {"label": "Play lo-fi", "command": "play lo-fi music"},
                {"label": "Just a stretch", "command": "_ack"},
            ],
        )

    def _check_idle_too_long(self) -> Optional[ProactiveSuggestion]:
        """30+ min of no activity → check in"""
        idle_sec = time.time() - self._last_user_activity
        if idle_sec < 30 * 60:
            return None
        if idle_sec > 4 * 3600:
            return None  # probably gone home
        sid = f"idle_{int(self._last_user_activity)}"
        if self._is_dismissed(sid):
            return None
        mins = int(idle_sec / 60)
        return ProactiveSuggestion(
            id=sid,
            title=f"You've been away {mins} min",
            body="Still there? Want me to summarize what you missed, or just stand by?",
            priority=0,
            category="time",
            actions=[
                {"label": "Summarize", "command": "what did I miss"},
                {"label": "Stand by", "command": "_ack"},
            ],
        )

    def _check_morning_routine(self) -> Optional[ProactiveSuggestion]:
        """Between 8-10am, greet with personalized day overview."""
        now = datetime.now()
        if not (8 <= now.hour < 10):
            return None
        sid = f"morning_{now.strftime('%Y%m%d')}"
        if self._is_dismissed(sid):
            return None
        # Use profile + session memory for personalization (Phase 1)
        name = ""
        yesterday_summary = ""
        try:
            from omni_v2.agents.user_profile import get_user_profile
            profile = get_user_profile()
            name = profile.greeting_name()
        except Exception:
            pass
        try:
            from omni_v2.memory.session_memory import get_session_memory
            sess_mem = get_session_memory()
            yesterday = sess_mem.get_yesterday_digest()
            if yesterday and yesterday.total_commands > 0:
                yesterday_summary = f" Yesterday you were working on {yesterday.top_topics[0][0] if yesterday.top_topics else 'stuff'}."
        except Exception:
            pass
        name_part = f" {name}" if name else ""
        body = f"It's {now.strftime('%A, %B %d')}.{yesterday_summary} Want me to brief you on today's calendar, weather, and top emails?"
        return ProactiveSuggestion(
            id=sid,
            title=f"Good morning{name_part} ☀️",
            body=body,
            priority=1,
            category="time",
            actions=[
                {"label": "Brief me", "command": "brief my day"},
                {"label": "What did I do yesterday?", "command": "what did I do yesterday"},
                {"label": "Skip", "command": "_ack"},
            ],
        )

    def _check_welcome_back(self) -> Optional[ProactiveSuggestion]:
        """User returning after 1+ day absence"""
        try:
            from omni_v2.memory.session_memory import get_session_memory
            sess_mem = get_session_memory()
            last_seen = sess_mem.get_last_seen()
            if not last_seen:
                return None
            now = datetime.now()
            hours_away = (now - last_seen).total_seconds() / 3600
            if hours_away < 18:  # less than 18 hours, normal daily return
                return None
            if hours_away > 24 * 7:  # more than a week, not relevant
                return None
            # Get yesterday's digest
            yesterday = sess_mem.get_yesterday_digest()
            if not yesterday or yesterday.total_commands == 0:
                return None
            name = ""
            try:
                from omni_v2.agents.user_profile import get_user_profile
                name = get_user_profile().greeting_name()
            except Exception:
                pass
            name_part = f" {name}" if name else ""
            top_topic = yesterday.top_topics[0][0] if yesterday.top_topics else "your project"
            sid = f"welcome_back_{now.strftime('%Y%m%d')}"
            if self._is_dismissed(sid):
                return None
            return ProactiveSuggestion(
                id=sid,
                title=f"Welcome back{name_part}!",
                body=f"Last time you were working on {top_topic}. {yesterday.summary[:200]}",
                priority=1,
                category="time",
                actions=[
                    {"label": "Catch me up", "command": "what did I miss"},
                    {"label": f"Continue {top_topic}", "command": f"continue working on {top_topic}"},
                    {"label": "Skip", "command": "_ack"},
                ],
            )
        except Exception as e:
            logger.debug(f"welcome back check: {e}")
            return None

    def _check_end_of_day(self) -> Optional[ProactiveSuggestion]:
        """Around 5-7pm, wrap-up prompt with personalization."""
        now = datetime.now()
        if not (17 <= now.hour < 19):
            return None
        sid = f"eod_{now.strftime('%Y%m%d')}"
        if self._is_dismissed(sid):
            return None
        # Get today's stats for personalization
        today_stats = ""
        try:
            from omni_v2.memory.session_memory import get_session_memory
            sess_mem = get_session_memory()
            today = sess_mem.get_today_digest()
            if today and today.total_commands > 0:
                top_topic = today.top_topics[0][0] if today.top_topics else "various things"
                today_stats = f" Today: {today.total_commands} commands, mostly {top_topic}."
        except Exception:
            pass
        name = ""
        try:
            from omni_v2.agents.user_profile import get_user_profile
            name = get_user_profile().greeting_name()
        except Exception:
            pass
        name_part = f" {name}" if name else ""
        return ProactiveSuggestion(
            id=sid,
            title=f"End of day{name_part}",
            body=f"{today_stats} Want me to commit your work, close your apps, and prep tomorrow's agenda?",
            priority=1,
            category="time",
            actions=[
                {"label": "Wrap it up", "command": "wrap up my day"},
                {"label": "Daily review", "command": "what did I do today"},
                {"label": "Keep going", "command": "_ack"},
            ],
        )

    def _check_test_failures(self) -> Optional[ProactiveSuggestion]:
        """Code-aware: tests failed recently"""
        code_ctx = self._context.get("code")
        if not code_ctx:
            return None
        if code_ctx.get("last_test_status") != "failed":
            return None
        sid = f"tests_failed_{code_ctx.get('last_test_run', 0)}"
        if self._is_dismissed(sid):
            return None
        return ProactiveSuggestion(
            id=sid,
            title=f"Tests failed: {code_ctx.get('failed_count', '?')} failures",
            body=f"Last test run at {code_ctx.get('last_test_time', 'just now')}. Want me to investigate the failures?",
            priority=2,
            category="code",
            actions=[
                {"label": "Investigate", "command": "check why tests failed"},
                {"label": "Show log", "command": "show test output"},
                {"label": "Skip", "command": "_ack"},
            ],
        )

    def _check_unread_important(self) -> Optional[ProactiveSuggestion]:
        """Inbox-aware: urgent unread emails"""
        inbox = self._context.get("inbox")
        if not inbox:
            return None
        urgent = inbox.get("urgent_unread", 0)
        if urgent < 3:
            return None
        sid = f"inbox_urgent_{int(time.time() / 3600)}"
        if self._is_dismissed(sid):
            return None
        return ProactiveSuggestion(
            id=sid,
            title=f"{urgent} urgent emails",
            body="You have unread emails marked urgent. Want me to summarize them?",
            priority=1,
            category="inbox",
            actions=[
                {"label": "Summarize", "command": "summarize my urgent emails"},
                {"label": "Open inbox", "command": "open gmail"},
                {"label": "Later", "command": "_ack"},
            ],
        )

    def _check_system_health(self) -> Optional[ProactiveSuggestion]:
        """System-aware: battery, disk, CPU"""
        sys_ctx = self._context.get("system")
        if not sys_ctx:
            return None
        # Battery low
        battery = sys_ctx.get("battery_percent")
        if battery is not None and battery < 15 and not sys_ctx.get("plugged_in", True):
            sid = f"battery_low_{int(time.time()/1800)}"
            if not self._is_dismissed(sid):
                return ProactiveSuggestion(
                    id=sid,
                    title=f"Battery at {battery}%",
                    body="You're running low. Want me to dim the screen and close heavy apps to save power?",
                    priority=2,
                    category="system",
                    actions=[
                        {"label": "Battery saver", "command": "enable battery saver"},
                        {"label": "Find charger", "command": "find nearest charger"},
                        {"label": "Ignore", "command": "_ack"},
                    ],
                )
        # Disk full
        disk_free = sys_ctx.get("disk_free_gb")
        if disk_free is not None and disk_free < 5:
            sid = f"disk_full_{int(time.time()/1800)}"
            if not self._is_dismissed(sid):
                return ProactiveSuggestion(
                    id=sid,
                    title=f"Only {disk_free:.1f}GB free",
                    body="Disk is almost full. Want me to clean up temp files and old downloads?",
                    priority=2,
                    category="system",
                    actions=[
                        {"label": "Clean up", "command": "clean temp files"},
                        {"label": "Show big files", "command": "show me what's using space"},
                        {"label": "Ignore", "command": "_ack"},
                    ],
                )
        return None

    def _check_weekly_review(self) -> Optional[ProactiveSuggestion]:
        """Friday afternoon: weekly review prompt"""
        now = datetime.now()
        if now.weekday() != 4:  # Friday
            return None
        if not (15 <= now.hour < 17):
            return None
        sid = f"weekly_review_{now.strftime('%Y%W')}"
        if self._is_dismissed(sid):
            return None
        return ProactiveSuggestion(
            id=sid,
            title="Friday afternoon",
            body="End of week. Want me to summarize what you accomplished and plan next week?",
            priority=0,
            category="time",
            actions=[
                {"label": "Weekly review", "command": "give me a weekly review"},
                {"label": "Skip", "command": "_ack"},
            ],
        )

    # ===== PUBLIC API =====

    def get_pending_suggestions(self, max_n: int = 5) -> List[Dict[str, Any]]:
        """Get the most recent non-dismissed suggestions for the UI."""
        pending = [s for s in self._suggestions if not s.dismissed and not s.acted_on]
        pending.sort(key=lambda s: (-s.priority, -s.timestamp))
        return [s.to_dict() for s in pending[:max_n]]

    def dismiss(self, suggestion_id: str):
        """Mark a suggestion as dismissed."""
        for s in self._suggestions:
            if s.id == suggestion_id:
                s.dismissed = True
                self._save_state()
                return

    def mark_acted_on(self, suggestion_id: str):
        """Mark a suggestion as acted on (user clicked an action)."""
        for s in self._suggestions:
            if s.id == suggestion_id:
                s.acted_on = True
                self._save_state()
                return

    def force_suggestion(self, title: str, body: str, priority: int = 1, category: str = "manual", actions: Optional[List[Dict]] = None) -> ProactiveSuggestion:
        """Manually trigger a suggestion (for testing or external triggers)."""
        s = ProactiveSuggestion(
            id=f"manual_{int(time.time()*1000)}",
            title=title,
            body=body,
            priority=priority,
            category=category,
            actions=actions or [],
        )
        self._emit(s)
        return s


def get_proactive_engine(interval_sec: float = 60.0) -> ProactiveEngineV2:
    return ProactiveEngineV2(interval_sec=interval_sec)
