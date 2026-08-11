"""
OMNI MESH (Phase 16, #3) — multi-machine state sync.

Reconciles OMNI's state (brain, harness, KB, goals, identity, vault meta,
schedules, automations, journal) between TWO machines — e.g. your laptop and the
DGX Station — so both stay in sync without losing work.

Design:
  - export_state() -> dict snapshot of all relevant state.
  - import_state(snapshot) -> restore into this machine.
  - sync_to_machine(snapshot) / sync_from_machine(snapshot): reconcile with
    conflict resolution (newer timestamp wins per collection; collections merge).
  - Collection-aware: goals/harness/identity/journal have per-record timestamps,
    so merge keeps the newest of each.

Fully local + headless-testable: works on the local data dir with fakes.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Mesh")

from omni_v2.core.paths import DATA_DIR


class MeshSync:
    """Exports, imports and reconciles OMNI state across machines."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR

    # -- helpers -----------------------------------------------------------
    def _read_json(self, rel: str) -> Optional[Dict[str, Any]]:
        p = self.data_dir / rel
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_json(self, rel: str, data: Any) -> None:
        p = self.data_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # -- export ------------------------------------------------------------
    def export_state(self) -> Dict[str, Any]:
        """Export the whole OMNI state as a portable dict."""
        state = {"meta": {"exported_at": time.time(), "version": "omni-v3"},
                 "collections": {}}
        # dict-based collections (keyed by id with timestamps)
        for rel, label in [
            ("brain/goals.json", "goals"),
            ("brain/harness/index.json", "harness"),
            ("brain/identity.json", "identity"),
            ("brain/triggers.json", "automations"),
            ("brain/recurring.json", "schedules"),
            ("brain/action_journal.json", "journal"),
            ("brain/leaderboard.json", "leaderboard"),
        ]:
            data = self._read_json(rel)
            if data:
                state["collections"][label] = data
        # scalar config
        cfg = self._read_json("config.json")
        if cfg:
            state["config"] = cfg
        return state

    # -- import ------------------------------------------------------------
    def import_state(self, state: Dict[str, Any], overwrite: bool = True) -> Dict[str, Any]:
        """Import a full snapshot into this machine."""
        imported = 0
        collections = state.get("collections", {})
        for label, rel in [
            ("goals", "brain/goals.json"),
            ("harness", "brain/harness/index.json"),
            ("identity", "brain/identity.json"),
            ("automations", "brain/triggers.json"),
            ("schedules", "brain/recurring.json"),
            ("journal", "brain/action_journal.json"),
            ("leaderboard", "brain/leaderboard.json"),
        ]:
            if label in collections and (overwrite or not (self.data_dir / rel).exists()):
                self._write_json(rel, collections[label])
                imported += 1
        if "config" in state and (overwrite or not (self.data_dir / "config.json").exists()):
            self._write_json("config.json", state["config"])
            imported += 1
        return {"ok": True, "imported_collections": imported}

    # -- reconcile (merge, newest-wins per record) --------------------------
    @staticmethod
    def _ts_key(record: Dict[str, Any]) -> float:
        # find the newest timestamp field in a record
        for k in ("updated_at", "last_run", "last_access", "created_at", "ts"):
            v = record.get(k)
            if isinstance(v, (int, float)):
                return float(v)
        return 0.0

    def _merge_records(self, local: Optional[Dict[str, Any]], remote: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if local is None:
            return remote
        if remote is None:
            return local
        merged = {}
        keys = set(local.keys()) | set(remote.keys())
        for k in keys:
            a = local.get(k)
            b = remote.get(k)
            if a is None:
                merged[k] = b
            elif b is None:
                merged[k] = a
            elif isinstance(a, dict) and isinstance(b, dict) and "ts" in a or (isinstance(a, dict) and "updated_at" in a):
                # nested record: newest wins
                merged[k] = a if self._ts_key(a) >= self._ts_key(b) else b
            else:
                merged[k] = a
        return merged

    def reconcile(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Merge this machine's state with a remote snapshot (newest wins)."""
        merged_count = 0
        remote_colls = state.get("collections", {})
        for label, rel in [
            ("goals", "brain/goals.json"),
            ("harness", "brain/harness/index.json"),
            ("identity", "brain/identity.json"),
            ("automations", "brain/triggers.json"),
            ("schedules", "brain/recurring.json"),
            ("journal", "brain/action_journal.json"),
        ]:
            local = self._read_json(rel)
            remote = remote_colls.get(label)
            if remote is None:
                continue
            # merge top-level record maps
            merged = self._merge_records(local, remote)
            if merged is not None:
                self._write_json(rel, merged)
                merged_count += 1
        return {"ok": True, "reconciled_collections": merged_count}

    # -- stats ---------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        return {"data_dir": str(self.data_dir),
                "collections_supported": ["goals", "harness", "identity",
                                          "automations", "schedules", "journal",
                                          "leaderboard"]}


def get_mesh(**kwargs) -> MeshSync:
    return MeshSync(**kwargs)
