"""
Command Registry - Pattern-based Command Parser
Maps natural language to structured commands for ALL phases (MVP + ALPHA + BETA)
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
        "github": "https://www.github.com",
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
    }
    
    def __init__(self):
        self._patterns: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
        self._register_all_patterns()
        logger.info("CommandRegistry initialized with all phases")
    
    def _register_all_patterns(self) -> None:
        """Register patterns for MVP + ALPHA + BETA"""
        
        # ===== BROWSER COMMANDS (MVP) =====
        self.register_patterns("browser", {
            "navigate": [
                (r"open\s+(?:the\s+)?(?:website\s+)?(?P<site>\w+(?:\.\w+)?)", "site"),
                (r"go\s+to\s+(?P<url>https?://[^\s]+)", "url"),
                (r"navigate\s+(?:to\s+)?(?P<url>https?://[^\s]+)", "url"),
                (r"(?:visit|load)\s+(?P<site>\w+(?:\.\w+)?)", "site"),
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
        
        # ===== WINDOWS COMMANDS (MVP) =====
        self.register_patterns("windows", {
            "launch": [
                (r"open\s+(?:the\s+)?(?P<app>\w+(?:\s+\w+)?)", "app"),
                (r"launch\s+(?:the\s+)?(?P<app>\w+(?:\s+\w+)?)", "app"),
                (r"start\s+(?:the\s+)?(?P<app>\w+(?:\s+\w+)?)", "app"),
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
        
        # ===== VS CODE COMMANDS (MVP) =====
        self.register_patterns("vscode", {
            "open": [
                (r"open\s+(?:file\s+)?(?P<file>[^\s]+(?:\.\w+)?)", "file"),
                (r"show\s+(?:file\s+)?(?P<file>[^\s]+(?:\.\w+)?)", "file"),
                (r"find\s+file\s+(?P<file>[^\s]+(?:\.\w+)?)", "file"),
            ],
            "terminal": [
                (r"run\s+(?:command\s+)?(?P<command>.+)", "command"),
                (r"execute\s+(?P<command>.+)", "command"),
                (r"terminal\s+(?P<command>.+)", "command"),
            ],
            "save": [
                (r"save\s+(?:file)?", None),
                (r"(?:ctrl\s+\+\s*)?s\s+save", None),
            ],
            "create": [
                (r"create\s+(?:new\s+)?file\s+(?P<file>.+)", "file"),
                (r"new\s+file\s+(?P<file>.+)", "file"),
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
        
        # ===== OMNI CONTROL (MVP) =====
        self.register_patterns("omni", {
            "help": [
                (r"(?:what\s+can\s+you\s+do|help|commands|what[']?s\s+available)", None),
            ],
            "settings": [
                (r"(?:open\s+)?settings", None),
                (r"(?:change|modify)\s+settings", None),
            ],
            "status": [
                (r"status", None),
                (r"(?:what[']?s\s+)?(?:your\s+)?state", None),
            ],
            "repeat": [
                (r"(?:do\s+)?(?:that\s+)?again", None),
                (r"repeat\s+(?:that\s+)?", None),
                (r"redo", None),
            ],
            "undo": [
                (r"undo", None),
                (r"go\s+back", None),
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
                (r"run\s+(?P<macro>\w+)", "macro"),
                (r"execute\s+macro\s+(?P<macro>\w+)", "macro"),
            ],
            "show_hints": [
                (r"(?:what\s+can\s+i\s+say|available\s+commands|hints)", None),
                (r"show\s+commands", None),
                (r"help\s+me", None),
            ],
            "screen_desc": [
                (r"what[']?s?\s+(?:on\s+)?screen", None),
                (r"describe\s+screen", None),
                (r"read\s+page", None),
                (r"where\s+(?:am\s+i|is)", None),
            ],
            "find": [
                (r"find\s+(?P<element>.+)", "element"),
                (r"locate\s+(?P<element>.+)", "element"),
                (r"where\s+(?:is|are)\s+(?P<element>.+)", "element"),
            ],
            "learn": [
                (r"learn\s+this", None),
                (r"remember\s+this", None),
            ],
        })
        
        # ===== BETA: INTEGRATIONS =====
        self.register_patterns("integrations", {
            "send_email": [
                (r"(?:send|compose)\s+(?:an?\s+)?email\s+(?:to\s+)?(?P<recipient>[^\s]+)", "recipient"),
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
                (r"(?:turn\s+)?off\s+(?:the\s+)?lights?", None),
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
        
        # Try each category and action
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
                            else:
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
                patterns = [p[0] for p in pattern_list[:2]]  # Show max 2
                lines.append(f"  • {action}: {patterns[0] if patterns else 'N/A'}")
            
            lines.append("")
        
        lines.append("Say 'help' anytime to see this list.")
        lines.append("───────────────────────────────────────────")
        
        return "\n".join(lines)