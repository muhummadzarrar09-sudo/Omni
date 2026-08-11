"""
OMNI HARNESS LEADERBOARD (Phase 14, #8b) — prioritize what to improve.

Tracks which harness skills / automation triggers are used most (and how useful
they are), so OMNI can PRIORITIZE which skills to refine and which to retire.

Design (all headless-testable):
  - Leaderboard: a persistent, counted store keyed by artifact/trigger name.
  - record_skill_use(name, ok), record_automation_fire(name, ok): bump counters.
  - Rank by usage + usefulness:
      score = uses * (1.0 if ok else -0.5)   (used-and-working ranks up; used-
      and-failing sinks down for refinement)
  - report(): top skills to keep, bottom skills to refine/retire.

Persistence to data/brain/leaderboard.json.
"""
from __future__ import annotations
import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Leaderboard")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

LEADERBOARD_PATH = DATA_DIR / "brain" / "leaderboard.json"


class Leaderboard:
    """Counts skill/automation usage + usefulness to prioritize refinement."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else LEADERBOARD_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                self._entries = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"leaderboard load failed: {e}")

    def _save(self) -> None:
        with self._lock:
            try:
                self.path.write_text(json.dumps(self._entries, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"leaderboard save failed: {e}")

    def record(self, name: str, kind: str = "skill", ok: bool = True) -> None:
        """Record one usage of a skill/automation."""
        with self._lock:
            e = self._entries.get(name, {"name": name, "kind": kind,
                                         "uses": 0, "ok": 0, "fail": 0,
                                         "last": 0})
            e["uses"] += 1
            if ok:
                e["ok"] += 1
            else:
                e["fail"] += 1
            e["last"] = time.time()
            self._entries[name] = e
            self._save()

    def record_skill_use(self, name: str, ok: bool = True) -> None:
        self.record(name, kind="skill", ok=ok)

    def record_automation_fire(self, name: str, ok: bool = True) -> None:
        self.record(name, kind="automation", ok=ok)

    @staticmethod
    def _score(e: Dict[str, Any]) -> float:
        uses = e.get("uses", 0)
        ok = e.get("ok", 0)
        fail = e.get("fail", 0)
        # used-and-working ranks high; used-and-failing sinks
        return uses * (1.0 if ok >= fail else -0.5)

    def report(self, kind: str = "") -> Dict[str, Any]:
        """Return ranked entries: keep-list (top) + refine-list (bottom/failing)."""
        entries = list(self._entries.values())
        if kind:
            entries = [e for e in entries if e.get("kind") == kind]
        scored = sorted(entries, key=self._score, reverse=True)

        keep = [e for e in scored if e.get("ok", 0) >= e.get("fail", 0) and e.get("uses", 0) > 0][:10]
        refine = [e for e in scored if e.get("fail", 0) > e.get("ok", 0) or e.get("uses", 0) == 0][:10]
        return {
            "total": len(scored),
            "keep": [self._summarize(e) for e in keep],
            "refine": [self._summarize(e) for e in refine],
        }

    @staticmethod
    def _summarize(e: Dict[str, Any]) -> Dict[str, Any]:
        return {"name": e.get("name"), "kind": e.get("kind"), "uses": e.get("uses"),
                "ok": e.get("ok"), "fail": e.get("fail")}

    def entries(self) -> List[Dict[str, Any]]:
        return list(self._entries.values())

    def stats(self) -> Dict[str, Any]:
        return {"entries": len(self._entries), "path": str(self.path)}


def get_leaderboard(**kwargs) -> Leaderboard:
    return Leaderboard(**kwargs)
