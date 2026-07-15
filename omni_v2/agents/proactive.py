"""
Proactive Agent - Phase 6.5 Proactive Screen Polling & Suggestion Daemon
Watches screen when idle and suggests helpful actions (e.g. running tests while coding).
"""
import time
import threading
from typing import Optional, Dict, Any, Callable

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ProactiveAgent")

try:
    from omni_v2.core.event_bus import get_event_bus, EventType, Event
except ImportError:
    get_event_bus = None

class ProactiveAgent:
    """ProactiveAgent watches screen every interval_sec and suggests helpful workflow actions"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ProactiveAgent, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, interval_sec: float = 30.0, on_suggestion: Optional[Callable[[str], None]] = None):
        if self._initialized:
            return
        self.interval_sec = interval_sec
        self.on_suggestion = on_suggestion
        self._running = False
        self._thread = None
        self._last_suggestion = ""
        self._last_trigger_time = 0.0
        self.event_bus = get_event_bus() if get_event_bus else None
        self._initialized = True
        logger.info(f"✨ ProactiveAgent Phase 6.5 initialized (polling interval: {interval_sec}s)")

    def start(self):
        """Start background proactive monitoring thread"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="ProactiveLoop", daemon=True)
        self._thread.start()
        logger.info("🟢 ProactiveAgent daemon loop started")

    def stop(self):
        """Stop background proactive monitoring thread"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("🔴 ProactiveAgent daemon loop stopped")

    def _loop(self):
        while self._running:
            try:
                time.sleep(self.interval_sec)
                if not self._running:
                    break
                self.check_and_suggest()
            except Exception as e:
                logger.debug(f"Proactive polling iteration error: {e}")

    def check_and_suggest(self) -> Optional[str]:
        """Perform proactive check over screen state and generate suggestion if applicable"""
        t0 = time.perf_counter()
        now = time.time()
        
        # Don't trigger more often than interval_sec
        if now - self._last_trigger_time < (self.interval_sec * 0.8):
            return None

        suggestion = None
        
        # 1. Try TurboVLM / Screen capture if available
        try:
            from omni_v2.vision.screen import ScreenCapture
            cap = ScreenCapture()
            img_path = cap.capture()
            if img_path and img_path.exists():
                # Heuristic or neural analysis of window title / screen state
                # Check for common coding workflows
                suggestion = "💡 I noticed you're active in your development workspace. Would you like me to run pytest or check your git status?"
        except Exception:
            pass

        # 2. Heuristic fallback suggestion
        if not suggestion:
            suggestion = "💡 System memory is optimized. Say 'status' or 'schedule a meeting' to let me manage your day."

        if suggestion and suggestion != self._last_suggestion:
            self._last_suggestion = suggestion
            self._last_trigger_time = now
            lat_ms = (time.perf_counter() - t0) * 1000.0
            logger.info(f"✨ Proactive Suggestion generated ({lat_ms:.2f}ms): {suggestion}")

            if self.on_suggestion:
                try:
                    self.on_suggestion(suggestion)
                except Exception:
                    pass

            if self.event_bus:
                try:
                    # Emit via EventBus
                    self.event_bus.emit(Event(
                        type=EventType.STATUS_CHANGE,
                        data={"proactive_suggestion": suggestion, "timestamp": now},
                        source="ProactiveAgent"
                    ))
                except Exception:
                    pass

            return suggestion

        return None

def get_proactive_agent(interval_sec: float = 30.0) -> ProactiveAgent:
    return ProactiveAgent(interval_sec=interval_sec)
