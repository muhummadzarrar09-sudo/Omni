"""
OMNI V3 - Session Memory (Phase 1B: It Remembers You)

Tracks every command, every tool call, every interaction.
Generates digests. Enables "what did I do yesterday" / "yesterday I was working on X" / "3 days ago I asked about auth".

Storage:
  data/memory/sessions/{date}/{session_id}.json (one file per session)
  data/memory/digests/{YYYY-MM-DD}.json (one digest per day)

Features:
  - Auto-save every 30 seconds
  - Cross-session search
  - Daily / weekly digests
  - Cleanup of >90 day old sessions
  - Thread-safe
"""
from __future__ import annotations
import json
import time
import threading
import uuid
import re
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import Counter

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SessionMemory")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


@dataclass
class SessionEntry:
    """One session of OMNI usage."""
    id: str
    started_at: float
    ended_at: Optional[float] = None
    duration_min: float = 0.0
    command_count: int = 0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    summary: str = ""
    mood: str = "neutral"  # "focused" | "exploratory" | "frustrated" | "neutral" | "playful"
    project: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DailyDigest:
    """One day's worth of sessions, summarized."""
    date: str  # "2026-07-15"
    session_ids: List[str] = field(default_factory=list)
    total_commands: int = 0
    total_duration_min: float = 0.0
    top_topics: List[Tuple[str, int]] = field(default_factory=list)
    summary: str = ""
    accomplishments: List[str] = field(default_factory=list)
    unfinished: List[str] = field(default_factory=list)
    mood: str = "neutral"
    generated_at: float = 0.0

    def to_dict(self):
        d = asdict(self)
        d["top_topics"] = [list(t) for t in self.top_topics]
        return d

    @classmethod
    def from_dict(cls, d):
        d2 = dict(d)
        d2["top_topics"] = [tuple(t) for t in d.get("top_topics", [])]
        return cls(**{k: v for k, v in d2.items() if k in cls.__dataclass_fields__})


def extract_topics(text: str) -> List[str]:
    """
    Extract topics from text using simple keyword extraction.
    Real LLM-based extraction could be added later.
    """
    if not text:
        return []
    text_lower = text.lower()
    # Common dev/productivity topics
    topic_keywords = {
        "github": ["github", "git", "commit", "pr", "pull request", "repo"],
        "auth": ["auth", "login", "password", "token", "credential"],
        "tests": ["test", "pytest", "unittest", "spec", "tdd"],
        "browser": ["chrome", "firefox", "edge", "browser", "web", "url", "http"],
        "email": ["email", "gmail", "inbox", "mail", "send"],
        "calendar": ["calendar", "meeting", "schedule", "appointment", "event"],
        "files": ["file", "folder", "directory", "save", "load", "read", "write"],
        "music": ["music", "spotify", "song", "play", "audio", "lo-fi", "lofi"],
        "code": ["code", "python", "javascript", "typescript", "compile", "syntax", "function"],
        "vscode": ["vscode", "vs code", "editor", "ide"],
        "calculator": ["calculator", "calc", "math", "tkinter"],
        "smart home": ["lights", "temperature", "thermostat", "smart home", "hue"],
        "memory": ["remember", "memory", "recall", "yesterday", "history"],
    }
    found = []
    for topic, keywords in topic_keywords.items():
        if any(kw in text_lower for kw in keywords):
            found.append(topic)
    # Also extract hashtags or all-caps terms
    hashtags = re.findall(r"#(\w+)", text_lower)
    found.extend(hashtags)
    return list(set(found))[:5]  # cap to 5 topics per command


def detect_mood(command: str, success: bool) -> str:
    """Quick heuristic mood detection."""
    cmd_lower = command.lower()
    if not success:
        return "frustrated"
    if any(w in cmd_lower for w in ["test", "debug", "fix", "error", "bug", "broken"]):
        return "focused"
    if any(w in cmd_lower for w in ["play", "music", "joke", "fun"]):
        return "playful"
    if "?" in command:
        return "exploratory"
    return "neutral"


def detect_project(command: str) -> str:
    """Try to identify which project a command relates to."""
    cmd_lower = command.lower()
    # Look for project names in active projects
    # For now, just heuristic
    if "omni" in cmd_lower or "agni" in cmd_lower:
        return "Omni"
    if "auth" in cmd_lower or "login" in cmd_lower:
        return "auth-system"
    return ""


