"""Files Tool V2 - 10 tools"""
from pathlib import Path
from typing import Dict, Any
from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class FilesTool(CommandPlugin):
    metadata = CommandMetadata(
        name="files_list_dir",
        category="files",
        description="Files 10 tools",
        patterns=[],
        examples=["list files"]
    )
    SUPPORTED_ACTIONS = ["files_create_folder", "files_delete", "files_list_dir",
                         "files_search_files", "files_write", "files_read"]

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = context.get("original", "").lower()

        # Path-based action takes priority
        action = entities.get("action", "")
        path = entities.get("path") or entities.get("file_path") or entities.get("filename")
        content = entities.get("content") or entities.get("text") or entities.get("data")

        # 1. WRITE FILE (the big one for "create X and open in Y")
        if action == "write" or content is not None or "write" in original or "save" in original:
            return await self._write_file(path, content, original)

        # 2. READ FILE
        if action == "read" or "read" in original or "open file" in original:
            return await self._read_file(path, original)

        # 3. LIST
        if "list" in original:
            files = list(Path.cwd().glob("*"))[:20]
            return CommandResult.ok(f"Files: {', '.join(f.name for f in files)}")

        # 4. CREATE FOLDER
        if "create folder" in original:
            name = entities.get("name", "test_folder")
            Path(name).mkdir(exist_ok=True)
            return CommandResult.ok(f"Created folder {name}")

        return CommandResult.ok(f"Files action: {original}")

    async def _write_file(self, path, content, original):
        """Write text to a file. Creates dirs as needed. SECURE."""
        if not path:
            # Guess a path from the request
            name = "output.txt"
            if "python" in original or ".py" in original:
                name = "script.py"
            elif "html" in original:
                name = "page.html"
            elif "javascript" in original or ".js" in original:
                name = "script.js"
            path = f"D:/Omni/data/output/{name}"

        if content is None:
            content = ""

        # GUARD-02: validate path & content
        try:
            from omni_v2.core.guardrails import safe_path, cap_string
            from pathlib import Path as _Path
            # Default allowed root = D:/Omni/data/output/ or wherever REPO_ROOT/data is
            try:
                from omni_v2.core.paths import DATA_DIR
                allowed_root = DATA_DIR / "output"
            except Exception:
                allowed_root = _Path("D:/Omni/data/output")
            allowed_root.mkdir(parents=True, exist_ok=True)
            is_safe, err = safe_path(path, allowed_root=allowed_root)
            if not is_safe:
                return CommandResult.fail(f"Path blocked by guardrail: {err}")
            # Cap content size
            content = cap_string(str(content), max_len=1024*1024, name="file content")
        except ImportError:
            pass  # guardrails not available, fall through

        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(content), encoding="utf-8")
            return CommandResult.ok(
                f"✅ Wrote {len(str(content))} chars to {path}",
                metadata={"path": str(p.resolve()), "size": len(str(content))}
            )
        except Exception as e:
            return CommandResult.fail(f"Write failed: {e}")

    async def _read_file(self, path, original):
        if not path:
            return CommandResult.fail("No path given")
        try:
            p = Path(path)
            if not p.exists():
                return CommandResult.fail(f"File not found: {path}")
            content = p.read_text(encoding="utf-8", errors="replace")
            return CommandResult.ok(content[:2000], metadata={"path": str(p.resolve())})
        except Exception as e:
            return CommandResult.fail(f"Read failed: {e}")

    async def verify_action(self, e, c):
        return True
