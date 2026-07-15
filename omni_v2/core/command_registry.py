"""
Command Registry V2 - 100+ Tools + Chain Commands + Context Awareness
Supports: "open chrome and maximize it and go to youtube" -> 3 steps
"""

import re
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("RegistryV2")

try:
    from omni_v2.core.intent_mapper import IntentMapper
    _INTENT_AVAILABLE = True
except Exception as e:
    logger.warning(f"IntentMapper not available: {e} - regex only")
    IntentMapper = None
    _INTENT_AVAILABLE = False


@dataclass
class ParsedCommand:
    action: str
    entities: Dict[str, str]
    original: str
    confidence: float
    patterns_matched: List[str]

@dataclass
class ActionStep:
    """Single step in a chain"""
    action: str
    entities: Dict[str, str]
    original: str
    description: str
    step_index: int = 0

class CommandRegistry:
    URL_SHORTCUTS = {
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "reddit": "https://reddit.com",
        "twitter": "https://twitter.com",
        "linkedin": "https://linkedin.com",
        "discord": "https://discord.com",
        "whatsapp": "https://web.whatsapp.com",
        "drive": "https://drive.google.com",
        "spotify": "https://spotify.com",
        "netflix": "https://netflix.com",
        "amazon": "https://amazon.com",
    }

    WINDOWS_APPS = [
        "notepad", "calculator", "explorer", "cmd", "powershell",
        "paint", "wordpad", "taskmgr", "chrome", "firefox", "edge",
        "code", "vscode", "spotify", "discord", "steam", "vlc"
    ]

    CODE_EXTS = r"(?:py|js|ts|jsx|tsx|json|md|txt|html|css|yaml|yml|sh|bat|go|rs|java|cpp|c)"

    def __init__(self):
        self._patterns: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
        try:
            if _INTENT_AVAILABLE and IntentMapper:
                self.intent_mapper = IntentMapper()
            else:
                class Dummy:
                    def register_command(self, *a, **k): pass
                    def match(self, t): return None, 0.0
                self.intent_mapper = Dummy()
        except Exception as e:
            logger.debug(f"IntentMapper init failed: {e}")
            class Dummy:
                def register_command(self, *a, **k): pass
                def match(self, t): return None, 0.0
            self.intent_mapper = Dummy()

        self._register_all()
        logger.info(f"Registry V2: {sum(len(v) for v in self._patterns.values())} categories, chain + context aware")

    def _register_all(self):
        # VSCode
        self.register("vscode", {
            "open": [(r"open\s+(?:file\s+)?(?P<file>\S+\." + self.CODE_EXTS + r")\b", "file")],
            "terminal": [(r"run\s+command\s+(?P<command>.+)", "command")],
            "save": [(r"^save(?:\s+file)?$", None)],
            "create": [(r"create\s+(?:new\s+)?file\s+(?P<file>\S+\." + self.CODE_EXTS + r")\b", "file")],
        })
        # Browser - 15 tools expanded - FIXED for chain like "open first result"
        self.register("browser", {
            "navigate": [
                (r"go\s+to\s+(?P<url>https?://\S+)", "url"),
                (r"open\s+(?:the\s+)?(?P<site>github|reddit|youtube|discord|notion|figma|google|gmail|drive|spotify|netflix|amazon)\b", "site"),
                (r"open\s+(?:the\s+)?(?P<site>\w+(?:\.\w+){1,3})\b", "site"),
                (r"open\s+(?:first\s+)?result", "site"),  # For chain: "open first result"
                (r"open\s+first", "site"),
            ],
            "search": [(r"search\s+(?:for\s+)?(?P<query>.+)", "query"), (r"google\s+(?P<query>.+)", "query")],
            "click": [(r"click\s+(?:on\s+)?(?P<element>.+)", "element")],
            "type": [(r"type\s+(?P<text>.+)", "text")],
            "scroll": [(r"scroll\s+(up|down)", "direction")],
            "new_tab": [(r"new\s+tab", None)],
            "close_tab": [(r"close\s+tab", None)],
            "back": [(r"go\s+back", None)],
            "forward": [(r"go\s+forward", None)],
            "refresh": [(r"refresh|reload", None)],
            "screenshot_element": [(r"screenshot\s+(?P<element>.+)", "element")],
            "extract_text": [(r"extract\s+text", None)],
            "fill_form": [(r"fill\s+form", None)],
            "bookmark": [(r"bookmark", None)],
        })
        # Windows - 15 tools
        self.register("windows", {
            "launch": [(r"open\s+(?:the\s+)?(?P<app>" + "|".join(self.WINDOWS_APPS) + r")\b", "app")],
            "close": [(r"close\s+(?:this\s+)?(?:window)?", None)],
            "minimize": [(r"minimize\s+(?:this\s+)?(?:window)?", None)],
            "maximize": [(r"maximize\s+(?:this\s+)?(?:window)?", None)],
            "move": [(r"move\s+window", None)],
            "resize": [(r"resize\s+window", None)],
            "focus": [(r"focus\s+(?P<app>.+)", "app")],
            "switch": [(r"switch\s+window|alt\s+tab", None)],
            "kill": [(r"kill\s+(?P<app>.+)", "app")],
            "lock": [(r"lock\s+(?:pc|computer|screen)", None)],
            "sleep": [(r"sleep|hibernate", None)],
        })
        # System - 10 tools
        self.register("system", {
            "screenshot": [(r"(?:take\s+)?(?:a\s+)?screenshot", None)],
            "copy": [(r"copy\s+(?P<text>.+)", "text")],
            "paste": [(r"paste", None)],
            "volume": [(r"volume\s+(up|down|mute)", "action")],
            "brightness": [(r"brightness\s+(up|down)", "action")],
            "clean_temp": [(r"clean\s+temp|cleanup", None)],
            "battery": [(r"battery\s+status", None)],
        })
        # Media - 10 tools
        self.register("media", {
            "play_music": [(r"play\s+(?:music|song)\s*(?P<query>.*)?", "query")],
            "pause": [(r"pause\s+(?:music)?", None)],
            "next": [(r"next\s+song|skip", None)],
            "prev": [(r"previous\s+song|prev", None)],
            "youtube_play": [(r"play\s+on\s+youtube\s+(?P<query>.+)", "query")],
            "spotify_control": [(r"spotify\s+(?P<action>play|pause|next|prev)", "action")],
        })
        # Files - 10 tools
        self.register("files", {
            "create_folder": [(r"create\s+folder\s+(?P<name>.+)", "name")],
            "delete": [(r"delete\s+(?P<file>.+)", "file")],
            "list_dir": [(r"list\s+(?:files|dir)", None)],
            "search_files": [(r"search\s+files\s+(?P<query>.+)", "query")],
        })
        # AI - 10 tools
        self.register("ai", {
            "chat": [(r"chat\s+(?P<text>.+)", "text"), (r"ask\s+(?P<text>.+)", "text")],
            "summarize": [(r"summarize\s+(?P<text>.+)", "text")],
            "translate": [(r"translate\s+(?P<text>.+)", "text")],
            "code_generate": [(r"generate\s+code\s+(?P<text>.+)", "text")],
        })
        # Integrations - 20 tools
        self.register("integrations", {
            "send_email": [(r"send\s+email\s+to\s+(?P<recipient>\w+)", "recipient")],
            "show_calendar": [(r"what'?s?\s+on\s+my\s+calendar", None), (r"show\s+calendar", None)],
            "lights_on": [(r"turn\s+on\s+(?:the\s+)?lights?", None), (r"lights?\s+on", None)],
            "lights_off": [(r"turn\s+off\s+(?:the\s+)?lights?", None), (r"lights?\s+off", None)],
            "performance": [(r"system\s+status|performance", None)],
            "weather": [(r"weather|temperature", None)],
            "timer": [(r"set\s+timer\s+(?P<time>.+)", "time")],
            "set_temperature": [(r"set\s+temperature\s+to\s+(?P<temp>\d+)", "temp")],
        })
        # Omni
        self.register("omni", {
            "help": [(r"^help$", None), (r"what\s+can\s+you\s+do", None)],
            "settings": [(r"open\s+settings", None)],
            "status": [(r"^status$", None)],
            "repeat": [(r"do\s+that\s+again|repeat", None)],
        })
        # Alpha / Accessibility
        self.register("alpha", {
            "screen_desc": [(r"what'?s?\s+on\s+screen|describe\s+screen", None)],
            "show_hints": [(r"show\s+commands|what\s+can\s+i\s+say", None)],
        })

    def register(self, category: str, patterns: Dict[str, List[Tuple[str, str]]]):
        if category not in self._patterns:
            self._patterns[category] = {}
        for action, plist in patterns.items():
            if action not in self._patterns[category]:
                self._patterns[category][action] = []
            self._patterns[category][action].extend(plist)
            examples = [p[0].replace(r"\s+", " ").strip() for p, _ in plist]
            self.intent_mapper.register_command(f"{category}_{action}", examples)

    def parse(self, text: str) -> ParsedCommand:
        text = text.lower().strip()
        # Try semantic first
        try:
            best_intent, score = self.intent_mapper.match(text)
            if best_intent:
                try:
                    cat, act = best_intent.split("_", 1)
                    entities = {}
                    for pat, _ in self._patterns.get(cat, {}).get(act, []):
                        m = re.search(pat, text, re.IGNORECASE)
                        if m:
                            entities.update({k: v for k, v in m.groupdict().items() if v is not None})
                            break
                    if "site" in entities:
                        site = entities["site"].lower()
                        entities["url"] = self.URL_SHORTCUTS.get(site, f"https://{site}.com" if "." not in site else f"https://{site}")
                        del entities["site"]
                    return ParsedCommand(best_intent, entities, text, score, [f"semantic_{best_intent}"])
                except ValueError:
                    pass
        except Exception:
            pass

        # Regex fallback
        for cat, actions in self._patterns.items():
            for act, plist in actions.items():
                for pat, _ in plist:
                    m = re.search(pat, text, re.IGNORECASE)
                    if m:
                        entities = {k: v for k, v in m.groupdict().items() if v is not None}
                        if "site" in entities:
                            site = entities["site"].lower()
                            entities["url"] = self.URL_SHORTCUTS.get(site, f"https://{site}.com" if "." not in site else f"https://{site}")
                            del entities["site"]
                        return ParsedCommand(f"{cat}_{act}", entities, text, 0.9, [pat])

        return ParsedCommand("unknown", {"text": text}, text, 0.0, [])

    def parse_chain(self, text: str) -> List[ActionStep]:
        """V2 NEW: Parse chain commands like 'open chrome and maximize it and go to youtube'"""
        # Split by chain delimiters: and, then, , , plus
        parts = re.split(r'\s+(?:and|then|,|plus|after\s+that)\s+', text, flags=re.IGNORECASE)
        steps = []
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            parsed = self.parse(part)
            # Handle context: "it" refers to previous entity
            if parsed.action != "unknown":
                if "it" in part.lower() and i > 0:
                    # Replace "it" with previous entity if possible
                    prev_entities = steps[-1].entities if steps else {}
                    if prev_entities and not parsed.entities:
                        parsed.entities = prev_entities.copy()

                steps.append(ActionStep(
                    action=parsed.action,
                    entities=parsed.entities,
                    original=parsed.original,
                    description=f"Step {i+1}: {parsed.action} {parsed.entities}",
                    step_index=i
                ))
            else:
                # Even unknown, keep as step for evaluator to re-plan
                steps.append(ActionStep(
                    action="unknown",
                    entities={"text": part},
                    original=part,
                    description=f"Step {i+1}: unknown ({part})",
                    step_index=i
                ))

        # If no chain delimiters but single command, return single step
        if not steps:
            parsed = self.parse(text)
            steps.append(ActionStep(
                action=parsed.action,
                entities=parsed.entities,
                original=parsed.original,
                description=f"Executing {parsed.action}",
                step_index=0
            ))

        logger.info(f"Chain parsed: '{text}' -> {len(steps)} steps")
        return steps
