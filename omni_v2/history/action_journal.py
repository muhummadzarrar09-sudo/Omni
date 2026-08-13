"""
OMNI ACTION JOURNAL (Phase 15, #2) — session replay + safe undo.

A full, persistent record of every OMNI action (tool calls / file operations /
commands) that you can:
  - REPLAY: re-run a recorded action or sequence.
  - UNDO: reverse a reversible action (e.g. restore a file that was moved /
    renamed / overwritten) — SAFELY.

Design:
  - ActionRecord: {id, ts, action, args, reversible, undo_info, session}.
  - ActionJournal:
      * record(action, args, reversible, undo_info) -> id
      * replay(action_id) / replay_session(session)
      * undo(action_id) — restores the prior state if reversible.
  - UNDO for file ops: before a file is moved/renamed/overwritten, we snapshot
    the original (copy) so undo can restore it. `prepare_undo(op, path)` returns
    undo_info capturing the original location/content.
  - Fully local, headless-testable.

Usage:
    omni history list            # recent actions
    omni history replay <id>     # re-run an action
    omni history undo <id>       # undo a reversible action
"""
from __future__ import annotations
import json
import time
import shutil
import uuid
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ActionJournal")

from omni_v2.core.paths import DATA_DIR

JOURNAL_PATH = DATA_DIR / "brain" / "action_journal.json"
UNDO_DIR = DATA_DIR / "brain" / "undo"


class ActionRecord:
    def __init__(self, action: str, args: Dict[str, Any], reversible: bool = False,
                 undo_info: Optional[Dict[str, Any]] = None, session: str = "default"):
        self.id = uuid.uuid4().hex[:12]
        self.ts = time.time()
        self.action = action
        self.args = args or {}
        self.reversible = reversible
        self.undo_info = undo_info
        self.session = session

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "ts": self.ts, "action": self.action, "args": self.args,
                "reversible": self.reversible, "undo_info": self.undo_info,
                "session": self.session}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ActionRecord":
        r = ActionRecord(d["action"], d.get("args", {}), d.get("reversible", False),
                         d.get("undo_info"), d.get("session", "default"))
        r.id = d["id"]
        r.ts = d.get("ts", time.time())
        return r


