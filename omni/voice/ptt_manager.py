"""PTT Manager - Push-to-Talk with global hotkey detection"""
import time
import threading
from loguru import logger
from omni.core.event_bus import EventBus, EventType

class PTTManager:
    """Manages Push-to-Talk functionality via global hotkey."""
    
    VK_MAP = {
        "caps_lock": 0x14,
        "left_ctrl": 0x11,
        "right_ctrl": 0xA3,
        "space": 0x32,
    }
    
    def __init__(self, key: str = "caps_lock", event_bus: EventBus = None):
        self.key_name = key.lower()
        self.vk_code = self.VK_MAP.get(self.key_name, 0x14)
        self.event_bus = event_bus or EventBus()
        self.is_pressed = False
        self.press_time = None
        self._running = False
        self._monitor_thread = None
        self._is_ptt_processing = False  # Guard: prevent double-trigger while releasing
        logger.info(f"PTTManager initialized with key: {self.key_name}")
    
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="PTT-Monitor")
        self._monitor_thread.start()
        logger.info("PTT monitoring started")
    
    def stop(self) -> None:
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
    
    def _monitor_loop(self) -> None:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            last_state = False
            while self._running:
                try:
                    current_state = user32.GetAsyncKeyState(self.vk_code) < 0
                    if current_state and not last_state:
                        self.is_pressed = True
                        self.press_time = time.time()
                        self.event_bus.emit(EventType.PTT_PRESSED, source="PTTManager")
                    elif not current_state and last_state:
                        self.is_pressed = False
                        duration = time.time() - self.press_time if self.press_time else 0
                        self.event_bus.emit(EventType.PTT_RELEASED, {"duration": duration}, "PTTManager")
                    last_state = current_state
                except: pass
                time.sleep(0.02)
        except Exception as e:
            logger.error(f"PTT monitor error: {e}")
