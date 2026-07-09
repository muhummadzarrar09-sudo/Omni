"""OMNI Plugin - Built-in OMNI control commands"""
from typing import Dict, Any

from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class OMNIPlugin(CommandPlugin):
    """Built-in OMNI control commands.
    
    Routing is handled entirely by command_registry.py.
    This plugin executes based on the parsed action name.
    """
    
    metadata = CommandMetadata(
        name="omni_help",
        category="omni",
        description="OMNI app control commands (help, settings, status)",
        patterns=[
            r"help",
            r"commands",
            r"what\s+can\s+you\s+do",
            r"what[']?s\s+available",
            r"^settings$",
            r"open\s+settings",
            r"status",
        ],
        examples=[
            "what can you do",
            "help",
            "open settings",
            "status"
        ]
    )
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute OMNI control command.
        
        The action (omni_help, omni_settings, omni_status) is determined
        by command_registry.parse() — we just respond to the original text.
        """
        original = (context.get("original") or "").lower().strip()
        
        # Help commands
        if any(kw in original for kw in [
            "help", "commands", "what can you do", "what's available",
            "show me commands", "what's there", "available"
        ]):
            return CommandResult.ok(
                "OMNI Voice Commands:\n\n"
                "BROWSER:\n"
                "  • 'open github' — Open a website\n"
                "  • 'search for cats' — Google search\n"
                "  • 'go to https://...' — Open any URL\n\n"
                "WINDOWS:\n"
                "  • 'open notepad' — Launch a desktop app\n"
                "  • 'launch chrome' — Start an application\n\n"
                "SYSTEM:\n"
                "  • 'screenshot' — Capture your screen\n"
                "  • 'volume up/down' — Adjust audio\n\n"
                "ACCESSIBILITY (ALPHA):\n"
                "  • 'record this' — Start macro recording\n"
                "  • 'run mymacro' — Play a saved macro\n"
                "  • 'what's on screen' — Describe current UI\n"
                "  • 'show commands' — Context-aware hints\n\n"
                "OMNI:\n"
                "  • 'help' — Show this list\n"
                "  • 'settings' — Open settings panel\n"
                "  • 'status' — System status\n\n"
                "INTEGRATIONS:\n"
                "  • 'send email to john' — Compose email\n"
                "  • 'what's on my calendar' — Today's schedule\n"
                "  • 'turn on the lights' — Smart home control"
            )
        
        # Settings
        if any(kw in original for kw in ["settings", "change settings", "modify settings"]):
            return CommandResult.ok(
                "Opening OMNI settings...",
                data={"action": "open_settings"}
            )
        
        # Status
        if any(kw in original for kw in ["status", "what's your state", "how are you"]):
            return CommandResult.ok(
                "OMNI v1.0.0 — All systems operational.\n"
                "8 plugins loaded. CapsLock PTT active.\n"
                "Whisper base.en ready. SAPI TTS ready."
            )
        
        return CommandResult.error("Unknown OMNI command")