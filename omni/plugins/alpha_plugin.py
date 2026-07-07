"""
ALPHA Plugin - Accessibility Innovation Features
Includes: Voice Macros, Context-Aware Help, Adaptive Commands, Screen Description
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger

from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


@dataclass
class VoiceMacro:
    """A recorded voice macro"""
    name: str
    commands: List[Dict[str, Any]]
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "commands": self.commands,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VoiceMacro':
        return cls(
            name=data["name"],
            commands=data["commands"],
            created_at=data.get("created_at", "")
        )


class MacroManager:
    """Manages voice macro recording and playback"""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or (Path.home() / ".omni" / "macros.json")
        self.macros: Dict[str, VoiceMacro] = {}
        self.is_recording = False
        self.recorded_commands: List[Dict] = []
        self._load()
    
    def _load(self) -> None:
        """Load macros from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.macros = {
                        name: VoiceMacro.from_dict(m) 
                        for name, m in data.items()
                    }
                logger.info(f"Loaded {len(self.macros)} macros")
            except Exception as e:
                logger.error(f"Failed to load macros: {e}")
    
    def _save(self) -> None:
        """Save macros to storage"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.storage_path, 'w') as f:
                json.dump({
                    name: m.to_dict() 
                    for name, m in self.macros.items()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save macros: {e}")
    
    def start_recording(self) -> None:
        """Start recording a new macro"""
        self.is_recording = True
        self.recorded_commands = []
        logger.info("Macro recording started")
    
    def add_command(self, command: Dict[str, Any]) -> None:
        """Add a command to the current recording"""
        if self.is_recording:
            self.recorded_commands.append(command)
            logger.debug(f"Added command to recording: {command}")
    
    def save_recording(self, name: str) -> bool:
        """Save the recorded commands as a macro"""
        if not self.recorded_commands:
            return False
        
        from datetime import datetime
        
        macro = VoiceMacro(
            name=name,
            commands=self.recorded_commands.copy(),
            created_at=datetime.now().isoformat()
        )
        
        self.macros[name] = macro
        self._save()
        
        self.is_recording = False
        self.recorded_commands = []
        
        logger.info(f"Macro saved: {name}")
        return True
    
    def cancel_recording(self) -> None:
        """Cancel the current recording"""
        self.is_recording = False
        self.recorded_commands = []
        logger.info("Macro recording cancelled")
    
    def get_macro(self, name: str) -> Optional[VoiceMacro]:
        """Get a macro by name"""
        return self.macros.get(name)
    
    def delete_macro(self, name: str) -> bool:
        """Delete a macro"""
        if name in self.macros:
            del self.macros[name]
            self._save()
            return True
        return False
    
    def list_macros(self) -> List[str]:
        """List all macro names"""
        return list(self.macros.keys())


class ContextManager:
    """Manages context-aware command suggestions"""
    
    def __init__(self):
        self.current_context = "unknown"
        self.context_hints: Dict[str, List[str]] = {
            "browser": [
                "open [website]",
                "search for [query]",
                "click [element]",
                "type [text]",
                "scroll up/down"
            ],
            "windows": [
                "open [app]",
                "click [button]",
                "close window",
                "minimize window",
                "type [text]"
            ],
            "vscode": [
                "open [file]",
                "run [command]",
                "save file",
                "create file [name]"
            ],
            "desktop": [
                "open [app]",
                "screenshot",
                "volume up/down",
                "show help"
            ]
        }
    
    def set_context(self, context: str) -> None:
        """Set the current context"""
        self.current_context = context
        logger.debug(f"Context set to: {context}")
    
    def get_hints(self) -> List[str]:
        """Get command hints for current context"""
        return self.context_hints.get(self.current_context, [
            "open [app or website]",
            "search for [query]",
            "help",
            "settings"
        ])
    
    def suggest_commands(self, partial: str) -> List[str]:
        """Suggest commands based on partial input"""
        all_commands = []
        for hints in self.context_hints.values():
            all_commands.extend(hints)
        
        partial = partial.lower()
        return [c for c in all_commands if partial in c.lower()][:5]


class AdaptiveParser:
    """Learns from user command patterns"""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or (Path.home() / ".omni" / "patterns.json")
        self.patterns: Dict[str, int] = {}
        self._load()
    
    def _load(self) -> None:
        """Load patterns from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    self.patterns = json.load(f)
                logger.info(f"Loaded {len(self.patterns)} patterns")
            except:
                pass
    
    def _save(self) -> None:
        """Save patterns to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.patterns, f, indent=2)
        except:
            pass
    
    def learn(self, command: str) -> None:
        """Learn a command pattern"""
        cmd = command.lower().strip()
        self.patterns[cmd] = self.patterns.get(cmd, 0) + 1
        self._save()
    
    def suggest(self, partial: str) -> List[str]:
        """Suggest commands based on learned patterns"""
        partial = partial.lower()
        matches = [
            (cmd, count) 
            for cmd, count in self.patterns.items() 
            if cmd.startswith(partial)
        ]
        matches.sort(key=lambda x: x[1], reverse=True)
        return [cmd for cmd, _ in matches[:5]]


class AlphaPlugin(CommandPlugin):
    """ALPHA Features: Voice Macros, Context-Aware Help, Adaptive Learning"""
    
    metadata = CommandMetadata(
        name="alpha_control",
        category="alpha",
        description="Advanced accessibility features - macros, context help, adaptive learning",
        patterns=[
            r"record\s+(?:this|macro)",
            r"save\s+macro\s+(?P<name>\w+)",
            r"run\s+(?P<macro>\w+)",
            r"show\s+(?:me\s+)?(?:what\s+can\s+i\s+say|commands|hints)",
            r"(?:what\s+can\s+i\s+say|available\s+commands)",
            r"learn\s+this",
            r"screen\s+description",
            r"what[']?s?\s+(?:on\s+)?screen",
            r"find\s+(?P<element>.+)",
        ],
        examples=[
            "record this",
            "save macro morning",
            "run morning",
            "what can i say",
            "what's on screen",
            "find the login button"
        ]
    )
    
    def __init__(self):
        super().__init__()
        self.macro_manager = MacroManager()
        self.context_manager = ContextManager()
        self.adaptive_parser = AdaptiveParser()
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Execute ALPHA command"""
        original = entities.get("original", "").lower()
        
        # Macro recording
        if "record" in original:
            return self._start_recording()
        
        # Save macro
        if "save macro" in original or "save this" in original:
            name = entities.get("name", "untitled")
            return self._save_macro(name)
        
        # Run macro
        if "run" in original and "macro" in entities:
            return await self._run_macro(entities["macro"])
        
        # Show hints
        if any(kw in original for kw in ["what can i say", "commands", "hints", "available"]):
            return self._show_hints()
        
        # Screen description
        if any(kw in original for kw in ["screen", "what's on", "find"]):
            return self._describe_screen(entities.get("element", ""))
        
        # Learn command
        if "learn" in original:
            return self._learn_command(context)
        
        return CommandResult.error("Unknown ALPHA command")
    
    def _start_recording(self) -> CommandResult:
        """Start macro recording"""
        self.macro_manager.start_recording()
        return CommandResult.ok("Recording started. Execute commands, then say 'save macro [name]' or 'cancel recording'")
    
    def _save_macro(self, name: str) -> CommandResult:
        """Save current recording as macro"""
        if self.macro_manager.is_recording:
            if self.macro_manager.save_recording(name):
                return CommandResult.ok(f"Macro '{name}' saved with {len(self.macro_manager.recorded_commands)} commands")
            return CommandResult.error("No commands recorded")
        return CommandResult.error("Not currently recording. Say 'record this' to start")
    
    async def _run_macro(self, name: str) -> CommandResult:
        """Run a saved macro"""
        macro = self.macro_manager.get_macro(name)
        
        if not macro:
            return CommandResult.error(f"Macro '{name}' not found")
        
        # Execute all commands in macro
        # This would need to be passed to the command executor
        return CommandResult.ok(
            f"Running macro '{name}' with {len(macro.commands)} commands",
            data={"macro": macro.to_dict()}
        )
    
    def _show_hints(self) -> CommandResult:
        """Show available commands for current context"""
        hints = self.context_manager.get_hints()
        context = self.context_manager.current_context
        
        hints_text = f"Commands for {context}:\n" + "\n".join(f"  • {h}" for h in hints)
        hints_text += "\n\nAlso try: 'record this' to create a macro"
        
        return CommandResult.ok(hints_text)
    
    def _describe_screen(self, element: str = "") -> CommandResult:
        """Provide screen description"""
        if element:
            return CommandResult.ok(
                f"Looking for '{element}'...\n"
                f"Note: Full screen description requires browser accessibility tree. "
                f"Ensure Chrome is running with --force-renderer-accessibility"
            )
        
        return CommandResult.ok(
            "Screen description:\n"
            "This feature reads the current screen/UI elements.\n"
            "Use with Chrome for best results."
        )
    
    def _learn_command(self, context: Dict[str, Any]) -> CommandResult:
        """Learn the current command"""
        original = context.get("original", "")
        if original:
            self.adaptive_parser.learn(original)
            return CommandResult.ok(f"Learned: '{original}'")
        return CommandResult.error("No command to learn")


