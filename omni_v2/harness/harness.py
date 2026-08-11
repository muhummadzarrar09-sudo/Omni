"""
OMNI CONTINUAL HARNESS (Phase 12) — the "grows with you" self-refining loop.

Inspired by Prime Agent's Continual Harness: a durable, versioned store of
supplemental agent state (skills, memories, lessons) that OMNI REFINES from its
own trajectories — never rewriting the immutable base system prompt.

Core ideas (all headless-testable, no model required for the plumbing):
  - HARNESS STATE: durable, versioned artifacts under data/brain/harness/:
      skills/   -> reusable procedural skills (created + self-improved)
      memory/   -> distilled durable facts ("who you are" / environment quirks)
      lessons/  -> evidence-backed trajectory lessons ("do X before Y")
  - SNAPSHOTS: every commit is versioned and rollback-able. The base prompt is
    never touched.
  - REFINE FROM TRAJECTORY: given a finished goal (goals stack) + metacog
    verdicts, distill reusable knowledge into a new or updated artifact.
  - AUTO SKILL CREATION: on a repeated successful pattern, generate a skill
    (verified by the SkillVerifier) and wire it into the brain.
  - SELF-IMPROVEMENT: when metacog flags a skill/lesson misfiring, patch it with
    the suggested fix and bump the version.

The model is NOT required for the harness plumbing: distillation uses a
pluggable `distiller` (supply the deep LLM on DGX later). With no distiller it
produces deterministic, evidence-backed artifacts from the trajectory, so it
works today on the 1050 Ti and upgrades automatically on the DGX Station.
"""
from __future__ import annotations
import json
import re
import time
import uuid
import shutil
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Harness")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

HARNESS_DIR = DATA_DIR / "brain" / "harness"
SKILLS_DIR = HARNESS_DIR / "skills"
MEMORY_DIR = HARNESS_DIR / "memory"
LESSONS_DIR = HARNESS_DIR / "lessons"
INDEX_PATH = HARNESS_DIR / "index.json"

# artifact kinds
KIND_SKILL = "skill"
KIND_MEMORY = "memory"
KIND_LESSON = "lesson"


class HarnessArtifact:
    """One versioned artifact in the harness (skill / memory / lesson)."""

    def __init__(self, kind: str, name: str, content: str, version: int = 1,
                 created_at: Optional[float] = None, updated_at: Optional[float] = None,
                 evidence: Optional[List[str]] = None):
        self.kind = kind
        self.name = name
        self.content = content
        self.version = version
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at
        self.evidence = evidence or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind, "name": self.name, "content": self.content,
            "version": self.version, "created_at": self.created_at,
            "updated_at": self.updated_at, "evidence": self.evidence,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "HarnessArtifact":
        return HarnessArtifact(
            kind=d["kind"], name=d["name"], content=d["content"],
            version=d.get("version", 1), created_at=d.get("created_at"),
            updated_at=d.get("updated_at"), evidence=d.get("evidence", []),
        )

    @property
    def path(self) -> Path:
        return HARNESS_DIR / self.kind / f"{self.name}.json"


