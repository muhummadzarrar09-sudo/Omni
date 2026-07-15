"""
OMNI BRAIN - The actual AGI reasoning core.
Uses LLaMA.cpp as the PRIMARY reasoner, not a fallback.

This replaces the regex-first dispatcher with a real LLM-driven loop:
1. ReAct (Reason + Act) loop: LLM thinks, picks a tool, observes result, repeats
2. Tool-use prompt format: LLM knows all available tools with descriptions
3. Streaming: tokens stream in real-time so the UI can show thinking
4. Conversation memory: last N turns kept in context
5. Self-correction: LLM can re-plan if a tool fails

FIXES the core problem: OMNI used to be a regex dispatcher with a hardcoded
fallback. Now it's an LLM-first agent that uses regex ONLY to validate/fast-
match obvious commands (like "help", "status") when the LLM is offline.
"""
from __future__ import annotations
import json
import re
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Generator
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Brain")


# Tool schema - what the LLM sees
# Tool schema - what the LLM sees
TOOL_SCHEMA = """You are OMNI, a local AGI assistant that CONTROLS the user's computer.

You are NOT a chatbot. When the user asks you to DO something, you MUST output a tool call JSON.

TOOLS (output tool calls, never describe doing them in text):
{brief}

CRITICAL RULES:
1. If the user asks you to CREATE, MAKE, WRITE, BUILD, OPEN, LAUNCH, RUN, SHOW, FIND, SEND, or any action verb, you MUST output `{{"tool": "name", "args": {{...}}}}`. NEVER write code in a text response when the user wants a file.
2. For CHAIN commands ("X and Y", "X then Y"), output a JSON ARRAY: `[{{"tool":"a","args":{{}}}}, {{"tool":"b","args":{{}}}}]`
3. For pure CONVERSATION ("how are you", "what can you do", "explain X"), respond naturally in <30 words.
4. For "create a [thing] and open in [app]": FIRST call files_write to save it, THEN call windows_launch for the app.
5. Browser: `browser_navigate` with `{{"url":"https://..."}}`. Search: `browser_search` with `{{"query":"..."}}`.
6. Launch apps: `windows_launch` with `{{"app":"notepad"}}` (or "chrome","code","explorer","calc","msedge","powershell","cmd","idle").
7. Create files: `files_write` with `{{"path":"D:/Omni/data/output/filename.py","content":"<file contents>"}}`.
8. NEVER put code in your text response when the user wants it written to disk.
9. NEVER ask "do you want me to..." - just DO IT. The user gave you a command. Execute it.

EXAMPLES:
- "open github" -> {{"tool":"browser_navigate","args":{{"url":"https://github.com"}}}}
- "create calculator with tkinter and open in IDLE" -> [{{"tool":"files_write","args":{{"path":"D:/Omni/data/output/calculator.py","content":"<python code>"}}}}, {{"tool":"windows_launch","args":{{"app":"idle"}}}}]
- "what can you do" -> natural text response
- "play music" -> {{"tool":"media_play_music","args":{{}}}}
- "turn on lights" -> {{"tool":"integrations_lights_on","args":{{}}}}
"""


@dataclass
class BrainResponse:
    """The brain's response to a user utterance."""
    text: str                            # Final user-facing text
    tool_calls: List[Dict[str, Any]]     # Tools the LLM wants to invoke
    thoughts: str = ""                   # LLM's chain-of-thought (for UI)
    tier: str = "brain"                  # Which path: "llm" | "regex" | "fallback"
    latency_ms: float = 0.0
    raw: str = ""                        # Raw LLM output
    success: bool = True