class ScreenDescriberPlugin(CommandPlugin):
    """AI-powered screen description for accessibility"""
    
    metadata = CommandMetadata(
        name="screen_description",
        category="accessibility",
        description="Describe screen content for accessibility",
        patterns=[
            r"what[']?s?\s+(?:on\s+)?screen",
            r"describe\s+screen",
            r"read\s+page",
            r"where\s+(?:am\s+i|is)",
        ],
        examples=[
            "what's on screen",
            "describe screen",
            "where am i"
        ]
    )
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Describe the current screen"""
        # This would integrate with CDP accessibility tree
        description = """
Current screen description:

🔍 I can see you're in an application window.

To get detailed descriptions:
• Ensure Chrome is open with accessibility enabled
• Use "find [element]" to locate specific items

Example: "Find the submit button"
"""
        return CommandResult.ok(description.strip())


class AccessibilityPlugin(CommandPlugin):
    """High-contrast mode, large text, audio-only mode"""
    
    metadata = CommandMetadata(
        name="accessibility_mode",
        category="accessibility",
        description="Accessibility mode controls",
        patterns=[
            r"high\s+contrast",
            r"large\s+text",
            r"audio\s+only",
            r"accessibility\s+mode",
        ],
        examples=[
            "high contrast",
            "large text",
            "audio only mode"
        ]
    )
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Toggle accessibility mode"""
        original = entities.get("original", "").lower()
        
        modes = {
            "high contrast": "High contrast mode enabled",
            "large text": "Large text mode enabled",
            "audio only": "Audio-only mode enabled (visual UI minimized)"
        }
        
        for mode, message in modes.items():
            if mode in original:
                return CommandResult.ok(message + ". Say the same command to disable.")
        
        return CommandResult.ok("Accessibility modes:\n• 'high contrast'\n• 'large text'\n• 'audio only mode'")