class SessionMemoryStore:
    """
    The long-term memory of OMNI. Tracks all sessions.
    Singleton, thread-safe, persistent.
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

    def __init__(self, memory_dir: Optional[Path] = None):
        if self._initialized:
            return
        self.memory_dir = memory_dir or (DATA_DIR / "memory")
        self.sessions_dir = self.memory_dir / "sessions"
        self.digests_dir = self.memory_dir / "digests"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.digests_dir.mkdir(parents=True, exist_ok=True)

        self._lock_obj = threading.RLock()
        self._current_session: Optional[SessionEntry] = None
        self._last_save: float = 0.0
        self._save_interval_sec: float = 30.0
        self._in_memory_cache: Dict[str, SessionEntry] = {}
        self._digest_cache: Dict[str, DailyDigest] = {}

        # Load recent sessions into memory (last 7 days for speed)
        self._warm_cache()
        self._initialized = True
        logger.info(f"🧠 SessionMemory initialized (dir: {self.memory_dir})")

    def _warm_cache(self):
        """Load last 7 days of sessions into memory."""
        try:
            cutoff = time.time() - 7 * 86400
            for day_dir in self.sessions_dir.iterdir():
                if not day_dir.is_dir():
                    continue
                for sess_file in day_dir.glob("*.json"):
                    try:
                        data = json.loads(sess_file.read_text(encoding="utf-8"))
                        sess = SessionEntry.from_dict(data)
                        if sess.started_at >= cutoff:
                            self._in_memory_cache[sess.id] = sess
                    except Exception as e:
                        logger.debug(f"Load {sess_file}: {e}")
            logger.info(f"🧠 Warmed cache with {len(self._in_memory_cache)} recent sessions")
        except Exception as e:
            logger.debug(f"Warm cache: {e}")

    def _save_session(self, session: SessionEntry):
        """Atomic save of a session file."""
        date_str = datetime.fromtimestamp(session.started_at).strftime("%Y-%m-%d")
        day_dir = self.sessions_dir / date_str
        day_dir.mkdir(parents=True, exist_ok=True)
        path = day_dir / f"{session.id}.json"
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(day_dir),
                prefix=".sess_",
                suffix=".json.tmp",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise
        except Exception as e:
            logger.error(f"Save session {session.id}: {e}")

    # ===== SESSION LIFECYCLE =====

    def start_session(self) -> SessionEntry:
        """Start a new session. Auto-ends the previous one if active."""
        with self._lock_obj:
            if self._current_session and self._current_session.ended_at is None:
                # End previous
                self._current_session.ended_at = time.time()
                self._current_session.duration_min = (
                    self._current_session.ended_at - self._current_session.started_at
                ) / 60.0
                self._save_session(self._current_session)
                self._in_memory_cache[self._current_session.id] = self._current_session
            sid = f"sess_{uuid.uuid4().hex[:12]}"
            self._current_session = SessionEntry(
                id=sid,
                started_at=time.time(),
            )
            self._last_save = time.time()
            logger.info(f"🧠 Started new session: {sid}")
            return self._current_session

    def get_current_session(self) -> Optional[SessionEntry]:
        """Get the active session, starting one if none exists."""
        with self._lock_obj:
            if self._current_session is None or self._current_session.ended_at is not None:
                self.start_session()
            return self._current_session

    def end_session(self) -> Optional[SessionEntry]:
        """End the current session."""
        with self._lock_obj:
            if self._current_session is None or self._current_session.ended_at is not None:
                return None
            self._current_session.ended_at = time.time()
            self._current_session.duration_min = (
                self._current_session.ended_at - self._current_session.started_at
            ) / 60.0
            self._save_session(self._current_session)
            self._in_memory_cache[self._current_session.id] = self._current_session
            # Generate daily digest
            self._maybe_generate_digest()
            ended = self._current_session
            self._current_session = None
            logger.info(f"🧠 Ended session: {ended.id} ({ended.duration_min:.1f} min, {ended.command_count} cmds)")
            return ended

    # ===== RECORD EVENTS =====

    def record_command(self, command: str) -> None:
        """Record a command in the current session."""
        with self._lock_obj:
            sess = self.get_current_session()
            sess.commands.append(command)
            sess.command_count += 1
            topics = extract_topics(command)
            sess.topics.extend(topics)
            sess.mood = detect_mood(command, True)
            sess.project = detect_project(command) or sess.project
            # Auto-save
            if time.time() - self._last_save > self._save_interval_sec:
                self._save_session(sess)
                self._last_save = time.time()

    def record_tool_call(self, tool: str, args: Dict, result: Any) -> None:
        """Record a tool call in the current session."""
        with self._lock_obj:
            sess = self.get_current_session()
            sess.tool_calls.append({
                "tool": tool,
                "args": str(args)[:200],
                "result": str(result)[:200] if result else "",
                "timestamp": time.time(),
            })
            # Extract topic from args
            if isinstance(args, dict):
                topics = extract_topics(json.dumps(args))
                sess.topics.extend(topics)
            if time.time() - self._last_save > self._save_interval_sec:
                self._save_session(sess)
                self._last_save = time.time()

    def force_save(self) -> None:
        """Force-save the current session."""
        with self._lock_obj:
            if self._current_session and self._current_session.ended_at is None:
                self._save_session(self._current_session)
                self._last_save = time.time()

    # ===== RECALL =====

    def recall_sessions(self, days: int = 7) -> List[SessionEntry]:
        """Get sessions from the last N days, newest first."""
        with self._lock_obj:
            cutoff = time.time() - days * 86400
            sessions = list(self._in_memory_cache.values())
            # Add any from disk that aren't in cache
            for day_dir in self.sessions_dir.iterdir():
                if not day_dir.is_dir():
                    continue
                try:
                    day_date = datetime.strptime(day_dir.name, "%Y-%m-%d").timestamp()
                except ValueError:
                    continue
                if day_date < cutoff - 86400:  # give 1 day buffer
                    continue
                for sess_file in day_dir.glob("*.json"):
                    sid = sess_file.stem
                    if sid not in self._in_memory_cache:
                        try:
                            data = json.loads(sess_file.read_text(encoding="utf-8"))
                            sess = SessionEntry.from_dict(data)
                            self._in_memory_cache[sid] = sess
                        except Exception:
                            continue
            sessions = [s for s in self._in_memory_cache.values() if s.started_at >= cutoff]
            sessions.sort(key=lambda s: -s.started_at)
            return sessions

    def search_history(self, query: str, days: int = 30) -> List[SessionEntry]:
        """Search sessions by topic, command, or project."""
        if not query:
            return []
        query_lower = query.lower()
        sessions = self.recall_sessions(days)
        matches = []
        for s in sessions:
            score = 0
            # Match in commands
            for cmd in s.commands:
                if query_lower in cmd.lower():
                    score += 2
            # Match in topics
            for t in s.topics:
                if query_lower in t.lower():
                    score += 3
            # Match in project
            if query_lower in s.project.lower():
                score += 4
            # Match in summary
            if query_lower in s.summary.lower():
                score += 1
            if score > 0:
                matches.append((score, s))
        matches.sort(key=lambda x: -x[0])
        return [s for _, s in matches]

    def get_last_seen(self) -> Optional[datetime]:
        """Get the timestamp of the last completed session."""
        with self._lock_obj:
            ended = [s for s in self._in_memory_cache.values() if s.ended_at]
            if not ended:
                return None
            latest = max(ended, key=lambda s: s.ended_at)
            return datetime.fromtimestamp(latest.ended_at)

    # ===== DIGESTS =====

    def _digest_file(self, date_str: str) -> Path:
        return self.digests_dir / f"{date_str}.json"

    def _load_digest(self, date_str: str) -> Optional[DailyDigest]:
        """Load a daily digest, from cache or disk."""
        if date_str in self._digest_cache:
            return self._digest_cache[date_str]
        path = self._digest_file(date_str)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            d = DailyDigest.from_dict(data)
            self._digest_cache[date_str] = d
            return d
        except Exception as e:
            logger.debug(f"Load digest {date_str}: {e}")
            return None

    def _save_digest(self, digest: DailyDigest):
        path = self._digest_file(digest.date)
        try:
            fd, tmp = tempfile.mkstemp(dir=str(self.digests_dir), prefix=".digest_", suffix=".json.tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(digest.to_dict(), f, indent=2, ensure_ascii=False)
                os.replace(tmp, path)
            except Exception:
                try: os.unlink(tmp)
                except: pass
                raise
        except Exception as e:
            logger.error(f"Save digest {digest.date}: {e}")

    def get_today_digest(self) -> DailyDigest:
        """Get or generate today's digest."""
        today = datetime.now().strftime("%Y-%m-%d")
        existing = self._load_digest(today)
        if existing:
            return existing
        return self._generate_digest(today)

    def get_digest(self, date_str: str) -> Optional[DailyDigest]:
        """Get digest for a specific date (YYYY-MM-DD)."""
        existing = self._load_digest(date_str)
        if existing:
            return existing
        return self._generate_digest(date_str)

    def get_yesterday_digest(self) -> Optional[DailyDigest]:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return self.get_digest(yesterday)

    def get_weekly_summary(self) -> Dict[str, Any]:
        """Get a 7-day summary."""
        sessions = self.recall_sessions(days=7)
        if not sessions:
            return {
                "days_active": 0,
                "total_commands": 0,
                "total_minutes": 0,
                "top_topics": [],
                "by_day": {},
            }
        all_topics = Counter()
        by_day: Dict[str, Dict] = {}
        total_cmds = 0
        total_min = 0.0
        for s in sessions:
            date_str = datetime.fromtimestamp(s.started_at).strftime("%Y-%m-%d")
            if date_str not in by_day:
                by_day[date_str] = {"sessions": 0, "commands": 0, "minutes": 0.0}
            by_day[date_str]["sessions"] += 1
            by_day[date_str]["commands"] += s.command_count
            by_day[date_str]["minutes"] += s.duration_min
            total_cmds += s.command_count
            total_min += s.duration_min
            for t in s.topics:
                all_topics[t] += 1
        return {
            "days_active": len(by_day),
            "total_commands": total_cmds,
            "total_minutes": round(total_min, 1),
            "top_topics": all_topics.most_common(10),
            "by_day": by_day,
        }

    def _maybe_generate_digest(self):
        """Generate digest for today if it's been a while."""
        today = datetime.now().strftime("%Y-%m-%d")
        existing = self._load_digest(today)
        # Generate if missing or stale (>1 hour)
        if not existing or (time.time() - existing.generated_at) > 3600:
            self._generate_digest(today)

    def _generate_digest(self, date_str: str) -> DailyDigest:
        """Generate a digest for a given date."""
        # Find all sessions for this date
        day_dir = self.sessions_dir / date_str
        sessions = []
        if day_dir.exists():
            for sf in day_dir.glob("*.json"):
                try:
                    data = json.loads(sf.read_text(encoding="utf-8"))
                    sessions.append(SessionEntry.from_dict(data))
                except Exception:
                    continue

        # Aggregate
        all_topics = Counter()
        all_commands: List[str] = []
        all_tools: List[str] = []
        total_cmds = 0
        total_min = 0.0
        for s in sessions:
            all_commands.extend(s.commands)
            all_topics.update(s.topics)
            for tc in s.tool_calls:
                if isinstance(tc, dict) and "tool" in tc:
                    all_tools.append(tc["tool"])
            total_cmds += s.command_count
            total_min += s.duration_min

        # Build summary
        if total_cmds == 0:
            summary = f"No activity on {date_str}."
            mood = "neutral"
        else:
            top = all_topics.most_common(3)
            topic_str = ", ".join(t for t, _ in top) if top else "various tasks"
            summary = f"Used OMNI for {total_cmds} commands across {len(sessions)} sessions ({total_min:.0f} min). Focused on: {topic_str}."
            # Determine mood from sessions
            moods = [s.mood for s in sessions if s.mood]
            mood = max(set(moods), key=moods.count) if moods else "neutral"

        digest = DailyDigest(
            date=date_str,
            session_ids=[s.id for s in sessions],
            total_commands=total_cmds,
            total_duration_min=round(total_min, 1),
            top_topics=all_topics.most_common(10),
            summary=summary,
            accomplishments=[],  # could be LLM-generated
            unfinished=[],
            mood=mood,
            generated_at=time.time(),
        )
        self._save_digest(digest)
        self._digest_cache[date_str] = digest
        logger.info(f"🧠 Generated digest for {date_str}: {summary[:80]}")
        return digest

    # ===== CLEANUP =====

    def cleanup_old_sessions(self, max_age_days: int = 90) -> int:
        """Delete session files older than N days. Returns count deleted."""
        cutoff = time.time() - max_age_days * 86400
        deleted = 0
        for day_dir in self.sessions_dir.iterdir():
            if not day_dir.is_dir():
                continue
            try:
                day_date = datetime.strptime(day_dir.name, "%Y-%m-%d").timestamp()
            except ValueError:
                continue
            if day_date < cutoff:
                for sf in day_dir.glob("*.json"):
                    try:
                        sf.unlink()
                        deleted += 1
                    except Exception:
                        pass
                try:
                    day_dir.rmdir()
                except Exception:
                    pass
        return deleted

    def get_session_stats(self) -> Dict[str, Any]:
        """High-level session statistics for the UI."""
        with self._lock_obj:
            current = self._current_session
            return {
                "active_session_id": current.id if current else None,
                "active_session_commands": current.command_count if current else 0,
                "active_session_duration_min": round((time.time() - current.started_at) / 60, 1) if current else 0,
                "cached_sessions": len(self._in_memory_cache),
                "last_seen": self.get_last_seen().isoformat() if self.get_last_seen() else None,
            }


def get_session_memory() -> SessionMemoryStore:
    """Get the singleton SessionMemoryStore."""
    return SessionMemoryStore()