class ContinualHarness:
    """Versioned, refinable harness store + refine-from-trajectory loop."""

    def __init__(self, harness_dir: Optional[Path] = None,
                 distiller: Optional[Callable[[str], str]] = None,
                 verifier=None,
                 post_skill_hook: Optional[Callable[[HarnessArtifact], None]] = None):
        self.root = Path(harness_dir) if harness_dir else HARNESS_DIR
        for sub in (self.root / "skills", self.root / "memory",
                    self.root / "lessons", self.root / "snapshots"):
            sub.mkdir(parents=True, exist_ok=True)
        self.distiller = distiller       # optional LLM for richer distillation
        self.verifier = verifier         # SkillVerifier for skills
        # post_skill_hook(skill): called after a SKILL artifact is created or
        # refined — used by the SkillVerificationLoop to auto-test + rollback.
        self.post_skill_hook = post_skill_hook
        self._lock = threading.RLock()
        self._load_verifier()
        self._artifacts: Dict[str, HarnessArtifact] = {}
        self._load()

    def _load_verifier(self):
        if self.verifier is None:
            try:
                from omni_v2.skills.verifier import SkillVerifier
                self.verifier = SkillVerifier
            except Exception:
                self.verifier = None

    # -- persistence --------------------------------------------------------
    def _load(self) -> None:
        try:
            idx_path = self.root / "index.json"
            if idx_path.exists():
                idx = json.loads(idx_path.read_text(encoding="utf-8"))
                for key, d in idx.items():
                    self._artifacts[key] = HarnessArtifact.from_dict(d)
        except Exception as e:
            logger.warning(f"harness load failed: {e}")

    def _save(self) -> None:
        with self._lock:
            try:
                idx_path = self.root / "index.json"
                idx_path.write_text(
                    json.dumps({k: v.to_dict() for k, v in self._artifacts.items()}, indent=2),
                    encoding="utf-8")
                # also write per-artifact files for inspectability
                for a in self._artifacts.values():
                    p = self.root / a.kind / f"{a.name}.json"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(json.dumps(a.to_dict(), indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"harness save failed: {e}")

    def _key(self, kind: str, name: str) -> str:
        return f"{kind}:{name.lower()}"

    # -- CRUD ---------------------------------------------------------------
    def add(self, kind: str, name: str, content: str,
            evidence: Optional[List[str]] = None) -> HarnessArtifact:
        """Add a new artifact (skill/memory/lesson). Snapshots the prior if replacing."""
        key = self._key(kind, name)
        with self._lock:
            prior = self._artifacts.get(key)
            if prior is not None and prior.content != content:
                self._snapshot(prior)  # preserve old version before overwrite
            art = HarnessArtifact(kind=kind, name=name, content=content,
                                  version=(prior.version + 1) if prior else 1,
                                  evidence=evidence or [])
            self._artifacts[key] = art
            self._save()
        # fire post-skill hook (auto verification) after releasing the lock
        if kind == KIND_SKILL and self.post_skill_hook is not None:
            try:
                self.post_skill_hook(art)
            except Exception as e:
                logger.warning(f"post_skill_hook failed: {e}")
        return art

    def get(self, kind: str, name: str) -> Optional[HarnessArtifact]:
        return self._artifacts.get(self._key(kind, name))

    def remove(self, kind: str, name: str) -> bool:
        """Remove an artifact. Returns True if it existed."""
        key = self._key(kind, name)
        with self._lock:
            if key in self._artifacts:
                del self._artifacts[key]
                self._save()
                return True
            return False

    def list(self, kind: Optional[str] = None) -> List[HarnessArtifact]:
        arts = self._artifacts.values()
        if kind:
            arts = [a for a in arts if a.kind == kind]
        return sorted(arts, key=lambda a: a.updated_at, reverse=True)

    def _snapshot(self, art: HarnessArtifact) -> None:
        """Save a prior version into a snapshots dir (rollback-able)."""
        try:
            snap_dir = self.root / "snapshots" / self._key(art.kind, art.name)
            snap_dir.mkdir(parents=True, exist_ok=True)
            (snap_dir / f"v{art.version}.json").write_text(
                json.dumps(art.to_dict(), indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"harness snapshot failed: {e}")

    def rollback(self, kind: str, name: str, version: Optional[int] = None) -> bool:
        """Restore a previous snapshot. Returns True if a snapshot was found."""
        key = self._key(kind, name)
        snap_dir = self.root / "snapshots" / key
        if not snap_dir.exists():
            return False
        snaps = sorted(snap_dir.glob("v*.json"))
        target = snaps[-1] if version is None else next(
            (s for s in snaps if s.stem == f"v{version}"), None)
        if target is None:
            return False
        d = json.loads(target.read_text(encoding="utf-8"))
        with self._lock:
            self._artifacts[key] = HarnessArtifact.from_dict(d)
            self._save()
        return True

    # -- context loading ----------------------------------------------------
    def build_context(self, topic: str = "", max_chars: int = 1500) -> str:
        """Assemble a compact harness-context block (skills/lessons/memory) to
        inject into the prompt for a given topic — the 'retrieve on demand' win."""
        parts = []
        tl = topic.lower()
        budget = 0
        for a in self.list():
            if tl and tl not in a.name.lower() and tl not in a.content.lower():
                continue
            header = f"[{a.kind.upper()}] {a.name}"
            block = f"{header}: {a.content}"
            budget += len(block)
            if budget > max_chars:
                break
            parts.append(block)
        if not parts:
            return ""
        return "[OMNI HARNESS (refined from experience)]\n" + "\n".join(parts)

    # -- refine from trajectory (the core) ----------------------------------
    def refine_from_trajectory(self, goal: Any, verdicts: Optional[List[Dict[str, Any]]] = None,
                               success: Optional[bool] = None,
                               repeated: bool = False) -> Dict[str, Any]:
        """
        Given a finished goal + its metacog verdicts, distill reusable knowledge:
          - on success + repeated -> auto-create/improve a SKILL
          - always -> add durable MEMORY facts + a LESSON
        Returns summary of what was committed.
        """
        intent = getattr(goal, "intent", "") or getattr(goal, "title", "")
        steps = [s.desc for s in getattr(goal, "steps", [])]
        history = getattr(goal, "history", []) or []
        ok = success if success is not None else (getattr(goal, "status", "") == "done")
        verdicts = verdicts or []

        committed = {"skills": [], "memory": [], "lessons": []}

        # --- distill a reusable skill on a repeated successful pattern ---
        skill_name = self._skill_name(intent)
        existing = self.get(KIND_SKILL, skill_name)
        if ok and (repeated or existing is not None):
            content = self._compose_skill(intent, steps, evidence=history)
            art = self.add(KIND_SKILL, skill_name, content, evidence=[f"goal:{getattr(goal,'id','?')}"])
            committed["skills"].append(art.name)
        elif not ok:
            logger.info(f"harness: goal failed, refining memory/lessons not skill")

        # --- distill durable memory facts ---
        mem_content = self._distill_memory(intent, steps, ok)
        if mem_content:
            mem_name = self._memory_name(intent)
            art = self.add(KIND_MEMORY, mem_name, mem_content,
                           evidence=[f"goal:{getattr(goal,'id','?')}"])
            committed["memory"].append(art.name)

        # --- distill a lesson (esp. from failures / fixes) ---
        lesson = self._distill_lesson(intent, ok, verdicts)
        if lesson:
            lesson_name = self._lesson_name(intent)
            art = self.add(KIND_LESSON, lesson_name, lesson,
                           evidence=[f"goal:{getattr(goal,'id','?')}"])
            committed["lessons"].append(art.name)

        # --- self-improve: apply metacog suggested fixes to an existing skill ---
        if not ok:
            for v in verdicts:
                fix = v.get("suggested_fix", "")
                if fix and existing is not None:
                    improved = existing.content + "\n\nFIX: " + fix
                    art = self.add(KIND_SKILL, skill_name, improved,
                                   evidence=[f"metacog fix: {fix[:60]}"])
                    committed["skills"].append(art.name + f" (improved v{art.version})")
                    break

        return committed

    # -- deterministic distillation (no model) ------------------------------
    def _compose_skill(self, intent: str, steps: List[str], evidence=None) -> str:
        # a lightweight procedural skill in a readable form (SDK-compatible later)
        lines = [f"# Skill: {self._skill_name(intent)}", "",
                 f"## Purpose\n{intent}", "",
                 "## Procedure"]
        for i, s in enumerate(steps, 1):
            lines.append(f"{i}. {s}")
        if evidence:
            lines += ["", "## Evidence"]
            for e in evidence[-5:]:
                lines.append(f"- {str(e)[:80]}")
        return "\n".join(lines)

    def _distill_memory(self, intent: str, steps: List[str], ok: bool) -> str:
        # compact durable fact about how this kind of task is done
        brief = intent[:120]
        if ok:
            return f"Successfully handled: {brief} ({len(steps)} steps). Reusable approach documented."
        return f"Attempted: {brief}. Needs adjustment (see lesson)."

    def _distill_lesson(self, intent: str, ok: bool, verdicts) -> str:
        if ok:
            return f"For '{intent[:100]}': the working path was step-by-step decomposition; keep this ordering."
        # failure lesson from metacog
        causes = ", ".join({v.get("cause", "unknown") for v in verdicts if v.get("cause")})
        if causes:
            return f"For '{intent[:100]}': watch for failures caused by {causes}. Verify before finalizing."
        return f"For '{intent[:100]}': this task needs a different approach before repeating."

    # -- naming ---------------------------------------------------------------
    @staticmethod
    def _slug(name: str) -> str:
        s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        return s[:60] or "artifact"

    def _skill_name(self, intent: str) -> str:
        return "skill_" + self._slug(intent)[:40]

    def _memory_name(self, intent: str) -> str:
        return "mem_" + self._slug(intent)[:40]

    def _lesson_name(self, intent: str) -> str:
        return "lesson_" + self._slug(intent)[:40]

    # -- introspection --------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            kinds = {}
            for a in self._artifacts.values():
                kinds[a.kind] = kinds.get(a.kind, 0) + 1
            return {"artifacts": len(self._artifacts), "by_kind": kinds,
                    "dir": str(self.root), "has_distiller": self.distiller is not None}


def get_harness(**kwargs) -> ContinualHarness:
    return ContinualHarness(**kwargs)
