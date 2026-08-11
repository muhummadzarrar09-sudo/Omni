"""
OMNI SKILL INSTALLER (Phase 11) — the "app store" moment.

`omni add-skill <url>` pulls a community skill, verifies it with the SDK's AST
safety verifier, and wires it into the brain's tools automatically.

Flow:
  1. fetch the skill source from a URL (raw github / paste / local file)
  2. run SkillVerifier.verify() (AST safety: no destructive ops, no network by
     default)
  3. write it to data/skills/custom/<name>.py
  4. load it via the SkillRegistry (registers into PluginManager + FastAF DB)
  5. report result

Fully local after the fetch. Verifies before executing anything.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("SkillInstaller")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

CUSTOM_SKILLS_DIR = DATA_DIR / "skills" / "custom"


class SkillInstaller:
    """Fetch, verify, install and load community skills."""

    def __init__(self, skills_dir: Optional[Path] = None, verifier=None, registry=None):
        self.skills_dir = Path(skills_dir) if skills_dir else CUSTOM_SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.verifier = verifier
        self.registry = registry
        self._load_verifier()

    def _load_verifier(self):
        if self.verifier is None:
            try:
                from omni_v2.skills.verifier import SkillVerifier
                self.verifier = SkillVerifier
            except Exception:
                self.verifier = None

    def _load_registry(self):
        if self.registry is None:
            try:
                from omni_v2.skills.registry import SkillRegistry
                self.registry = SkillRegistry()
            except Exception:
                self.registry = None

    # -- fetching ---------------------------------------------------------
    @staticmethod
    def fetch_source(source: str) -> Tuple[str, str]:
        """
        Fetch skill source. Returns (code, name_hint).
        Supports: raw URL (github raw), 'name=...' local file, or plain path.
        """
        if source.startswith(("http://", "https://")):
            import urllib.request
            req = urllib.request.Request(source, headers={"User-Agent": "OMNI-SkillInstaller/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                code = r.read().decode("utf-8", errors="ignore")
            name_hint = Path(source).stem
            return code, name_hint
        # local file or inline
        p = Path(source)
        if p.exists() and p.is_file():
            return p.read_text(encoding="utf-8"), p.stem
        raise ValueError(f"cannot fetch skill source: {source}")

    # -- install ------------------------------------------------------------
    def install(self, source: str, allow_network: bool = False,
                force: bool = False) -> Dict[str, Any]:
        """Fetch, verify, write and load a skill. Returns result dict."""
        try:
            code, name_hint = self.fetch_source(source)
        except Exception as e:
            return {"ok": False, "step": "fetch", "detail": str(e)}

        # verify
        if self.verifier is not None:
            try:
                safe, msg = self.verifier.verify(code, allow_network=allow_network)
                if not safe:
                    return {"ok": False, "step": "verify", "detail": msg}
            except Exception as e:
                return {"ok": False, "step": "verify", "detail": f"verifier error: {e}"}

        # determine skill name
        name = name_hint
        m = None
        try:
            import re
            m = re.search(r'@skill\(\s*name\s*=\s*["\']([\w_]+)["\']', code)
            if m:
                name = m.group(1)
        except Exception:
            pass
        if not name or name in ("MySkill", "my_skill"):
            name = f"skill_{int(time.time())}"
        target = self.skills_dir / f"{name}.py"
        if target.exists() and not force:
            return {"ok": False, "step": "exists", "detail": f"{name}.py already exists (use force)"}

        # write
        try:
            target.write_text(code, encoding="utf-8")
        except Exception as e:
            return {"ok": False, "step": "write", "detail": str(e)}

        # load + register
        loaded = False
        load_msg = ""
        self._load_registry()
        if self.registry is not None:
            try:
                plugin = self.registry.load_skill_file(target)
                loaded = plugin is not None
                load_msg = f"registered '{plugin.metadata.name}'" if plugin else "loaded but not registered"
            except Exception as e:
                load_msg = f"load error: {e}"
        return {"ok": True, "step": "installed", "detail": f"installed {name}.py ({load_msg})",
                "name": name, "path": str(target), "loaded": loaded}

    def list_installed(self) -> Dict[str, Any]:
        """List installed custom skills."""
        files = sorted(self.skills_dir.glob("*.py"))
        return {"skills": [f.stem for f in files], "dir": str(self.skills_dir), "count": len(files)}


def get_skill_installer(**kwargs) -> SkillInstaller:
    return SkillInstaller(**kwargs)
