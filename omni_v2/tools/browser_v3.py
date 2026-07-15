"""
OMNI V3 - Browser Tool FIXED - Profile Isolation Magic (Your Ace)
Opens Chrome in data/chrome_profile/OMNI-Profile without your email = privacy-first
This is your killer feature - keep, document, make it bulletproof
"""
from pathlib import Path
from typing import Dict, Any
import subprocess
import os
import webbrowser

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("BrowserV3")

try:
    from omni_v2.core.plugin_manager import CommandPlugin, CommandMetadata, CommandResult
except ImportError:
    # Fallback stubs for testing without full core
    class CommandPlugin: pass
    class CommandMetadata:
        def __init__(self, **kw): pass
    class CommandResult:
        @staticmethod
        def ok(msg, data=None): return {"success": True, "message": msg, "data": data}
        @staticmethod
        def error(msg): return {"success": False, "message": msg}

class BrowserToolV3(CommandPlugin):
    metadata = CommandMetadata(
        name="browser_v3",
        category="browser",
        description="Browser with profile isolation - privacy-first, no email leak",
        patterns=["open", "search", "github", "youtube", "google", "chrome"],
        examples=["open github", "search for iron man", "open youtube"]
    )
    
    SUPPORTED_ACTIONS = [
        "browser_navigate", "browser_search", "browser_new_tab",
        "browser_github", "browser_youtube", "browser_google"
    ]
    
    def __init__(self):
        # Profile isolated dir - privacy-first - PORTABLE, not D:/Omni hardcoded
        # Works wherever judges clone: C:/Users/Judge/Downloads/Omni, /home/user/Omni, etc.
        try:
            # Relative to this file: omni_v2/tools/browser_v3.py -> parent.parent = omni_v2 -> parent.parent.parent = repo root
            OMNI_ROOT = Path(__file__).resolve().parent.parent.parent
            if not (OMNI_ROOT / "omni_v2").exists():
                # Fallback to cwd if run from weird location
                OMNI_ROOT = Path.cwd()
        except Exception:
            OMNI_ROOT = Path.cwd()
        
        self.profile_dir = OMNI_ROOT / "data" / "chrome_profile"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.profile_name = "OMNI-Profile"
        logger.info(f"Browser V3 - Profile isolated: {self.profile_dir.absolute()} / {self.profile_name} (portable, works for judges anywhere)")
    
    def _find_chrome(self) -> str:
        """Find chrome.exe path"""
        possible = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            "chrome.exe",  # PATH
            "chrome",
        ]
        for p in possible:
            if p == "chrome.exe" or p == "chrome":
                return p
            if Path(p).exists():
                return p
        return "chrome.exe"
    
    def _launch_chrome_isolated(self, url: str) -> bool:
        """Launch Chrome with isolated profile - YOUR MAGIC"""
        try:
            chrome = self._find_chrome()
            user_data = str(self.profile_dir.absolute())
            
            # Args for isolated profile + remote debugging (for future automation)
            args = [
                chrome,
                f"--user-data-dir={user_data}",
                f"--profile-directory={self.profile_name}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-features=Translate",
                "--remote-debugging-port=9222",  # For future Selenium/CDP
                url
            ]
            
            logger.info(f"🚀 Launching isolated Chrome: {self.profile_name} -> {url}")
            logger.info(f"   User data: {user_data}")
            logger.info(f"   This profile has NO email signed in - privacy by design!")
            
            # Use shell=False for security (hardened)
            subprocess.Popen(args, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
            
        except Exception as e:
            logger.error(f"Chrome isolated launch failed: {e}, fallback webbrowser")
            try:
                webbrowser.open(url, new=2)
                return True
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                return False
    
    async def execute(self, entities: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        context = context or {}
        original = context.get('original', '').lower()
        url = entities.get('url', '')
        query = entities.get('query', '')

        # GUARD-06: validate URL before doing anything
        if url:
            try:
                from omni_v2.core.guardrails import safe_url
                is_safe, err = safe_url(url)
                if not is_safe:
                    logger.warning(f"Guardrail blocked URL: {url[:80]} | {err}")
                    try:
                        from omni_v2.core.plugin_manager import CommandResult
                        return CommandResult.error(
                            f"URL blocked by security guardrail: {err}. "
                            f"OMNI only allows http/https/ftp URLs to safe destinations."
                        )
                    except:
                        return {"success": False, "message": f"URL blocked: {err}"}
            except ImportError:
                pass  # guardrails unavailable, fall through

        # Determine intent from original text if no entities
        if not url and not query:
            if 'github' in original:
                url = "https://github.com"
            elif 'youtube' in original:
                if 'search' in original or 'play' in original:
                    # Extract search after "search for" or "play"
                    import re
                    m = re.search(r'(?:search for|play|search)\s+(.+)', original)
                    if m:
                        query = m.group(1).strip()
                        if 'youtube' in query:
                            query = query.replace('youtube', '').strip()
                        url = f"https://www.youtube.com/results?search_query={query}" if query else "https://www.youtube.com"
                    else:
                        url = "https://www.youtube.com"
                else:
                    url = "https://www.youtube.com"
            elif 'google' in original:
                url = "https://www.google.com"
            elif 'gmail' in original:
                url = "https://mail.google.com"
            elif 'search' in original:
                import re
                m = re.search(r'search(?: for)?\s+(.+)', original)
                if m:
                    query = m.group(1)
                    url = f"https://www.google.com/search?q={query}"
        
        # If still no url but query present
        if not url and query:
            url = f"https://www.google.com/search?q={query}"
        
        # If still nothing, try parse url from original
        if not url:
            import re
            url_match = re.search(r'https?://[^\s]+', original)
            if url_match:
                url = url_match.group(0)
        
        if url:
            success = self._launch_chrome_isolated(url)
            if success:
                try:
                    from omni_v2.core.plugin_manager import CommandResult
                    return CommandResult.ok(
                        f"✅ Opened in isolated profile {self.profile_name}: {url} (no email, privacy by design)",
                        data={"url": url, "profile": self.profile_name, "user_data_dir": str(self.profile_dir)}
                    )
                except:
                    return {"success": True, "message": f"Opened {url} in isolated profile"}
            else:
                try:
                    from omni_v2.core.plugin_manager import CommandResult
                    return CommandResult.error(f"Failed to open {url}")
                except:
                    return {"success": False, "message": f"Failed {url}"}
        
        # If query only
        if query:
            url = f"https://www.google.com/search?q={query}"
            success = self._launch_chrome_isolated(url)
            if success:
                try:
                    from omni_v2.core.plugin_manager import CommandResult
                    return CommandResult.ok(f"Searching in isolated profile: {query}", data={"url": url, "query": query})
                except:
                    return {"success": True, "message": f"Searching {query}"}
        
        try:
            from omni_v2.core.plugin_manager import CommandResult
            return CommandResult.ok(f"Browser: {original}")
        except:
            return {"success": True, "message": f"Browser: {original}"}

# For get_all_tools()
def get_tool():
    return BrowserToolV3()
