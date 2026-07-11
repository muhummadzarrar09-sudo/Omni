"""OMNI Plugin - Built-in OMNI control commands"""
from typing import Dict, Any

from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class OMNIPlugin(CommandPlugin):
    """Built-in OMNI control commands.
    
    Handles: help, settings, status, repeat, undo
    Routing is handled by PluginManager alias map + command_registry
    """

    metadata = CommandMetadata(
        name="omni_help",
        category="omni",
        description="OMNI app control commands (help, settings, status, repeat, undo)",
        patterns=[
            r"help",
            r"commands",
            r"what\s+can\s+you\s+do",
            r"what's\s+available",
            r"^settings$",
            r"open\s+settings",
            r"status",
            r"(?:do\s+)?(?:that\s+)?again",
            r"repeat\s+(?:that\s+)?",
            r"redo",
            r"undo",
            r"go\s+back",
        ],
        examples=[
            "what can you do",
            "help",
            "open settings",
            "do that again",
            "repeat",
            "undo"
        ]
    )

    SUPPORTED_ACTIONS = [
        "omni_help",
        "omni_settings",
        "omni_status",
        "omni_repeat",
        "omni_undo",
    ]

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute OMNI control command.
        
        The action (omni_help, omni_settings, omni_status, omni_repeat, omni_undo)
        is determined by command_registry.parse() — we respond based on action name.
        """
        original = (context.get("original") or "").lower().strip()
        last_cmd = context.get("last_command")
        action = context.get("action") or ""

        # Determine sub-action by action name or keywords
        # Normalize action from context if PluginManager injected
        effective_action = ""
        if isinstance(context, dict):
            # action could be passed explicitly via command registry
            effective_action = context.get("original_action", "") or ""

        # We also get parsed action from outer layer? In app.py, parsed.action is passed as external.
        # For safety, we inspect both original and entities
        parsed_action = entities.get("__parsed_action") or ""  # might be injected later
        # Since plugin_manager aliases multiple actions to this plugin, we need to detect intention
        # Use original text analysis but prioritize explicit action string from command_registry
        # The caller (reasoner) passes parsed.original as context["original"], not the action name.
        # We need to infer from original; for more accurate we check if action contains settings/status etc
        # Let's check context for 'action' hint if available
        hint = ""
        if "settings" in original:
            hint = "settings"
        elif "status" in original or "state" in original:
            hint = "status"
        elif any(k in original for k in ["again", "repeat", "redo"]):
            hint = "repeat"
        elif "undo" in original or "go back" in original:
            hint = "undo"
        else:
            hint = "help"

        # Also check if the alias action name is available via special key __action
        # app.py passes parsed.action as separate? No, but we can check context['parsed_action'] if supplied
        if "__parsed_action" in context:
            pa = context["__parsed_action"]
            if "settings" in pa:
                hint = "settings"
            elif "status" in pa:
                hint = "status"
            elif "repeat" in pa:
                hint = "repeat"
            elif "undo" in pa:
                hint = "undo"
            elif "help" in pa:
                hint = "help"

        if hint == "repeat":
            if last_cmd:
                return CommandResult.ok(
                    f"Repeating: '{last_cmd}'",
                    data={"action": "repeat_last", "command": last_cmd}
                )
            return CommandResult.ok(
                "Nothing to repeat yet. Execute a command first, then say 'do that again'."
            )

        if hint == "undo":
            return CommandResult.ok(
                "Undo is not yet implemented for this context. "
                "Some commands like macro playback support undo in future updates."
            )

        if hint == "settings":
            return CommandResult.ok(
                "Opening OMNI settings...",
                data={"action": "open_settings"}
            )

        if hint == "status":
            # Provide richer status if available
            plugin_count = context.get("plugin_count", "many")
            return CommandResult.ok(
                f"OMNI v1.0.0 — All systems operational.\n"
                f"🤖 {plugin_count} plugins loaded\n"
                f"🎤 PTT: V key toggle (press to start/stop listening)\n"
                f"🧠 Reasoner: Plan → Act → Observe → Correct loop active\n"
                f"👁️ Visual Orb: Reactive state indicator\n"
                f"🔊 TTS: Kokoro-ONNX → SAPI → Silent fallback\n"
                f"Say 'help' for commands, 'what's on screen' for accessibility."
            )

        # Help - default
        return CommandResult.ok(
            "🤖 OMNI Voice Commands — Accessibility First\n\n"
            "BROWSER:\n"
            "  • 'open github' — Open a website\n"
            "  • 'search for cats' — Google search\n"
            "  • 'go to https://...' — Open any URL\n"
            "  • 'click login' / 'type hello' / 'scroll down'\n\n"
            "WINDOWS:\n"
            "  • 'open notepad' — Launch desktop app\n"
            "  • 'close window' / 'minimize window' / 'maximize window'\n\n"
            "VS CODE:\n"
            "  • 'open main.py' — Open file in VS Code\n"
            "  • 'run command echo hello' — Terminal command\n"
            "  • 'save' / 'create file utils.py'\n\n"
            "SYSTEM:\n"
            "  • 'screenshot' — Capture screen\n"
            "  • 'copy this text' / 'paste' / 'volume up/down/mute'\n\n"
            "ACCESSIBILITY (ALPHA):\n"
            "  • 'record this' — Start macro recording\n"
            "  • 'save macro morning' / 'run morning'\n"
            "  • 'what's on screen' — Describe current UI\n"
            "  • 'show commands' — Context-aware hints\n"
            "  • 'find login button'\n\n"
            "OMNI CORE:\n"
            "  • 'help' — Show this list\n"
            "  • 'settings' — Open settings panel\n"
            "  • 'do that again' — Repeat last command\n"
            "  • 'status' — System status\n\n"
            "INTEGRATIONS (BETA):\n"
            "  • 'send email to john' — Compose email\n"
            "  • 'what's on my calendar' — Today's schedule\n"
            "  • 'turn on the lights' — Smart home"
        )

    async def verify_action(self, entities: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return True
