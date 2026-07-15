"""
OMNI V3 - Stats Engine (Phase 3C: The Flex)

Aggregates stats for the UI / judges:
  - Total commands (lifetime)
  - Commands today / week
  - Tool usage breakdown
  - Success rate
  - Avg response time
  - Peak hours (bar chart data)
  - Time saved estimate

Storage: data/stats/aggregated.json (computed from session memory + user profile)
"""
from __future__ import annotations
import json
import time
import threading
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from collections import Counter
from datetime import datetime, timedelta

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Stats")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


class StatsEngine:
    """
    The butler's stats dashboard. Pulls from user profile + session memory.
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

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info("📊 StatsEngine initialized")

    def get_lifetime_stats(self) -> Dict[str, Any]:
        """Get lifetime stats."""
        try:
            from omni_v2.agents.user_profile import get_user_profile
            profile = get_user_profile()
            ps = profile.get_stats()
        except Exception:
            ps = {}
        try:
            from omni_v2.memory.session_memory import get_session_memory
            mem = get_session_memory()
            sessions = mem.recall_sessions(days=365)
        except Exception:
            sessions = []
        total_commands = sum(s.command_count for s in sessions) or ps.get("total_commands", 0)
        total_tool_calls = sum(len(s.tool_calls) for s in sessions)
        return {
            "total_commands": total_commands,
            "total_sessions": len(sessions),
            "total_tool_calls": total_tool_calls,
            "avg_commands_per_session": round(total_commands / max(1, len(sessions)), 1),
            "member_since": ps.get("member_since"),
            "days_using_omni": ps.get("days_using_omni", 0),
            "longest_session_min": ps.get("longest_session_min", 0),
        }

    def get_today_stats(self) -> Dict[str, Any]:
        """Get today's stats."""
        try:
            from omni_v2.memory.session_memory import get_session_memory
            mem = get_session_memory()
            today = mem.get_today_digest()
            return {
                "date": today.date,
                "total_commands": today.total_commands,
                "total_duration_min": today.total_duration_min,
                "top_topics": today.top_topics[:5],
                "mood": today.mood,
            }
        except Exception as e:
            logger.debug(f"Today stats: {e}")
            return {"date": datetime.now().strftime("%Y-%m-%d"), "total_commands": 0}

    def get_tool_breakdown(self, days: int = 30) -> List[Tuple[str, int]]:
        """Get tool usage breakdown, sorted by count."""
        try:
            from omni_v2.memory.session_memory import get_session_memory
            mem = get_session_memory()
            sessions = mem.recall_sessions(days=days)
            counts = Counter()
            for s in sessions:
                for tc in s.tool_calls:
                    if isinstance(tc, dict) and "tool" in tc:
                        counts[tc["tool"]] += 1
            return counts.most_common(20)
        except Exception as e:
            logger.debug(f"Tool breakdown: {e}")
            return []

    def get_peak_hours(self, days: int = 7) -> Dict[int, int]:
        """Get activity by hour of day (0-23)."""
        try:
            from omni_v2.memory.session_memory import get_session_memory
            mem = get_session_memory()
            sessions = mem.recall_sessions(days=days)
            by_hour: Dict[int, int] = {h: 0 for h in range(24)}
            for s in sessions:
                hour = datetime.fromtimestamp(s.started_at).hour
                by_hour[hour] += s.command_count
            return by_hour
        except Exception as e:
            logger.debug(f"Peak hours: {e}")
            return {h: 0 for h in range(24)}

    def get_weekly_chart(self, days: int = 7) -> Dict[str, int]:
        """Get commands per day for the last N days."""
        try:
            from omni_v2.memory.session_memory import get_session_memory
            mem = get_session_memory()
            summary = mem.get_weekly_summary()
            return summary.get("by_day", {})
        except Exception as e:
            logger.debug(f"Weekly chart: {e}")
            return {}

    def estimate_time_saved(self) -> Dict[str, Any]:
        """
        Estimate time saved by using OMNI.
        Assumes 30 sec saved per command (vs typing it manually).
        """
        try:
            lifetime = self.get_lifetime_stats()
            total = lifetime.get("total_commands", 0)
            sec_saved = total * 30
            return {
                "commands": total,
                "seconds_saved": sec_saved,
                "minutes_saved": round(sec_saved / 60, 1),
                "hours_saved": round(sec_saved / 3600, 1),
                "human_readable": self._humanize_time(sec_saved),
            }
        except Exception as e:
            logger.debug(f"Time saved: {e}")
            return {"commands": 0, "seconds_saved": 0, "human_readable": "0s"}

    def _humanize_time(self, seconds: int) -> str:
        """Format seconds into a human-readable string."""
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def get_full_dashboard(self) -> Dict[str, Any]:
        """Get everything for the stats UI."""
        return {
            "lifetime": self.get_lifetime_stats(),
            "today": self.get_today_stats(),
            "tool_breakdown": [
                {"tool": t, "count": c} for t, c in self.get_tool_breakdown()
            ],
            "peak_hours": self.get_peak_hours(),
            "weekly_chart": self.get_weekly_chart(),
            "time_saved": self.estimate_time_saved(),
        }


def get_stats_engine() -> StatsEngine:
    return StatsEngine()
