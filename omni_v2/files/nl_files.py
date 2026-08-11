"""
OMNI NATURAL-LANGUAGE FILE MANAGER (Phase 15, #5) — safe file operations.

Lets the brain turn commands like "move all PDFs from Downloads to Documents"
into safe, bounded file operations. It:
  - parses intent into an op (copy/move/delete/rename/list) + a matcher
    (extension, name-substring, folder) + src/dest.
  - SANDBOXES operations to an allowed root (never touches system paths).
  - records each op in the Action Journal so it can be undone.

Fully local + headless-testable (matcher + planner are pure logic; tests use
temp dirs). The executor is pluggable so the real tool can call this.
"""
from __future__ import annotations
import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("NLFileManager")


OPS = ("copy", "move", "delete", "rename", "list")


def parse_intent(text: str) -> Dict[str, Any]:
    """Parse a natural-language file command into a plan.
    Returns {op, ext, name, src, dest, ...} (best-effort)."""
    t = text.lower()
    plan: Dict[str, Any] = {"raw": text}

    # op
    if "move" in t or "mv " in t:
        plan["op"] = "move"
    elif "copy" in t or "duplicate" in t or "cp " in t:
        plan["op"] = "copy"
    elif "delete" in t or "remove" in t or "rm " in t:
        plan["op"] = "delete"
    elif "rename" in t:
        plan["op"] = "rename"
    elif "list" in t or "show" in t:
        plan["op"] = "list"
    else:
        plan["op"] = "list"

    # extension: literal ".pdf" OR a plural word like "pdfs"/"txt files"
    ext_m = re.search(r"\.([a-z0-9]{1,5})\b", t)
    if ext_m:
        plan["ext"] = "." + ext_m.group(1)
    else:
        # common file-type words: "pdfs", "txt files", "jpegs", etc.
        ft_m = re.search(r"\b([a-z0-9]{1,5})s?\s+(?:files|docs)\b|\b([a-z0-9]{1,5})s\b", t)
        if ft_m:
            w = (ft_m.group(1) or ft_m.group(2) or "").lower()
            if w and w not in ("all", "the", "these"):
                plan["ext"] = "." + w

    # from/to folders (last 'from X to Y' or 'to Y')
    to_m = re.search(r"\bto\s+([\w/\\ .-]+?)(?:\s|$)", t)
    from_m = re.search(r"\bfrom\s+([\w/\\ .-]+?)(?:\s+to\b|\s|$)", t)
    if from_m:
        plan["src"] = from_m.group(1).strip()
    if to_m:
        plan["dest"] = to_m.group(1).strip()

    # name substring (words after "named"/"called")
    name_m = re.search(r"(?:named|called)\s+([\w.\-]+)", t)
    if name_m:
        plan["name"] = name_m.group(1)

    return plan


