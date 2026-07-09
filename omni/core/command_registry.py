"""
Command Registry - Pattern-based Command Parser
Maps natural language to structured commands for ALL phases (MVP + ALPHA + BETA)

Priority order (first match wins):
  1. integrations (specific, context-rich patterns)
  2. alpha (accessibility)
  3. windows (desktop apps)
  4. browser (websites)
  5. vscode (code files)
  6. system
  7. omni (generic control)
  8. accessibility
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class ParsedCommand:
    """A parsed voice command"""
    action: str
    entities: Dict[str, str]
    original: str
    confidence: float
    patterns_matched: List[str]


class CommandRegistry:
    """Registry of command patterns for all OMNI phases."""
    
    # URL shortcuts for common sites
    URL_SHORTCUTS = {
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "google": "https://www.google.com",
        "chatgpt": "https://chat.openai.com",
        "chat": "https://chat.openai.com",
        "gmail": "https://www.gmail.com",
        "mail": "https://www.gmail.com",
        "reddit": "https://www.reddit.com",
        "twitter": "https://www.twitter.com",
        "x": "https://www.x.com",
        "linkedin": "https://www.linkedin.com",
        "discord": "https://www.discord.com",
        "whatsapp": "https://web.whatsapp.com",
        "wiki": "https://www.wikipedia.org",
        "drive": "https://drive.google.com",
        "spotify": "https://www.spotify.com",
        "netflix": "https://www.netflix.com",
        "amazon": "https://www.amazon.com",
        "instagram": "https://www.instagram.com",
        "facebook": "https://www.facebook.com",
        "bing": "https://www.bing.com",
        "stackoverflow": "https://stackoverflow.com",
        "gitlab": "https://gitlab.com",
        "bitbucket": "https://bitbucket.org",
        "trello": "https://trello.com",
        "notion": "https://www.notion.so",
        "figma": "https://www.figma.com",
        "slack": "https://slack.com",
        "teams": "https://teams.microsoft.com",
        "zoom": "https://zoom.us",
        "messenger": "https://www.messenger.com",
        "telegram": "https://web.telegram.org",
    }
    
    # Windows known apps (for disambiguation)
    WINDOWS_KNOWN_APPS = [
        "notepad", "calculator", "explorer", "cmd", "powershell",
        "paint", "wordpad", "taskmgr", "regedit", "control",
        "magnifier", "snipping", "mspaint", "word", "excel",
        "chrome", "firefox", "edge", "teams", "zoom",
        "discord", "spotify", "vlc", "steam",
        "terminal", "taskmanager",
    ]
    
    # Code file extensions (VSCode only, NOT web TLDs like .com, .org)
    CODE_EXTENSIONS = r"(?:py|js|ts|jsx|tsx|json|md|txt|csv|html|css|xml|yaml|yml|sh|bat|ps1|go|rs|java|cpp|c|h|pyw|pyi)"
    
    def __init__(self):
        self._patterns: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
        self._register_all_patterns()
        logger.info("CommandRegistry initialized with all phases")
    
    def _register_all_patterns(self) -> None:
        """Register patterns for MVP + ALPHA + BETA.
        Order matters: first category+action to match wins.
        """
        
        # ===== VS CODE COMMANDS (MVP) - FIRST for file disambiguation =====
        # Only code file extensions (NOT .com, .org, .net, .io, .co, etc.)
        self.register_patterns("vscode", {
            "open": [
                # "open main.py" - \b after extension prevents greedy .com → .c trick
                (r"open\s+(?:file\s+)?(?P<file>\S+\." + self.CODE_EXTENSIONS + r")\b", "file"),
                (r"show\s+(?:file\s+)?(?P<file>\S+\." + self.CODE_EXTENSIONS + r")\b", "file"),
                (r"find\s+file\s+(?P<file>\S+\." + self.CODE_EXTENSIONS + r")\b", "file"),
            ],
            "terminal": [
                # "run command echo hello" - explicit "command" keyword required
                (r"run\s+command\s+(?P<command>.+)", "command"),
                (r"execute\s+in\s+terminal\s+(?P<command>.+)", "command"),
                (r"terminal\s+(?P<command>.+)", "command"),
            ],
            "save": [
                # "save" alone or "save file" - must be standalone (not "save macro...")
                (r"^save(?:\s+file)?$", None),
                (r"(?:ctrl\s+\+\s*)?s\s+save", None),
            ],
            "create": [
                # "create new file main.py" - code files with explicit "file" keyword
                (r"create\s+(?:new\s+)?file\s+(?P<file>\S+\." + self.CODE_EXTENSIONS + r")\b", "file"),
                (r"new\s+file\s+(?P<file>\S+\." + self.CODE_EXTENSIONS + r")\b", "file"),
            ],
        })
        
        # ===== INTEGRATIONS (BETA) - HIGH PRIORITY =====
        self.register_patterns("integrations", {
            "send_email": [
                (r"(?:send|compose)\s+(?:an?\s+)?email\s+(?:to\s+)?(?P<recipient>\w[\w.-]*)", "recipient"),
            ],
            "read_emails": [
                (r"(?:read|check)\s+(?:my\s+)?emails?", None),
                (r"show\s+emails", None),
            ],
            "count_emails": [
                (r"(?:how\s+many|count)\s+(?:unread\s+)?emails?", None),
            ],
            "schedule_meeting": [
                (r"(?:schedule|book)\s+(?:meeting|event)\s+(?:called\s+)?(?P<title>.+)", "title"),
            ],
            "show_calendar": [
                # "what's on my calendar" / "show my calendar" / "what's today"
                (r"(?:what[']?s|show|check)\s+(?:on\s+)?(?:my\s+)?calenda?r", None),
                (r"what[']?s?\s+today", None),
            ],
            "cancel_event": [
                (r"(?:cancel|delete)\s+(?:meeting|event)\s+(?P<title>.+)", "title"),
            ],
            "lights_on": [
                (r"(?:turn\s+)?on\s+(?:the\s+)?lights?", None),
            ],
            "lights_off": [
                # "turn off the lights" / "lights off" / "turn the lights off"
                (r"(?:turn\s+)?off\s+(?:the\s+)?lights?", None),
                (r"lights\s+off", None),
            ],
            "set_temperature": [
                (r"(?:set|adjust)\s+(?:temperature|thermostat)\s+(?:to\s+)?(?P<temp>\d+)", "temp"),
            ],
            "lock_door": [
                (r"lock\s+(?:the\s+)?(?:smart\s+)?(?:door|lock)", None),
            ],
            "unlock_door": [
                (r"unlock\s+(?:the\s+)?(?:smart\s+)?(?:door|lock)", None),
            ],
            "show_camera": [
                (r"show\s+(?:me\s+)?(?:camera|doorbell|door\s+camera)", None),
            ],
            "performance": [
                (r"(?:system\s+)?status", None),
                (r"(?:check\s+)?performance", None),
                (r"(?:memory|cpu|ram)\s+(?:usage)?", None),
            ],
            "optimize": [
                (r"optimize", None),
                (r"cleanup", None),
            ],
        })
        
        # ===== ALPHA: ACCESSIBILITY INNOVATION =====
        self.register_patterns("alpha", {
            "record": [
                (r"record\s+(?:this|macro)", None),
                (r"start\s+recording", None),
            ],
            "save_macro": [
                (r"save\s+macro\s+(?P<name>\w+)", "name"),
                (r"save\s+this", None),
            ],
            "cancel_recording": [
                (r"cancel\s+(?:recording|macro)", None),
                (r"stop\s+recording", None),
            ],
            "run_macro": [
                # "run mymacro" (no "macro" keyword) - macro execution
                # "run macro mymacro" (with "macro" keyword) - also macro
                (r"run\s+(?:macro\s+)?(?P<macro>\w+)", "macro"),
                (r"execute\s+macro\s+(?P<macro>\w+)", "macro"),
                (r"play\s+(?P<macro>\w+)", "macro"),
            ],
            "show_hints": [
                # "show commands", "what can I say", "available commands", "hints"
                # Must have "show" or "available" at start - NOT just "what"
                (r"show\s+commands", None),
                (r"(?:what\s+can\s+i\s+say|available\s+commands|hints)\b", None),
                (r"help\s+me\b", None),
            ],
            "screen_desc": [
                # "what's on screen" / "describe screen" / "read page" / "where am i"
                (r"what[']?s?\s+(?:on|there)\s+(?:on\s+)?(?:the\s+)?screen", None),
                (r"describe\s+(?:the\s+)?screen", None),
                (r"read\s+(?:the\s+)?page", None),
                (r"where\s+(?:am\s+i|is\s+the)", None),
            ],
            "find": [
                (r"find\s+(?P<element>.+)\b", "element"),
                (r"locate\s+(?P<element>.+)\b", "element"),
                (r"where\s+(?:is|are)\s+(?P<element>.+)\b", "element"),
            ],
            "learn": [
                (r"learn\s+this", None),
                (r"remember\s+this", None),
            ],
        })
        
        # ===== WINDOWS COMMANDS (MVP) =====
        # Only known desktop apps or .exe - avoids collision with browser/omni
        self.register_patterns("windows", {
            "launch": [
                # "open notepad", "open calculator" (known desktop apps only)
                (r"open\s+(?:the\s+)?(?P<app>" + "|".join(self.WINDOWS_KNOWN_APPS) + r")(?:\s+\w+)?", "app"),
                (r"launch\s+(?:the\s+)?(?P<app>" + "|".join(self.WINDOWS_KNOWN_APPS) + r")(?:\s+\w+)?", "app"),
                (r"start\s+(?:the\s+)?(?P<app>" + "|".join(self.WINDOWS_KNOWN_APPS) + r")(?:\s+\w+)?", "app"),
                # "open appname.exe" - explicit executable files
                (r"open\s+(?:the\s+)?(?P<app>\w+\.exe)", "app"),
                (r"launch\s+(?:the\s+)?(?P<app>\w+\.exe)", "app"),
            ],
            "close": [
                (r"close\s+(?:this\s+)?(?:window)?", None),
                (r"exit\s+(?:this\s+)?(?:window)?", None),
            ],
            "minimize": [
                (r"minimize\s+(?:this\s+)?(?:window)?", None),
            ],
            "maximize": [
                (r"maximize\s+(?:this\s+)?(?:window)?", None),
            ],
        })
        
        # ===== BROWSER COMMANDS (MVP) =====
        # Negative lookahead (?!\S+\.\w+$) prevents matching code file paths like "main.py"
        self.register_patterns("browser", {
            "navigate": [
                # "go to https://..." / "navigate to https://..." - explicit URLs first
                (r"go\s+to\s+(?P<url>https?://\S+)", "url"),
                (r"navigate\s+(?:to\s+)?(?P<url>https?://\S+)", "url"),
                # "open github" / "open reddit" - known shortcuts (no TLD needed)
                (r"open\s+(?:the\s+)?(?P<site>github|reddit|youtube|discord|notion|figma)\b", "site"),
                # "open google.com" - domains with TLD, NOT code files (.py, .js, etc.)
                (r"open\s+(?:the\s+)?(?P<site>\w+(?:\.\w+){1,3})\b", "site"),
                (r"(?:visit|load)\s+(?:the\s+)?(?P<site>\w+(?:\.\w+){1,3})", "site"),
            ],
            "search": [
                (r"search\s+(?:for\s+)?(?P<query>.+)", "query"),
                (r"google\s+(?P<query>.+)", "query"),
                (r"find\s+(?P<query>.+)", "query"),
            ],
            "click": [
                (r"click\s+(?:on\s+)?(?:the\s+)?(?:button\s+)?(?P<element>.+)", "element"),
                (r"press\s+(?:the\s+)?(?P<element>.+?)(?:\s+button)?$", "element"),
                (r"tap\s+(?:on\s+)?(?P<element>.+)", "element"),
            ],
            "type": [
                (r"type\s+(?P<text>.+)", "text"),
                (r"enter\s+(?P<text>.+)", "text"),
                (r"fill\s+(?P<text>.+)", "text"),
            ],
            "scroll": [
                (r"scroll\s+(up|down)", "direction"),
            ],
        })
        
        
        
        # ===== SYSTEM COMMANDS (MVP) =====
        self.register_patterns("system", {
            "screenshot": [
                (r"(?:take\s+)?(?:a\s+)?screenshot", None),
                (r"capture\s+screen", None),
            ],
            "copy": [
                (r"copy\s+(?:the\s+)?(?P<text>.+)", "text"),
                (r"(?:ctrl\s+\+\s*c)", None),
            ],
            "paste": [
                (r"paste", None),
                (r"(?:ctrl\s+\+\s*v)", None),
            ],
            "volume": [
                (r"volume\s+(up|down|mute)", "action"),
            ],
        })
        
        # ===== OMNI CONTROL (MVP) - LOWEST PRIORITY =====
        # Generic help/status - only matches standalone help commands
        # Never matches context-specific queries like "what's on screen" or "what's on my calendar"
        self.register_patterns("omni", {
            "help": [
                # "help" or "commands" alone - must be the ONLY content
                (r"^help$", None),
                (r"^commands$", None),
                # "what can you do" / "what's available" - standalone only
                (r"^(?:what\s+can\s+you\s+do|what[']?s\s+available)\??$", None),
                # "show me commands" - explicit phrase
                (r"^show\s+me\s+commands$", None),
            ],
            "settings": [
                # "open settings" → OMNI settings panel
                (r"open\s+(?:the\s+)?settings\b", None),
                # "settings" alone (not settings.com)
                (r"(?<!\.com)(?<!\.org)(?<!\.io)(?<!\.net)(?<!\.app)\bsettings\b", None),
                (r"(?:change|modify)\s+settings", None),
            ],
            "status": [
                (r"status", None),
                (r"(?:what[']?s\s+)?(?:your\s+)?state", None),
            ],
            "repeat": [
                # "do that again", "that again", "again", "repeat", "repeat that"
                (r"(?:do\s+(?:that\s+)?)?again\b", None),
                (r"\brepeat\b", None),
                (r"redo\b", None),
            ],
            "undo": [
                (r"\bundo\b", None),
                (r"go\s+back\b", None),
            ],
        })
        
        # ===== ACCESSIBILITY MODES =====
        self.register_patterns("accessibility", {
            "high_contrast": [
                (r"high\s+contrast", None),
            ],
            "large_text": [
                (r"large\s+text", None),
            ],
            "audio_only": [
                (r"audio\s+only", None),
                (r"voice\s+only", None),
            ],
        })
    
    def register_patterns(self, category: str, patterns: Dict[str, List[Tuple[str, str]]]) -> None:
        """Register command patterns for a category"""
        if category not in self._patterns:
            self._patterns[category] = {}
        
        for action, pattern_list in patterns.items():
            if action not in self._patterns[category]:
                self._patterns[category][action] = []
            self._patterns[category][action].extend(pattern_list)
    
    def parse(self, text: str) -> ParsedCommand:
        """Parse voice input into a structured command."""
        text = text.lower().strip()
        
        # Try each category and action in registration order
        for category, actions in self._patterns.items():
            for action, pattern_list in actions.items():
                for pattern, entity_name in pattern_list:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        entities = match.groupdict()
                        entities = {k: v for k, v in entities.items() if v is not None}
                        
                        # URL shortcut resolution
                        if "site" in entities:
                            site = entities["site"].lower()
                            if site in self.URL_SHORTCUTS:
                                entities["url"] = self.URL_SHORTCUTS[site]
                            elif "." in site:
                                entities["url"] = f"https://{site}"
                            else:
                                # No TLD and not in shortcuts - use .com as fallback
                                entities["url"] = f"https://{site}.com"
                            del entities["site"]
                        
                        action_name = f"{category}_{action}"
                        
                        return ParsedCommand(
                            action=action_name,
                            entities=entities,
                            original=text,
                            confidence=0.9,
                            patterns_matched=[pattern]
                        )
        
        # No pattern matched
        logger.warning(f"No pattern matched: '{text}'")
        
        return ParsedCommand(
            action="unknown",
            entities={"text": text},
            original=text,
            confidence=0.0,
            patterns_matched=[]
        )
    
    def parse_compound(self, text: str) -> List[ParsedCommand]:
        """Parse compound commands (separated by 'and', 'then', etc.)"""
        parts = re.split(r'\s+(?:and|then|also|plus)\s+', text, flags=re.IGNORECASE)
        commands = []
        for part in parts:
            cmd = self.parse(part.strip())
            commands.append(cmd)
        return commands
    
    def get_all_commands(self) -> Dict[str, List[str]]:
        """Get all available commands by category"""
        return {
            category: list(actions.keys())
            for category, actions in self._patterns.items()
        }
    
    def get_help_text(self) -> str:
        """Generate comprehensive help text"""
        lines = [
            "═══════════════════════════════════════════",
            "        OMNI VOICE COMMANDS",
            "═══════════════════════════════════════════",
            ""
        ]
        for category, actions in self._patterns.items():
            cat_title = category.upper().replace("_", " ")
            lines.append(f"── {cat_title} ──")
            for action, pattern_list in actions.items():
                patterns = [p[0] for p in pattern_list[:2]]
                lines.append(f"  • {action}: {patterns[0] if patterns else 'N/A'}")
            lines.append("")
        lines.append("Say 'help' anytime to see this list.")
        lines.append("───────────────────────────────────────────")
        return "\n".join(lines)