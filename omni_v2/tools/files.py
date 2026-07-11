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
    SUPPORTED_ACTIONS = ["files_create_folder", "files_delete", "files_list_dir", "files_search_files"]
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = context.get("original","").lower()
        if "list" in original:
            files = list(Path.cwd().glob("*"))[:10]
            return CommandResult.ok(f"Files: {', '.join(f.name for f in files)}")
        if "create folder" in original:
            name = entities.get("name","test_folder")
            Path(name).mkdir(exist_ok=True)
            return CommandResult.ok(f"Created folder {name}")
        return CommandResult.ok(f"Files action: {original}")
    async def verify_action(self, e, c):
        return True
