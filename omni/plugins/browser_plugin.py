"""Browser Plugin - Chrome/Edge control via CDP"""
import asyncio
import json
from typing import Dict, Any
from loguru import logger
from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult

class BrowserPlugin(CommandPlugin):
    """Browser automation plugin using Chrome DevTools Protocol"""
    
    metadata = CommandMetadata(
        name="browser_navigate",
        category="browser",
        description="Control Chrome/Edge browser via voice",
        patterns=[r"open\s+(?P<site>\w+)", r"go\s+to\s+(?P<url>https?://[^\s]+)"],
        examples=["open github", "go to google.com"]
    )
    
    def __init__(self, port: int = 9222):
        super().__init__()
        self.port = port
        self._ws = None
        self._connected = False
    
    async def _connect(self) -> bool:
        if self._connected:
            return True
        try:
            import websockets
            import urllib.request
            response = urllib.request.urlopen(f"http://localhost:{self.port}/json/version")
            data = json.loads(response.read())
            ws_url = data.get("webSocketDebuggerUrl")
            if ws_url:
                self._ws = await websockets.connect(ws_url)
                self._connected = True
                logger.info(f"Connected to Chrome (port {self.port})")
                return True
        except Exception as e:
            logger.warning(f"Chrome not connected: {e}")
        return False
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        url = entities.get("url", "")
        
        if not url:
            site = entities.get("site", "").lower()
            shortcuts = {
                "youtube": "https://www.youtube.com",
                "github": "https://www.github.com",
                "google": "https://www.google.com",
                "chatgpt": "https://chat.openai.com",
            }
            url = shortcuts.get(site, f"https://{site}.com") if site else ""
        
        if not url:
            return CommandResult.error("No URL specified")
        
        try:
            if not await self._connect():
                return CommandResult.error("Chrome not connected. Launch with --force-renderer-accessibility")
            
            await self._ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": url}}))
            logger.info(f"Navigated to: {url}")
            return CommandResult.ok(f"Opened {url}")
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return CommandResult.error(f"Failed to open page")
