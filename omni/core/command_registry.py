"""Command Registry - Pattern-based Command Parser"""
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from loguru import logger

@dataclass
class ParsedCommand:
    action: str
    entities: Dict[str, str]
    original: str
    confidence: float
    patterns_matched: List[str]

class CommandRegistry:
    """Registry of command patterns. Maps natural language to structured commands."""
    
    URL_SHORTCUTS = {
        "youtube": "https://www.youtube.com",
        "github": "https://www.github.com",
        "google": "https://www.google.com",
        "chatgpt": "https://chat.openai.com",
        "gmail": "https://www.gmail.com",
    }
    
    def __init__(self):
        self._patterns: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
        self._register_default_patterns()
        logger.info("CommandRegistry initialized")
    
    def _register_default_patterns(self) -> None:
        # Browser
        self.register_patterns("browser", {
            "navigate": [
                (r"open\s+(?:the\s+)?(?:website\s+)?(?P<site>\w+(?:\.\w+)?)", "site"),
                (r"go\s+to\s+(?P<url>https?://[^\s]+)", "url"),
                (r"navigate\s+(?:to\s+)?(?P<url>https?://[^\s]+)", "url"),
            ],
            "search": [
                (r"search\s+(?:for\s+)?(?P<query>.+)", "query"),
                (r"google\s+(?P<query>.+)", "query"),
            ],
            "click": [
                (r"click\s+(?:on\s+)?(?:the\s+)?(?P<element>.+)", "element"),
            ],
        })
        # Windows
        self.register_patterns("windows", {
            "launch": [
                (r"open\s+(?:the\s+)?(?P<app>\w+)", "app"),
                (r"launch\s+(?:the\s+)?(?P<app>\w+)", "app"),
            ],
            "close": [(r"close\s+(?:this\s+)?(?:window)?", None)],
        })
        # VS Code
        self.register_patterns("vscode", {
            "open": [(r"open\s+(?:file\s+)?(?P<file>[^\s]+(?:\.\w+)?)", "file")],
            "terminal": [(r"run\s+(?:command\s+)?(?P<command>.+)", "command")],
        })
        # System
        self.register_patterns("system", {
            "screenshot": [(r"(?:take\s+)?(?:a\s+)?screenshot", None)],
        })
        # OMNI
        self.register_patterns("omni", {
            "help": [(r"(?:what\s+can\s+you\s+do|help|commands)", None)],
            "settings": [(r"(?:open\s+)?settings", None)],
            "status": [(r"status", None)],
        })
    
    def register_patterns(self, category: str, patterns: Dict[str, List[Tuple[str, str]]]) -> None:
        if category not in self._patterns:
            self._patterns[category] = {}
        for action, pattern_list in patterns.items():
            if action not in self._patterns[category]:
                self._patterns[category][action] = []
            self._patterns[category][action].extend(pattern_list)
    
    def parse(self, text: str) -> ParsedCommand:
        text = text.lower().strip()
        
        for category, actions in self._patterns.items():
            for action, pattern_list in actions.items():
                for pattern, entity_name in pattern_list:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        entities = match.groupdict()
                        entities = {k: v for k, v in entities.items() if v is not None}
                        
                        if "site" in entities:
                            site = entities["site"].lower()
                            if site in self.URL_SHORTCUTS:
                                entities["url"] = self.URL_SHORTCUTS[site]
                            else:
                                entities["url"] = f"https://{site}.com"
                            del entities["site"]
                        
                        return ParsedCommand(
                            action=f"{category}_{action}",
                            entities=entities,
                            original=text,
                            confidence=0.9,
                            patterns_matched=[pattern]
                        )
        
        return ParsedCommand(
            action="unknown",
            entities={"text": text},
            original=text,
            confidence=0.0,
            patterns_matched=[]
        )