class NLFileManager:
    """Executes safe, bounded file operations from parsed intent."""

    def __init__(self, allowed_root: Optional[Path] = None,
                 journal=None, on_op: Optional[Callable[[Dict[str, Any]], Any]] = None):
        self.allowed_root = Path(allowed_root) if allowed_root else Path.home()
        self.journal = journal      # ActionJournal (optional) for undo
        self.on_op = on_op          # callback for observability / recording

    def _safe(self, p: Path) -> bool:
        try:
            return str(p.resolve()).startswith(str(self.allowed_root.resolve()))
        except Exception:
            return False

    def _match(self, path: Path, plan: Dict[str, Any]) -> bool:
        if plan.get("ext") and path.suffix.lower() != plan["ext"].lower():
            return False
        if plan.get("name") and plan["name"].lower() not in path.name.lower():
            return False
        return True

    def resolve_src(self, plan: Dict[str, Any]) -> Path:
        s = plan.get("src", ".")
        p = Path(s)
        if not p.is_absolute():
            # case-insensitive match against allowed_root children
            base = self.allowed_root / s
            if not base.exists():
                base = self._case_insensitive(self.allowed_root, s)
            p = base
        if not self._safe(p):
            raise PermissionError(f"path outside allowed root: {p}")
        return p

    @staticmethod
    def _case_insensitive(base: Path, name: str) -> Path:
        """Find a child of base matching name (case-insensitive)."""
        for child in base.iterdir():
            if child.name.lower() == name.lower():
                return child
        # try nested
        for child in base.rglob("*"):
            if child.name.lower() == name.lower():
                return child
        return base / name

    def execute(self, text: str) -> Dict[str, Any]:
        """Parse + execute a file command. Returns results."""
        plan = parse_intent(text)
        op = plan.get("op", "list")
        if not self._safe(self.allowed_root):
            raise PermissionError("allowed root is not safe")

        try:
            src = self.resolve_src(plan)
        except PermissionError as e:
            return {"ok": False, "op": op, "error": str(e)}
        if not src.exists():
            return {"ok": False, "op": op, "error": f"source not found: {src}"}

        # gather matching files
        if src.is_dir():
            matches = [f for f in src.rglob("*") if f.is_file() and self._match(f, plan)]
        else:
            matches = [src] if self._match(src, plan) else []

        dest = None
        if plan.get("dest"):
            d = Path(plan["dest"])
            if not d.is_absolute():
                d = self.allowed_root / d
                if not d.exists():
                    d = self._case_insensitive(self.allowed_root, plan["dest"])
            if self._safe(d):
                dest = d
            else:
                return {"ok": False, "op": op, "error": "dest outside allowed root"}

        results = []
        for f in matches[:200]:
            try:
                results.append(self._do(op, f, dest, plan))
            except Exception as e:
                results.append({"file": str(f), "ok": False, "error": str(e)})

        if self.on_op:
            try:
                self.on_op({"op": op, "count": len(results), "plan": plan})
            except Exception:
                pass
        ok = sum(1 for r in results if r.get("ok"))
        return {"ok": ok == len(results) or ok > 0, "op": op,
                "matched": len(results), "succeeded": ok, "results": results}

    def _do(self, op: str, f: Path, dest: Optional[Path], plan) -> Dict[str, Any]:
        result = {"file": str(f), "ok": True}
        if op == "delete":
            # record undo snapshot in journal if available
            if self.journal is not None:
                undo = self.journal.prepare_file_undo("delete", f)
                f.unlink()
                aid = self.journal.record_with_undo("files_delete", {"path": str(f)}, undo)
                result["undo_id"] = aid
            else:
                f.unlink()
        elif op in ("copy", "move"):
            if dest is None:
                return {"file": str(f), "ok": False, "error": "no destination"}
            dest.mkdir(parents=True, exist_ok=True)
            target = dest / f.name
            if self.journal is not None and op == "move":
                undo = self.journal.prepare_file_undo("move", f, dest=target)
            if op == "copy":
                shutil.copy2(f, target)
            else:
                shutil.move(str(f), str(target))
            if self.journal is not None and op == "move":
                aid = self.journal.record_with_undo("files_move",
                                                    {"src": str(f), "dest": str(target)}, undo)
                result["undo_id"] = aid
            result["dest"] = str(target)
        elif op == "rename":
            if dest is None:
                return {"file": str(f), "ok": False, "error": "no new name"}
            target = dest / f.name if dest.is_dir() else dest
            if self.journal is not None:
                undo = self.journal.prepare_file_undo("rename", f, dest=target)
            f.rename(target)
            if self.journal is not None:
                aid = self.journal.record_with_undo("files_rename",
                                                    {"src": str(f), "dest": str(target)}, undo)
                result["undo_id"] = aid
            result["dest"] = str(target)
        elif op == "list":
            result["listed"] = True
        return result


def get_nl_file_manager(**kwargs) -> NLFileManager:
    return NLFileManager(**kwargs)
