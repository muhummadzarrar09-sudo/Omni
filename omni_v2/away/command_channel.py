"""
OMNI REMOTE COMMAND CHANNEL - talk to OMNI from your phone while away.

Polls the configured messenger for inbound messages (Telegram bot by default)
and routes them:
  * /research <topic>   -> submit a research task to the away queue
  * /digest             -> build & send a digest report
  * /status             -> reply with away-agent + KB stats
  * /help               -> list available commands
  * anything else       -> if a brain is attached, ask the brain; else ack.

The router is pure/testable (no network): `route(message, ...)` returns a
reply string. The `CommandPoller` wraps it in a loop that calls
messenger.poll_commands().

Incoming commands are also written to data/messenger/inbox/ so they're always
auditable locally even if no messenger replies.
"""
from __future__ import annotations
import time
import json
import re
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("CommandChannel")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


class CommandRouter:
    """Pure command routing logic (fully testable without network)."""

    def __init__(self, away_agent=None, brain=None, kb=None):
        self.away_agent = away_agent
        self.brain = brain
        self.kb = kb

    def route(self, text: str, sender: str = "") -> str:
        text = (text or "").strip()
        if not text:
            return ""
        low = text.lower()

        if low.startswith(("/help", "help", "commands")):
            return self._help()
        if low.startswith(("/status", "status")):
            return self._status()
        if low.startswith(("/digest", "digest")):
            return self._digest()
        if low.startswith(("/research", "research")):
            return self._research(text)
        if low.startswith(("/kb ", "kb ")):
            return self._kb_query(text)
        return self._fallback(text)

    # -- handlers ---------------------------------------------------------
    def _help(self) -> str:
        return (
            "OMNI remote commands:\n"
            "/research <topic>\n"
            "/digest\n"
            "/status\n"
            "/kb <question>\n"
            "or just ask me anything."
        )

    def _status(self) -> str:
        lines = []
        if self.away_agent is not None:
            st = self.away_agent.stats()
            lines.append(f"Away mode: {'ON' if st['active'] else 'OFF'}")
            lines.append(f"Queue: {st['tasks_total']} task(s) {st['tasks_by_status']}")
        if self.kb is not None:
            lines.append(f"KB memory: {self.kb.memory.stats().get('long_term_items', 0)} items")
        return "\n".join(lines) if lines else "No status available."

    def _digest(self) -> str:
        if self.away_agent is None:
            return "Away agent not available."
        task = self.away_agent.submit("digest", "remote_request")
        return f"Digest queued (task {task.id}). I'll send it shortly."

    def _research(self, text: str) -> str:
        topic = re.sub(r"^/research\b", "", text, flags=re.IGNORECASE).strip()
        topic = topic.strip(": ")
        if not topic:
            return "Usage: /research <topic> — e.g. /research quantum computing for beginners"
        if self.away_agent is None:
            return "Away agent not available."
        task = self.away_agent.submit("research", topic)
        return f"Research queued (task {task.id}): \"{topic}\". I'll report back when done."

    def _kb_query(self, text: str) -> str:
        q = re.sub(r"^/kb\b", "", text, flags=re.IGNORECASE).strip().strip(": ")
        if self.kb is None:
            return "Knowledge base not available."
        res = self.kb.query(q, k=2)
        if res["hit_count"] == 0:
            return f"No knowledge on \"{q}\" yet."
        top = res["hits"][0]
        snippet = top["text"][:180]
        return f"KB: {snippet}…"

    def _fallback(self, text: str) -> str:
        if self.brain is not None:
            try:
                resp = self.brain.think(text)
                return resp.text or "Done."
            except Exception as e:
                return f"Could not process that remotely ({e})."
        return f"Received: \"{text}\". (No brain attached — queued for review.)"

    # -- persistence of inbound -------------------------------------------------
    def _record_inbound(self, text: str, sender: str) -> None:
        try:
            inbox = DATA_DIR / "messenger" / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            (inbox / f"{int(time.time()*1000)}.json").write_text(
                json.dumps({"sender": sender, "text": text, "ts": time.time()}),
                encoding="utf-8",
            )
        except Exception:
            pass


class CommandPoller:
    """Background loop: poll messenger, route commands, reply."""

    def __init__(self, messenger, router: CommandRouter, interval: float = 5.0):
        self.messenger = messenger
        self.router = router
        self.interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="omni-cmd-poll")
        self._thread.start()
        logger.info("Remote command poller started")

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                for cmd in self.messenger.poll_commands():
                    reply = self.router.route(cmd.get("text", ""), cmd.get("sender", ""))
                    self.router._record_inbound(cmd.get("text", ""), cmd.get("sender", ""))
                    if reply:
                        try:
                            self.messenger.send_text(reply)
                        except Exception as e:
                            logger.warning(f"Command reply send failed: {e}")
            except Exception as e:
                logger.warning(f"Command poll loop error: {e}")
            self._stop.wait(self.interval)
