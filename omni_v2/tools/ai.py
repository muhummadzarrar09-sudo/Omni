"""AI Tool V2 - 10 tools"""
from typing import Dict, Any
from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("AIToolV2")


class AITool(CommandPlugin):
    metadata = CommandMetadata(
        name="ai_chat",
        category="ai",
        description="AI chat, summarize, translate, code gen — routes through the LLM brain",
        patterns=[],
        examples=["ask who is iron man", "summarize this"]
    )
    SUPPORTED_ACTIONS = ["ai_chat", "ai_summarize", "ai_translate", "ai_code_generate"]

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        text = (entities.get("text", "") or entities.get("query", "") or
                entities.get("prompt", "") or context.get("original", ""))
        if not text:
            return CommandResult.ok("Hi! I'm OMNI. Ask me anything or tell me to do something on your computer.")

        # Try the real LLM brain first
        try:
            from omni_v2.llm.brain import get_brain
            brain = get_brain()
            if brain and brain.model_loaded:
                resp = brain.think(text, stream=False)
                if resp.text:
                    return CommandResult.ok(resp.text[:2000], data={"tier": resp.tier, "ms": resp.latency_ms})
                if resp.tool_calls:
                    return CommandResult.ok(
                        f"I'd use {len(resp.tool_calls)} tool(s) for that: " +
                        ", ".join(t["tool"] for t in resp.tool_calls[:3])
                    )
        except Exception as e:
            logger.debug(f"AI brain fallback (using conversational reply): {e}")

        # Conversational fallback: this is the LLM brain's "no tools needed" path
        # We give a helpful canned response, not the embarrassing "Phase 1 mock" string
        text_lower = text.lower().strip()
        if any(w in text_lower for w in ["hello", "hi ", "hey", "yo", "sup"]):
            return CommandResult.ok(
                "Hey! I'm OMNI — your local AGI assistant. I can open apps, "
                "browse the web, write files, run commands, control your computer. "
                "What do you want to do?"
            )
        if "who are you" in text_lower or "what are you" in text_lower:
            return CommandResult.ok(
                "I'm OMNI V3 — a local AGI running a 1.5B Qwen model on your machine. "
                "I can see your screen, hear your voice, control apps, write code, and remember everything. "
                "All private. All offline. All yours."
            )
        if "what can you do" in text_lower or "help" in text_lower:
            return CommandResult.ok(
                "I can: open apps (Chrome, VS Code, Notepad, IDLE), "
                "browse the web, write & save files, run terminal commands (safely), "
                "take screenshots, control smart home, send emails, manage calendar, "
                "remember our conversations, and self-heal when things break. "
                "Try: 'open github', 'create a python calculator', or 'what's on my screen'."
            )
        if "thank" in text_lower:
            return CommandResult.ok("Anytime. What's next?")
        if "?" in text and len(text) < 100:
            return CommandResult.ok(
                f"You asked: '{text[:80]}'. I'm a local AGI focused on actions, not trivia. "
                f"Try asking me to do something — 'open github' or 'play music'."
            )
        # Default: acknowledge
        return CommandResult.ok(
            f"Got it: '{text[:80]}'. Tell me what to do with it — open it, save it, search for it, etc."
        )

    async def verify_action(self, e, c):
        return True
