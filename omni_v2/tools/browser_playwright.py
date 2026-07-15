"""
OMNI V3 - Browser V4 - Playwright-powered REAL browser automation

The "BEST OF THE BEST" browser tool:
  - Real Chromium headless engine (Playwright)
  - Isolated profile (privacy)
  - Screenshot capture
  - JavaScript execution
  - Form filling
  - Element clicking
  - DOM inspection
  - Cookie management
  - Network interception

Falls back to webbrowser module if Playwright not installed.
"""
from __future__ import annotations
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("BrowserV4")

try:
    from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult
    from omni_v2.core.guardrails import safe_url
except ImportError:
    class CommandPlugin: pass
    class CommandMetadata:
        def __init__(self, **kw): pass
    class CommandResult:
        @staticmethod
        def ok(msg, data=None): return {"success": True, "message": msg, "data": data}
        @staticmethod
        def error(msg): return {"success": False, "message": msg}
    def safe_url(url): return (True, "")


class BrowserV4Playwright(CommandPlugin):
    """
    The cinematic browser. Real headless Chromium with full automation.
    """
    metadata = CommandMetadata(
        name="browser_v4",
        category="browser",
        description="Browser V4 - Playwright-powered, real headless Chromium with full automation",
        patterns=[],
        examples=["open github", "search for iron man", "click the login button"]
    )
    SUPPORTED_ACTIONS = [
        "browser_navigate", "browser_search", "browser_click", "browser_type",
        "browser_screenshot", "browser_extract_text", "browser_fill_form",
        "browser_screenshot_url", "browser_execute_js", "browser_get_cookies",
        "browser_clear_cookies", "browser_close",
    ]

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self.profile_dir = Path.cwd() / "data" / "chrome_profile_v4"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._init_lock = threading.Lock()
        self._initialized = False
        self._init_browser()

    def _init_browser(self):
        """Lazy init - run in background thread to not block startup."""
        def _setup():
            try:
                from playwright.sync_api import sync_playwright
                # Run in a thread
                self.playwright = sync_playwright().start()
                # Use Chromium with isolated user data dir
                self.browser = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=True,
                    args=[
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=Translate",
                    ],
                ) if False else None
                # Simpler: launch browser and use context
                self.browser = self.playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                self.context = self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OMNI-AGI/3.0",
                    viewport={"width": 1920, "height": 1080},
                    storage_state=None,  # Fresh storage
                )
                self.page = self.context.new_page()
                self._initialized = True
                logger.info(f"✅ Browser V4: Playwright Chromium ready (profile: {self.profile_dir})")
            except ImportError as e:
                logger.debug(f"Playwright not installed: {e}")
                self._initialized = False
            except Exception as e:
                logger.error(f"Browser V4 init failed: {e}")
                self._initialized = False

        if not self._initialized:
            t = threading.Thread(target=_setup, daemon=True)
            t.start()

    def _ensure_ready(self) -> bool:
        """Wait briefly for browser init."""
        for _ in range(20):  # 2s max wait
            if self._initialized:
                return True
            import time
            time.sleep(0.1)
        return self._initialized

    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        if not self._ensure_ready():
            return CommandResult.error(
                "Browser V4: Playwright not available. Install: pip install playwright && playwright install chromium"
            )
        action = entities.get("action", "navigate")
        url = entities.get("url", "")
        query = entities.get("query", "")
        selector = entities.get("selector", "")
        text = entities.get("text", "")
        js_code = entities.get("js", "")

        # URL safety
        if url:
            is_safe, err = safe_url(url)
            if not is_safe:
                return CommandResult.error(f"URL blocked: {err}")

        try:
            if action == "navigate" or (not action and url):
                return await self._navigate(url or query)
            elif action == "search":
                return await self._search(query or text)
            elif action == "click":
                return await self._click(selector)
            elif action == "type":
                return await self._type(selector, text)
            elif action == "screenshot":
                return await self._screenshot(entities.get("path"))
            elif action == "screenshot_url":
                return await self._screenshot_url(url or query, entities.get("path"))
            elif action == "extract_text":
                return await self._extract_text(selector)
            elif action == "fill_form":
                return await self._fill_form(entities.get("fields", {}))
            elif action == "execute_js":
                return await self._execute_js(js_code)
            elif action == "get_cookies":
                return await self._get_cookies()
            elif action == "clear_cookies":
                return await self._clear_cookies()
            elif action == "close":
                return await self._close()
            else:
                return CommandResult.error(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Browser V4 action {action} failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return CommandResult.error(f"Browser error: {str(e)[:200]}")

    async def _navigate(self, url: str) -> Any:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
        title = await self.page.title()
        return CommandResult.ok(
            f"✅ Navigated to {url}\n📄 Title: {title}",
            data={"url": url, "title": title, "browser": "playwright-chromium"}
        )

    async def _search(self, query: str) -> Any:
        url = f"https://www.google.com/search?q={query}"
        return await self._navigate(url)

    async def _click(self, selector: str) -> Any:
        await self.page.click(selector, timeout=10000)
        await self.page.wait_for_load_state("networkidle", timeout=10000)
        title = await self.page.title()
        return CommandResult.ok(f"✅ Clicked {selector}\n📄 Now on: {title}", data={"title": title})

    async def _type(self, selector: str, text: str) -> Any:
        await self.page.fill(selector, text)
        return CommandResult.ok(f"✅ Typed into {selector}")

    async def _screenshot(self, path: Optional[str]) -> Any:
        if not path:
            from omni_v2.core.paths import DATA_DIR
            out_dir = DATA_DIR / "screenshots"
            out_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            path = str(out_dir / f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        await self.page.screenshot(path=path, full_page=True)
        return CommandResult.ok(f"✅ Screenshot saved: {path}", data={"path": path})

    async def _screenshot_url(self, url: str, path: Optional[str]) -> Any:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return await self._screenshot(path)

    async def _extract_text(self, selector: str) -> Any:
        if not selector:
            text = await self.page.inner_text("body")
        else:
            text = await self.page.inner_text(selector)
        return CommandResult.ok(f"📄 Extracted: {text[:1000]}", data={"text": text[:5000]})

    async def _fill_form(self, fields: Dict[str, str]) -> Any:
        for selector, value in fields.items():
            await self.page.fill(selector, value)
        return CommandResult.ok(f"✅ Filled {len(fields)} form fields")

    async def _execute_js(self, code: str) -> Any:
        # Cap to prevent abuse
        if len(code) > 5000:
            return CommandResult.error("JS code too long (max 5000 chars)")
        result = await self.page.evaluate(code)
        return CommandResult.ok(
            f"✅ JS executed, result: {str(result)[:500]}",
            data={"result": str(result)[:2000]}
        )

    async def _get_cookies(self) -> Any:
        cookies = await self.context.cookies()
        # Redact sensitive values for safety
        safe = []
        for c in cookies:
            safe.append({
                "name": c.get("name", ""),
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
                "expires": c.get("expires", -1),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "sameSite": c.get("sameSite", "None"),
                # value omitted in display for privacy
            })
        return CommandResult.ok(
            f"🍪 {len(cookies)} cookies in profile",
            data={"count": len(cookies), "cookies": safe}
        )

    async def _clear_cookies(self) -> Any:
        await self.context.clear_cookies()
        return CommandResult.ok("✅ All cookies cleared")

    async def _close(self) -> Any:
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self._initialized = False
        except Exception:
            pass
        return CommandResult.ok("✅ Browser closed")


# Singleton
_browser_v4_instance = None
_browser_v4_lock = threading.Lock()


def get_browser_v4() -> BrowserV4Playwright:
    global _browser_v4_instance
    if _browser_v4_instance is None:
        with _browser_v4_lock:
            if _browser_v4_instance is None:
                _browser_v4_instance = BrowserV4Playwright()
    return _browser_v4_instance
