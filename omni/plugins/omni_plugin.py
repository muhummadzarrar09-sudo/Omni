"""OMNI Plugin - Built-in OMNI control commands"""
from typing import Dict, Any
from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class OMNIPlugin(CommandPlugin):
    """Built-in OMNI control commands"""
    
    metadata = CommandMetadata(
        name="omni_help",
        category="omni",
        description="OMNI app control commands",
        patterns=[r"(?:what\s+can\s+you\s+do|help|commands)", r"(?:open\s+)?settings", r"status"],
        examples=["help", "settings", "status"]
    )
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        original = entities.get("original", "").lower()
        
        if any(kw in original for kw in ["help", "commands"]):
            return CommandResult.ok("""
OMNI Voice Commands:

BROWSER:
  • "open github" - Open website
  • "search for cats" - Google search
  
WINDOWS:
  • "open notepad" - Launch app

SYSTEM:
  • "screenshot" - Take screenshot

OMNI:
  • "help" - Show this help
  • "settings" - Open settings
""".strip())
        elif "settings" in original:
            return CommandResult.ok("Opening settings...", data={"action": "open_settings"})
        elif "status" in original:
            return CommandResult.ok("OMNI v1.0.0 ready")
        
        return CommandResult.error("Unknown OMNI command")
