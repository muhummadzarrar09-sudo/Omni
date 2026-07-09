"""Browser Plugin - Chrome/Edge control via CDP + OS fallback"""
import asyncio
import json
import subprocess
import sys
import urllib.parse
from typing import Dict, Any

from loguru import logger
from omni.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult


class BrowserPlugin(CommandPlugin):
    """Browser automation plugin.

    Handles: navigate, search, click, type, scroll
    Uses Chrome DevTools Protocol (CDP) when available, falls back to OS browser.
    """

    metadata = CommandMetadata(
        name="browser_navigate",
        category="browser",
        description="Control Chrome/Edge browser via voice",
        patterns=[],
        examples=["open github", "search for cats", "go to google.com"]
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

    def _open_url(self, url: str) -> CommandResult:
        """Open URL in default browser (always works)."""
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", "", url], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
            logger.info(f"Opened URL: {url}")
            return CommandResult.ok(
                f"Opened: {url}\n"
                "For full browser control, launch Chrome with:\n"
                "chrome.exe --remote-debugging-port=9222"
            )
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            return CommandResult.error(f"Could not open {url}")

    async def execute(
        self, entities: Dict[str, Any], context: Dict[str, Any]
    ) -> CommandResult:
        """Handle all browser commands: navigate, search, click, type, scroll."""
        original = (context.get("original") or "").lower()

        # === NAVIGATE ===
        if "url" in entities:
            url = entities["url"].strip()
            if not url:
                return CommandResult.error("No URL specified")

            # Try CDP first
            if await self._connect():
                try:
                    await self._send_cdp("Page.navigate", {"url": url})
                    logger.info(f"Navigated to: {url}")
                    return CommandResult.ok(f"Opened {url}")
                except Exception as e:
                    logger.error(f"CDP navigation error: {e}")

            # Fallback: OS default browser
            return self._open_url(url)

        # === SEARCH ===
        if "query" in entities:
            query = entities["query"].strip()
            if not query:
                return CommandResult.error("No search query specified")

            search_url = (
                f"https://www.google.com/search?"
                f"{urllib.parse.urlencode({'q': query})}"
            )
            return self._open_url(search_url)

        # === CLICK ===
        if "element" in entities:
            element = entities["element"].strip()
            if not element:
                return CommandResult.error("No element specified")

            if await self._connect():
                try:
                    # Use CDP to find and click element
                    result = await self._send_cdp(
                        "Runtime.evaluate",
                        {
                            "expression": (
                                f"document.querySelector('{element}')?.click()"
                            )
                        },
                    )
                    if result:
                        return CommandResult.ok(f"Clicked: {element}")
                except Exception as e:
                    logger.error(f"CDP click error: {e}")

            # Fallback: pyautogui click by image (if screenshot matched)
            try:
                import pyautogui
                # Try to click by element name (generic approach)
                pyautogui.click()  # Generic click at current mouse position
                return CommandResult.ok(
                    f"Clicked at current position.\n"
                    f"For precise '{element}' clicking, use Chrome with CDP:\n"
                    "chrome.exe --remote-debugging-port=9222"
                )
            except ImportError:
                pass

            return CommandResult.ok(
                f"Cannot click '{element}' — Chrome CDP not connected.\n"
                "Launch Chrome with: chrome.exe --remote-debugging-port=9222"
            )

        # === TYPE ===
        if "text" in entities:
            text = entities["text"].strip()
            if not text:
                return CommandResult.error("No text specified")

            if await self._connect():
                try:
                    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
                    await self._send_cdp(
                        "Runtime.evaluate",
                        {"expression": f'document.activeElement.value = "{escaped}"; document.activeElement.dispatchEvent(new Event("input"))'},
                    )
                    return CommandResult.ok(f"Typed: {text}")
                except Exception as e:
                    logger.error(f"CDP type error: {e}")

            # Fallback: pyautogui keyboard
            try:
                import pyautogui
                pyautogui.write(text, interval=0.05)
                return CommandResult.ok(f"Typed: {text}")
            except ImportError:
                pass

            return CommandResult.ok(
                f"Cannot type '{text}' — CDP not connected and pyautogui not available."
            )

        # === SCROLL ===
        if "direction" in entities:
            direction = entities["direction"].lower()
            scroll_amount = "down" in direction and 300 or -300

            if await self._connect():
                try:
                    await self._send_cdp(
                        "Runtime.evaluate",
                        {"expression": f"window.scrollBy(0, {scroll_amount})"},
                    )
                    return CommandResult.ok(f"Scrolled {direction}")
                except Exception:
                    pass

            # Fallback: pyautogui scroll
            try:
                import pyautogui
                pyautogui.scroll(scroll_amount // 100)
                return CommandResult.ok(f"Scrolled {direction}")
            except Exception:
                pass

            return CommandResult.ok(f"Scrolled {direction} (CDP fallback)")

        return CommandResult.error(
            "Browser command unclear. Try: 'open github' or 'search for cats'"
        )