class ActionJournal:
    """Records, replays and undoes OMNI actions."""

    def __init__(self, path: Optional[Path] = None, undo_dir: Optional[Path] = None,
                 executor: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
                 undo_executor: Optional[Callable[[Dict[str, Any]], Any]] = None):
        self.path = Path(path) if path else JOURNAL_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.undo_dir = Path(undo_dir) if undo_dir else UNDO_DIR
        self.undo_dir.mkdir(parents=True, exist_ok=True)
        self.executor = executor          # replay runner(action, args) -> result
        self.undo_executor = undo_executor  # undo runner(undo_info) -> result
        self._lock = threading.RLock()
        self._records: List[ActionRecord] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._records = [ActionRecord.from_dict(d) for d in data]
        except Exception as e:
            logger.warning(f"journal load failed: {e}")

    def _save(self) -> None:
        with self._lock:
            try:
                self.path.write_text(
                    json.dumps([r.to_dict() for r in self._records], indent=2),
                    encoding="utf-8")
            except Exception as e:
                logger.warning(f"journal save failed: {e}")

    # -- recording ---------------------------------------------------------
    def record(self, action: str, args: Dict[str, Any], reversible: bool = False,
               undo_info: Optional[Dict[str, Any]] = None,
               session: str = "default") -> str:
        with self._lock:
            r = ActionRecord(action, args, reversible, undo_info, session)
            self._records.append(r)
            self._records = self._records[-2000:]
            self._save()
        return r.id

    def record_with_undo(self, action: str, args: Dict[str, Any],
                         undo_snapshot: Dict[str, Any]) -> str:
        """Record a reversible action with an undo snapshot."""
        return self.record(action, args, reversible=True, undo_info=undo_snapshot)

    # -- undo preparation --------------------------------------------------
    @staticmethod
    def prepare_file_undo(op: str, path: Any, dest: Any = None) -> Dict[str, Any]:
        """Snapshot the original file so undo can restore it.
        op: move | rename | overwrite | delete. Returns undo_info."""
        p = Path(path)
        info = {"op": op, "original_path": str(p)}
        if not p.exists():
            return info  # nothing to snapshot
        # for move/rename, the 'original' IS the current file (dest is the new one)
        if op in ("move", "rename"):
            info["dest_path"] = str(dest) if dest else str(p)
        # copy the original content into the undo dir
        try:
            snap = Path(UNDO_DIR) / f"snap_{uuid.uuid4().hex[:10]}.bak"
            shutil.copy2(p, snap)
            info["snapshot_path"] = str(snap)
            info["had_content"] = True
        except Exception as e:
            info["snapshot_path"] = ""
            info["had_content"] = False
            info["error"] = str(e)
        return info

    # -- undo ----------------------------------------------------------------
    def undo(self, action_id: str) -> Dict[str, Any]:
        """Undo a reversible action. Returns result dict."""
        rec = self.get(action_id)
        if rec is None:
            return {"ok": False, "detail": "no such action"}
        if not rec.reversible or not rec.undo_info:
            return {"ok": False, "detail": "action is not reversible"}
        info = rec.undo_info
        op = info.get("op", "")
        # use the undo_executor if provided, else built-in file undo
        if self.undo_executor is not None:
            try:
                return {"ok": True, "result": self.undo_executor(info)}
            except Exception as e:
                return {"ok": False, "detail": str(e)}
        return self._builtin_file_undo(info)

    def _builtin_file_undo(self, info: Dict[str, Any]) -> Dict[str, Any]:
        op = info.get("op", "")
        orig = info.get("original_path", "")
        snap = info.get("snapshot_path", "")
        try:
            if op == "delete":
                if snap and Path(snap).exists():
                    Path(orig).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(snap, orig)
                    return {"ok": True, "detail": f"restored {orig} from snapshot"}
                return {"ok": False, "detail": "no snapshot to restore"}
            if op in ("move", "rename"):
                dest = info.get("dest_path", "")
                # move back: dest -> original
                if dest and Path(dest).exists():
                    Path(orig).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(dest, orig)
                    return {"ok": True, "detail": f"moved {dest} back to {orig}"}
                # or restore from snapshot
                if snap and Path(snap).exists():
                    Path(orig).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(snap, orig)
                    return {"ok": True, "detail": f"restored {orig} from snapshot"}
                return {"ok": False, "detail": "cannot undo move"}
            if op == "overwrite":
                if snap and Path(snap).exists():
                    Path(orig).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(snap, orig)
                    return {"ok": True, "detail": f"restored original content of {orig}"}
                return {"ok": False, "detail": "no snapshot to restore"}
            return {"ok": False, "detail": f"unsupported undo op '{op}'"}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    # -- replay ---------------------------------------------------------------
    def replay(self, action_id: str) -> Dict[str, Any]:
        rec = self.get(action_id)
        if rec is None:
            return {"ok": False, "detail": "no such action"}
        if self.executor is None:
            return {"ok": True, "detail": f"recorded {rec.action} (no executor)"}
        try:
            result = self.executor(rec.action, rec.args)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "detail": str(e)}

    def replay_session(self, session: str = "default") -> Dict[str, Any]:
        """Replay all actions in a session in order."""
        recs = [r for r in self._records if r.session == session]
        results = [self.replay(r.id) for r in recs]
        ok = all(r["ok"] for r in results)
        return {"ok": ok, "count": len(recs), "results": results}

    # -- introspection -----------------------------------------------------
    def get(self, action_id: str) -> Optional[ActionRecord]:
        return next((r for r in self._records if r.id == action_id), None)

    def list(self, n: int = 50, session: str = "") -> List[Dict[str, Any]]:
        recs = self._records
        if session:
            recs = [r for r in recs if r.session == session]
        return [r.to_dict() for r in recs[-n:][::-1]]

    def stats(self) -> Dict[str, Any]:
        reversible = sum(1 for r in self._records if r.reversible)
        return {"records": len(self._records), "reversible": reversible,
                "path": str(self.path)}


def get_journal(**kwargs) -> ActionJournal:
    return ActionJournal(**kwargs)
