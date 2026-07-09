"""Browser Plugin - Chrome/Edge control via CDP"""
import asyncio
import json
import subprocess
import sys
from typing import Dict, Any
from loguru import logger

from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class BrowserPlugin(CommandPlugin):
    """Browser automation plugin using Chrome DevTools Protocol.
    
    URL is resolved by command_registry.py (handles shortcuts like
    "open github" → https://github.com, TLDs like "open google.com",
    and explicit URLs like "go to https://...").
    This plugin just navigates to whatever URL it receives.
    """
    
    metadata = CommandMetadata(
        name="browser_navigate",
        category="browser",
        description="Control Chrome/Edge browser via voice",
        patterns=[],  # All URL routing handled by command_registry
        examples=["open github", "search for python", "go to google.com"]
    )
    
    def __init__(self, port: int = 9222):
        super().__init__()
        self.port = port
        self._ws = None
        self._connected = False
    
    async def _connect(self) -> bool:
        """Connect to Chrome via CDP."""
        if self._connected and self._ws is not None:
            return True
        try:
            import urllib.request
            response = urllib.request.urlopen(
                f"http://localhost:{self.port}/json/version", timeout=5
            )
            data = json.loads(response.read())
            ws_url = data.get("webSocketDebuggerUrl")
            if ws_url:
                import websockets
                self._ws = await websockets.connect(ws_url, ping_timeout=10)
                self._connected = True
                logger.info(f"Connected to Chrome (port {self.port})")
                return True
        except Exception as e:
            logger.warning(f"Chrome CDP not connected: {e}")
            self._connected = False
        return False
    
    async def _send_cdp(self, method: str, params: dict = None) -> dict:
        """Send CDP command and return response."""
        if not self._ws:
            return {}
        msg_id = 1
        await self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
        try:
            resp = await asyncio.wait_for(self._ws.recv(), timeout=10)
            return json.loads(resp)
        except Exception:
            return {}
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any]) -> CommandResult:
        """Navigate browser to URL."""
        url = entities.get("url", "").strip()
        
        if not url:
            return CommandResult.error(
                "No URL specified. Try 'open github' or 'go to https://google.com'"
            )
        
        # Try CDP first (Chrome must be running with --remote-debugging-port=9222)
        if await self._connect():
            try:
                await self._send_cdp("Page.navigate", {"url": url})
                logger.info(f"Navigated to: {url}")
                return CommandResult.ok(f"Opened {url}")
            except Exception as e:
                logger.error(f"CDP navigation error: {e}")
        
        # Fallback: open URL via OS default browser (always works)
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", "", url], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
            logger.info(f"Opened URL via default browser: {url}")
            return CommandResult.ok(
                f"Opened {url} in your default browser.\n"
                "For in-browser control, launch Chrome with:\n"
                "chrome.exe --remote-debugging-port=9222"
            )
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            return CommandResult.error(f"Could not open {url}")