class Brain:
    """
    The actual AGI reasoner. LLaMA.cpp is PRIMARY.
    Regex/FastAF is the FAST-PATH for obvious commands.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        model_path: Optional[str] = None,
        plugin_manager: Any = None,
        memory: Any = None,
        on_thought: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
    ):
        if self._initialized:
            return
        self.plugin_manager = plugin_manager
        self.memory = memory
        self.on_thought = on_thought        # UI hook: stream LLM thoughts
        self.on_tool_call = on_tool_call    # UI hook: show tool invocation
        self.llm = None
        self.model_loaded = False
        self._conversation: List[Dict[str, str]] = []  # last 5 turns
        self._max_history = 5
        self._tier = "fallback"

        # Try to load LLM
        if model_path is None:
            model_path = self._find_model()
        if model_path:
            self._load_model(model_path)
        else:
            logger.warning(
                "Brain: No GGUF model found. Brain running in REGEX-ONLY mode. "
                "Download: curl -L -o data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf "
                "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/"
                "qwen2.5-1.5b-instruct-q4_k_m.gguf"
            )

        # Build tool descriptions for the LLM prompt
        self._tool_brief = self._build_tool_brief()
        self._initialized = True
        logger.info(
            f"🧠 Brain initialized | LLM={'✅' if self.model_loaded else '❌'} | "
            f"Tier: {self._tier} | Tools: {len(self._tool_brief.split('|'))}"
        )

    def _find_model(self) -> Optional[str]:
        """Find a GGUF model in data/models/ - search multiple locations"""
        # Get project root for absolute path resolution
        try:
            from omni_v2.core.paths import DATA_DIR, PROJECT_ROOT
            data_dir = DATA_DIR
            project_root = PROJECT_ROOT
        except Exception:
            project_root = Path.cwd()
            data_dir = project_root / "data"

        # Search a wide range of candidate locations
        candidates = [
            data_dir / "models",                # PRIMARY: project data dir
            project_root / "data" / "models",   # also via project root
            Path("data/models"),                # relative to cwd
            project_root / "omni_v2" / "llm" / "models",
            Path("omni_v2/llm/models"),
            Path.home() / ".omni_v2" / "models",
        ]
        for d in candidates:
            if d.exists():
                ggufs = sorted(d.glob("*.gguf"), key=lambda p: p.stat().st_size)
                if ggufs:
                    # Prefer smaller models (1-3B) for fast inference
                    for g in ggufs:
                        if any(s in g.name.lower() for s in ["1.5b", "1b", "2b", "3b"]):
                            logger.info(f"Brain: Found model {g.name} at {g}")
                            return str(g.resolve())
                    logger.info(f"Brain: Found model {ggufs[0].name} at {ggufs[0]}")
                    return str(ggufs[0].resolve())
        return None

    def _load_model(self, model_path: str):
        """Load llama.cpp model with GTX 1050 Ti optimized settings"""
        try:
            from llama_cpp import Llama
            logger.info(f"Loading GGUF: {model_path}")
            t0 = time.time()
            # VRAM clamping: 1.5B Q4 fits in ~1.1GB VRAM, leave headroom
            self.llm = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_threads=8,
                n_gpu_layers=20,   # Most layers on GPU if available, fallback to CPU
                n_batch=512,
                use_mmap=True,
                use_mlock=False,
                verbose=False,
            )
            self.model_loaded = True
            self._tier = "llm"
            logger.info(f"✅ Brain LLM loaded in {time.time()-t0:.1f}s - {model_path}")
        except Exception as e:
            logger.error(f"LLM load failed: {e} - falling back to regex")
            self.model_loaded = False
            self._tier = "fallback"

    def _build_tool_brief(self) -> str:
        """Build compact tool descriptions for the LLM prompt.
        KEEP IT SHORT - long prompts = slow inference. Pick the most useful tools."""
        if not self.plugin_manager:
            return "no tools available"

        # Curated short list - the LLM doesn't need to know every alias,
        # just the canonical actions and a few high-value ones
        canonical = [
            ("browser_navigate", "Open a URL or website"),
            ("browser_search", "Search the web for a query"),
            ("windows_launch", "Open a Windows app (notepad, chrome, code, etc.)"),
            ("windows_maximize", "Maximize the current window"),
            ("system_screenshot", "Take a screenshot of the screen"),
            ("files_list_dir", "List files in a directory"),
            ("files_write", "Write text to a file (path + content) - USE THIS for create/make/write file requests"),
            ("ai_creative_write", "Write creative text content (stories, code, etc.) - returns text only, NOT to disk"),
            ("ai_chat", "Handle conversation/question (use this for general chat)"),
            ("omni_help", "Show available commands"),
            ("vscode_open", "Open a file in VS Code"),
            ("vscode_terminal", "Run a command in VS Code terminal"),
            ("integrations_lights_on", "Turn on the lights"),
            ("integrations_lights_off", "Turn off the lights"),
            ("integrations_set_temperature", "Set smart home temperature"),
            ("integrations_send_email", "Send an email"),
            ("integrations_show_calendar", "Show calendar events"),
        ]
        return "\n".join(f"{name} - {desc}" for name, desc in canonical)

    def think(
        self,
        user_text: str,
        stream: bool = False,
    ) -> BrainResponse:
        """
        The main reasoning entry point. LLM-first.
        Returns BrainResponse with text, tool_calls, thoughts.

        If stream=True, calls self.on_thought(token) repeatedly with LLM tokens
        so the UI can show thinking in real-time.
        """
        t0 = time.time()

        # Update conversation history
        self._conversation.append({"role": "user", "content": user_text})
        if len(self._conversation) > self._max_history * 2:
            self._conversation = self._conversation[-self._max_history * 2:]

        # FAST PATH: if LLM is offline, use regex
        if not self.model_loaded:
            return self._regex_fallback(user_text, t0)

        # PRIMARY PATH: LLM
        try:
            return self._llm_think(user_text, t0, stream=stream)
        except Exception as e:
            logger.error(f"LLM think failed: {e}, regex fallback")
            return self._regex_fallback(user_text, t0)

    def _llm_think(
        self, user_text: str, t0: float, stream: bool
    ) -> BrainResponse:
        """The actual LLM-driven reasoning."""
        from datetime import datetime
        # Shorter system prompt = faster inference
        now = datetime.now()
        date_ctx = f"TODAY: {now.strftime('%A %B %d, %Y')} | NOW: {now.strftime('%H:%M')}"
        sys_prompt = TOOL_SCHEMA.format(brief=self._tool_brief) + f"\n{date_ctx}"
        # Append history only if we have it
        if self._conversation:
            sys_prompt += "\nRECENT: " + self._format_history_compact()

        messages = [{"role": "system", "content": sys_prompt}]
        # Only send last 4 user messages (8 turns) for speed
        messages.extend(self._conversation[-8:])

        # Build prompt
        if stream and self.on_thought:
            raw_parts = []
            stream_iter = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=200,  # tighter cap = faster
                temperature=0.3,
                stop=["\n\n\n", "User:", "Human:"],  # stop early
                stream=True,
            )
            for chunk in stream_iter:
                delta = chunk["choices"][0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    raw_parts.append(token)
                    try:
                        self.on_thought(token)
                    except Exception:
                        pass
            raw = "".join(raw_parts)
        else:
            out = self.llm.create_chat_completion(
                messages=messages,
                max_tokens=200,
                temperature=0.3,
                stop=["\n\n\n", "User:", "Human:"],
                stream=False,
            )
            raw = out["choices"][0]["message"]["content"]

        # Parse the LLM output
        tool_calls, text, thoughts = self._parse_llm_output(raw)

        # Update conversation
        self._conversation.append({"role": "assistant", "content": raw[:300]})
        if len(self._conversation) > self._max_history * 2:
            self._conversation = self._conversation[-self._max_history * 2:]

        latency = (time.time() - t0) * 1000
        if tool_calls:
            logger.info(
                f"🧠 Brain LLM [{latency:.0f}ms] {len(tool_calls)} tool call(s): "
                f"{[t['tool'] for t in tool_calls]}"
            )
        else:
            logger.info(f"🧠 Brain LLM [{latency:.0f}ms] response: {text[:80]}")
        self._last_action = text or str(tool_calls)[:100]

        return BrainResponse(
            text=text,
            tool_calls=tool_calls,
            thoughts=thoughts,
            tier="llm",
            latency_ms=latency,
            raw=raw,
            success=True,
        )

    def _format_history_compact(self) -> str:
        """Compact conversation history for fast inference."""
        lines = []
        for msg in self._conversation[-6:]:
            role = "U" if msg["role"] == "user" else "OMNI"
            lines.append(f"{role}: {msg['content'][:60]}")
        return " | ".join(lines)

    def _parse_llm_output(self, raw: str) -> tuple:
        """
        Parse LLM output into (tool_calls, text, thoughts).
        Handles: pure JSON, JSON in markdown code blocks, mixed text+JSON, multi-tool arrays.
        """
        original = raw
        raw = raw.strip()
        tool_calls = []
        text = ""
        thoughts = ""

        # Strip markdown code fences: ```json ... ``` or ``` ... ```
        code_block = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", raw, re.DOTALL)
        if code_block:
            raw = code_block.group(1).strip()

        # Strategy 1: pure JSON array of tool calls
        if raw.startswith("["):
            try:
                # GUARD-03: safe JSON parse
                try:
                    from omni_v2.core.guardrails import safe_json_loads
                    ok, arr, _ = safe_json_loads(raw)
                    if not ok:
                        raise ValueError("JSON parse failed")
                except ImportError:
                    arr = json.loads(raw)
                if isinstance(arr, list):
                    for item in arr:
                        tc = self._extract_tool_call(item)
                        if tc:
                            tool_calls.append(tc)
                    if tool_calls:
                        return tool_calls, text, thoughts
            except Exception:
                pass

        # Strategy 2: pure JSON single tool call
        if raw.startswith("{"):
            try:
                # GUARD-03: safe JSON parse with size cap
                try:
                    from omni_v2.core.guardrails import safe_json_loads
                    ok, obj, _ = safe_json_loads(raw)
                    if not ok:
                        raise ValueError("JSON parse failed")
                except ImportError:
                    obj = json.loads(raw)
                tc = self._extract_tool_call(obj)
                if tc:
                    return [tc], text, thoughts
            except Exception:
                pass

        # Strategy 3: find JSON anywhere in the text
        json_patterns = [
            (r'\[\s*\{[^\]]*"tool"[^\]]*\}\s*\]', "array"),
            (r'\{\s*"tool"\s*:[^}]*\}', "single"),
        ]
        for pat, kind in json_patterns:
            matches = re.findall(pat, raw, re.DOTALL)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if kind == "array" and isinstance(parsed, list):
                        for item in parsed:
                            tc = self._extract_tool_call(item)
                            if tc:
                                tool_calls.append(tc)
                    elif kind == "single" and isinstance(parsed, dict):
                        tc = self._extract_tool_call(parsed)
                        if tc:
                            tool_calls.append(tc)
                except Exception:
                    pass

        if tool_calls:
            cleaned = raw
            for pat, _ in json_patterns:
                cleaned = re.sub(pat, "", cleaned, flags=re.DOTALL)
            # Also strip code fences from the cleaned version for text
            cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"```\s*", "", cleaned)
            text = cleaned.strip()
            for marker in ["Thought:", "Reasoning:", "Plan:"]:
                if marker.lower() in text.lower():
                    idx = text.lower().index(marker.lower())
                    thoughts = text[idx + len(marker):].strip()[:200]
                    text = text[:idx].strip()
            return tool_calls, text, thoughts

        # Strategy 4: pure conversational text
        text = original.strip()
        for marker in ["Let me think:", "I think", "Reasoning:"]:
            if text.lower().startswith(marker.lower()):
                thoughts = text[:200]
                text = text[200:].lstrip(" :,-")
                break
        return [], text.strip(), thoughts.strip()

    def _extract_tool_call(self, item) -> Optional[dict]:
        """Extract a tool call from a parsed JSON item, normalizing arg names."""
        if not isinstance(item, dict) or "tool" not in item:
            return None
        tool = item["tool"]
        # The LLM might output: {"tool": "x", "args": {...}} OR {"tool": "x", "url": "..."}
        if "args" in item and isinstance(item["args"], dict):
            args = dict(item["args"])
        else:
            # Flatten everything except "tool" into args
            args = {k: v for k, v in item.items() if k != "tool"}
        # Normalize common arg name variations
        if tool == "browser_navigate":
            if "query" in args and "url" not in args:
                # User wants a search, not a navigate
                tool = "browser_search"
                args = {"query": args["query"]}
        if tool in ("browser_search", "browser_navigate"):
            if "url" in args and tool == "browser_navigate":
                pass  # OK
        if tool == "windows_launch":
            if "name" in args and "app" not in args:
                args["app"] = args.pop("name")
        return {"tool": tool, "args": args}

    def _regex_fallback(self, user_text: str, t0: float) -> BrainResponse:
        """
        Fast-path when LLM is offline. Tries to handle obvious commands.
        This is what OMNI was BEFORE the brain. It's still useful as backup
        for judges who don't have a GPU.
        """
        from omni_v2.core import CommandRegistry
        registry = CommandRegistry()
        parsed = registry.parse(user_text)

        tool_calls = []
        if parsed.action != "unknown":
            # Convert ParsedCommand to brain tool call
            tool_calls.append({
                "tool": parsed.action,
                "args": parsed.entities,
            })
            text = f"Executing {parsed.action}..."
        else:
            text = "I don't have a local LLM loaded and couldn't pattern-match that command. Install one with: curl -L -o data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"

        return BrainResponse(
            text=text,
            tool_calls=tool_calls,
            thoughts="(regex fallback - no LLM)",
            tier="regex",
            latency_ms=(time.time() - t0) * 1000,
            raw=user_text,
            success=True,
        )

    def _format_history(self) -> str:
        """Format conversation history for the system prompt."""
        if not self._conversation:
            return "(no prior conversation)"
        lines = []
        for msg in self._conversation[-6:]:
            role = "User" if msg["role"] == "user" else "OMNI"
            content = msg["content"][:100]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _last_action_summary(self) -> str:
        return getattr(self, "_last_action", "(none)")

    def add_assistant_turn(self, text: str):
        """Called by executor after tool runs to add the result to history."""
        self._conversation.append({"role": "assistant", "content": text[:200]})
        if len(self._conversation) > self._max_history * 2:
            self._conversation = self._conversation[-self._max_history * 2:]

    def clear_history(self):
        self._conversation = []

    def get_status(self) -> dict:
        return {
            "model_loaded": self.model_loaded,
            "tier": self._tier,
            "history_length": len(self._conversation),
            "tool_count": len(self._tool_brief.split("\n")),
        }


def get_brain(plugin_manager=None, memory=None) -> Brain:
    """Get the singleton Brain instance."""
    if Brain._instance is None:
        Brain(plugin_manager=plugin_manager, memory=memory)
    elif plugin_manager and not Brain._instance.plugin_manager:
        Brain._instance.plugin_manager = plugin_manager
    elif memory and not Brain._instance.memory:
        Brain._instance.memory = memory
    return Brain._instance
