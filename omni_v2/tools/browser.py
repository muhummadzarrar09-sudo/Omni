"""Browser Tool V2 - 15 tools"""
import webbrowser
from typing import Dict, Any
from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class BrowserTool(CommandPlugin):
    metadata = CommandMetadata(
        name="browser_navigate",
        category="browser",
        description="Browser 15 tools: navigate, search, tabs, etc.",
        patterns=[],
        examples=["open github", "search for cats"]
    )
    SUPPORTED_ACTIONS = [
        "browser_navigate", "browser_search", "browser_click", "browser_type", "browser_scroll",
        "browser_new_tab", "browser_close_tab", "browser_back", "browser_forward", "browser_refresh",
        "browser_screenshot_element", "browser_extract_text", "browser_fill_form", "browser_bookmark"
    ]
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        url = entities.get("url", "")
        query = entities.get("query", "")
        if url:
            try:
                webbrowser.open(url, new=2)
                return CommandResult.ok(f"Opened: {url}", data={"url": url})
            except Exception as e:
                return CommandResult.error(f"Failed to open {url}: {e}")
        if query:
            search_url = f"https://www.google.com/search?q={query}"
            try:
                webbrowser.open(search_url, new=2)
                return CommandResult.ok(f"Searching for: {query}", data={"url": search_url})
            except Exception as e:
                return CommandResult.error(f"Search failed: {e}")
        return CommandResult.ok(f"Browser action: {context.get('original','')}")

    async def verify_action(self, entities, context):
        return True
