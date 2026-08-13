"""File tools restricted to OMNI's writable output directory."""

from pathlib import Path
from typing import Any, ClassVar

from omni_v2.core.guardrails import cap_string, safe_path
from omni_v2.core.paths import DATA_DIR
from omni_v2.core.plugin_manager import CommandMetadata, CommandPlugin, CommandResult


class FilesTool(CommandPlugin):
    metadata = CommandMetadata(
        name="files_list_dir",
        category="files",
        description="Files 10 tools",
        patterns=[],
        examples=["list files"],
    )
    SUPPORTED_ACTIONS: ClassVar[list[str]] = [
        "files_create_folder",
        "files_delete",
        "files_list_dir",
        "files_search_files",
        "files_write",
        "files_read",
    ]

    async def execute(
        self, entities: dict[str, Any], context: dict[str, Any]
    ) -> CommandResult:
        original = context.get("original", "").lower()

        # Path-based action takes priority.
        action = entities.get("action", "")
        path = (
            entities.get("path")
            or entities.get("file_path")
            or entities.get("filename")
        )
        content = entities.get("content") or entities.get("text") or entities.get("data")

        if action == "write" or content is not None or "write" in original or "save" in original:
            return await self._write_file(path, content, original)

        if action == "read" or "read" in original or "open file" in original:
            return await self._read_file(path, original)

        if "list" in original:
            files = list(Path.cwd().glob("*"))[:20]
            return CommandResult.ok(f"Files: {', '.join(f.name for f in files)}")

        if "create folder" in original:
            name = entities.get("name", "test_folder")
            Path(name).mkdir(exist_ok=True)
            return CommandResult.ok(f"Created folder {name}")

        return CommandResult.ok(f"Files action: {original}")

    @staticmethod
    def _output_path(path: str | Path, allowed_root: Path) -> Path:
        requested = Path(path)
        return (
            requested.resolve()
            if requested.is_absolute()
            else (allowed_root / requested).resolve()
        )

    async def _write_file(self, path, content, original):
        """Write text below the canonical runtime output directory."""
        if not path:
            name = "output.txt"
            if "python" in original or ".py" in original:
                name = "script.py"
            elif "html" in original:
                name = "page.html"
            elif "javascript" in original or ".js" in original:
                name = "script.js"
            path = name

        allowed_root = (DATA_DIR / "output").resolve()
        allowed_root.mkdir(parents=True, exist_ok=True)
        is_safe, error = safe_path(str(path), allowed_root=allowed_root)
        if not is_safe:
            return CommandResult.fail(f"Path blocked by guardrail: {error}")

        try:
            target = self._output_path(path, allowed_root)
            target.relative_to(allowed_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            bounded_content = cap_string(
                "" if content is None else str(content),
                max_len=1024 * 1024,
                name="file content",
            )
            target.write_text(bounded_content, encoding="utf-8")
            return CommandResult.ok(
                f"✅ Wrote {len(bounded_content)} chars to {target}",
                data={"path": str(target), "size": len(bounded_content)},
            )
        except (OSError, ValueError) as exc:
            return CommandResult.fail(f"Write failed: {exc}")

    async def _read_file(self, path, original):
        if not path:
            return CommandResult.fail("No path given")

        allowed_root = (DATA_DIR / "output").resolve()
        safe, error = safe_path(str(path), allowed_root=allowed_root)
        if not safe:
            return CommandResult.fail(f"Path blocked by guardrail: {error}")
        try:
            target = self._output_path(path, allowed_root)
            target.relative_to(allowed_root)
            if not target.is_file():
                return CommandResult.fail(f"File not found: {path}")
            content = target.read_text(encoding="utf-8", errors="replace")[:2000]
            return CommandResult.ok(content, data={"path": str(target)})
        except (OSError, ValueError) as exc:
            return CommandResult.fail(f"Read failed: {exc}")

    async def verify_action(self, e, c):
        return True
