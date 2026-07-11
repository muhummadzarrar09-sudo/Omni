"""PTT Manager - Push-to-Talk with global hotkey detection (Winning Cross-Platform Edition)"""
import time
import threading
import platform
from loguru import logger
from omni.core.event_bus import EventBus, EventType

class PTTManager:
    """Manages Push-to-Talk functionality via global hotkey with Windows + cross-platform fallback."""
    
    VK_MAP = {
        "v": 0x56,
        "b": 0x42,
        "left_ctrl": 0xA3,  # LCTRL on many systems is 0xA2 but we map broadly
        "right_ctrl": 0xA3,
        "left_ctrl_alias": 0x11,
        "space": 0x20,
        "caps_lock": 0x14,
        "capslock": 0x14,
    }

    # keyboard lib names mapping
    KEYBOARD_MAP = {
        "v": "v",
        "b": "b",
        "space": "space",
        "left_ctrl": "ctrl",
        "right_ctrl": "ctrl",
        "caps_lock": "caps lock",
        "capslock": "caps lock",
    }

    def __init__(self, key: str = "v", event_bus: EventBus = None):
        self.key_name = (key or "v").lower()
        self.vk_code = self.VK_MAP.get(self.key_name, 0x56)
        self.keyboard_key = self.KEYBOARD_MAP.get(self.key_name, "v")
        self.event_bus = event_bus or EventBus()
        self.is_pressed = False
        self.press_time = None
        self._running = False
        self._monitor_thread = None
        self._is_ptt_processing = False
        self._is_toggle_on = False
        self._key_is_pressed = False
        self._use_keyboard_lib = False
        self._platform = platform.system().lower()
        logger.info(f"PTTManager initialized with key: {self.key_name} (vk={hex(self.vk_code)} keyboard='{self.keyboard_key}' platform={self._platform})")
    
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        # Decide backend
        if self._platform == "windows":
            try:
                import ctypes
                # Test if windll available
                ctypes.windll.user32.GetAsyncKeyState
                self._use_keyboard_lib = False
                logger.info("PTT backend: Windows GetAsyncKeyState (optimal)")
            except Exception as e:
                logger.warning(f"Windows API not available ({e}), trying keyboard lib fallback")
                self._use_keyboard_lib = True
        else:
            self._use_keyboard_lib = True
            logger.info("PTT backend: keyboard lib (cross-platform)")

        if self._use_keyboard_lib:
            # Try to init keyboard lib
            try:
                import keyboard
                # Test import ok
                logger.info(f"keyboard lib available, listening for '{self.keyboard_key}'")
            except ImportError:
                logger.error("keyboard library not installed - PTT may not work. pip install keyboard")
                logger.error("For Linux, you may need sudo or input group permission")
                # We'll still try windows fallback if somehow

        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="PTT-Monitor")
        self._monitor_thread.start()
        logger.info(f"PTT monitoring started (backend={'keyboard' if self._use_keyboard_lib else 'win32'})")
    
    def stop(self) -> None:
        self._running = False
        if self._monitor_thread:
            try:
                self._monitor_thread.join(timeout=2)
            except Exception:
                pass
        if self._use_keyboard_lib:
            try:
                import keyboard
                keyboard.unhook_all()
            except Exception:
                pass
    
    def _monitor_loop(self) -> None:
        if self._use_keyboard_lib:
            self._monitor_loop_keyboard()
        else:
            self._monitor_loop_win32()

    def _monitor_loop_win32(self) -> None:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            while self._running:
                try:
                    key_down = user32.GetAsyncKeyState(self.vk_code) & 0x8000 != 0

                    if key_down and not self._key_is_pressed:
                        self._key_is_pressed = True
                        if self._is_toggle_on:
                            self._is_toggle_on = False
                            self.is_pressed = False
                            duration = time.time() - self.press_time if self.press_time else 0
                            try:
                                self.event_bus.emit(EventType.PTT_RELEASED, {"duration": duration}, "PTTManager")
                            except Exception as e:
                                logger.debug(f"Emit PTT_RELEASED failed: {e}")
                            logger.info("PTT toggle: OFF (released)")
                        else:
                            self._is_toggle_on = True
                            self.is_pressed = True
                            self.press_time = time.time()
                            try:
                                self.event_bus.emit(EventType.PTT_PRESSED, source="PTTManager")
                            except Exception as e:
                                logger.debug(f"Emit PTT_PRESSED failed: {e}")
                            logger.info("PTT toggle: ON (pressed)")

                    elif not key_down:
                        self._key_is_pressed = False

                except Exception as loop_e:
                    logger.debug(f"PTT win32 loop inner error: {loop_e}")
                time.sleep(0.02)
        except Exception as e:
            logger.error(f"PTT win32 monitor error (switching to keyboard fallback): {e}")
            self._use_keyboard_lib = True
            self._monitor_loop_keyboard()

    def _monitor_loop_keyboard(self) -> None:
        try:
            import keyboard
            # Use keyboard's on_press to toggle
            last_trigger = 0.0
            debounce = 0.4  # seconds to prevent double trigger

            def on_key_event(event):
                nonlocal last_trigger
                now = time.time()
                if now - last_trigger < debounce:
                    return
                # Only trigger on key down
                if event.event_type != 'down':
                    return
                last_trigger = now
                # Toggle logic
                if self._is_toggle_on:
                    self._is_toggle_on = False
                    self.is_pressed = False
                    duration = now - (self.press_time or now)
                    try:
                        self.event_bus.emit(EventType.PTT_RELEASED, {"duration": duration}, "PTTManager")
                    except Exception:
                        pass
                    logger.info("PTT toggle: OFF (keyboard lib)")
                else:
                    self._is_toggle_on = True
                    self.is_pressed = True
                    self.press_time = now
                    try:
                        self.event_bus.emit(EventType.PTT_PRESSED, source="PTTManager")
                    except Exception:
                        pass
                    logger.info("PTT toggle: ON (keyboard lib)")

            # Hook
            try:
                keyboard.on_press_key(self.keyboard_key, on_key_event, suppress=False)
            except Exception:
                # Fallback generic handler
                keyboard.on_press(on_key_event)

            logger.info(f"Keyboard lib hooked for '{self.keyboard_key}'")

            while self._running:
                time.sleep(0.1)

        except ImportError:
            logger.error("keyboard library not installed - PTT disabled. Install via: pip install keyboard")
            # Keep thread alive but do nothing
            while self._running:
                time.sleep(1)
        except Exception as e:
            logger.error(f"PTT keyboard lib error: {e}")
            # If keyboard lib fails due to permissions on Linux, fallback to polling via input?
            while self._running:
                time.sleep(0.5)
