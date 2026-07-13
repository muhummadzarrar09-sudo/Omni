"""PTT Manager V2 - Fixed - Actually Works"""
import time
import threading
import platform

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("PTTV2")

try:
    from omni_v2.core.event_bus import EventBus, EventType
except ImportError:
    EventBus = None
    EventType = None

class PTTManager:
    VK_MAP = {
        "v": 0x56,
        "b": 0x42,
        "left_ctrl": 0xA3,
        "right_ctrl": 0xA3,
        "space": 0x20,
        "caps_lock": 0x14,
        "capslock": 0x14,
    }
    KEYBOARD_MAP = {
        "v": "v",
        "b": "b",
        "space": "space",
        "left_ctrl": "ctrl",
        "right_ctrl": "ctrl",
        "caps_lock": "caps lock",
        "capslock": "caps lock",
    }

    def __init__(self, key: str = "v", event_bus=None):
        self.key_name = (key or "v").lower()
        self.vk_code = self.VK_MAP.get(self.key_name, 0x56)
        self.keyboard_key = self.KEYBOARD_MAP.get(self.key_name, "v")
        self.event_bus = event_bus
        self.is_pressed = False
        self.press_time = None
        self._running = False
        self._monitor_thread = None
        self._is_toggle_on = False
        self._key_is_pressed = False
        self._use_keyboard_lib = False
        self._platform = platform.system().lower()
        logger.info(f"PTTManager V2 - Key: {self.key_name} - Press V LOUD and CLOSE")

    def start(self):
        if self._running:
            return
        self._running = True
        if self._platform == "windows":
            try:
                import ctypes
                ctypes.windll.user32.GetAsyncKeyState
                self._use_keyboard_lib = False
            except Exception:
                self._use_keyboard_lib = True
        else:
            self._use_keyboard_lib = True

        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="PTT-V2")
        self._monitor_thread.start()
        logger.info(f"PTT V2 monitoring started - Press {self.key_name.upper()} to speak LOUD and CLOSE (2 inches)")

    def stop(self):
        self._running = False
        if self._monitor_thread:
            try:
                self._monitor_thread.join(timeout=2)
            except Exception:
                pass

    def _monitor_loop(self):
        if self._use_keyboard_lib:
            self._monitor_loop_keyboard()
        else:
            self._monitor_loop_win32()

    def _monitor_loop_win32(self):
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
                            if self.event_bus and EventType:
                                try:
                                    self.event_bus.emit(EventType.PTT_RELEASED, {"duration": duration}, "PTTManager")
                                except Exception:
                                    pass
                            logger.info("PTT OFF - Stop recording and transcribe")
                        else:
                            self._is_toggle_on = True
                            self.is_pressed = True
                            self.press_time = time.time()
                            if self.event_bus and EventType:
                                try:
                                    self.event_bus.emit(EventType.PTT_PRESSED, source="PTTManager")
                                except Exception:
                                    pass
                            logger.info("PTT ON - Start recording, SPEAK LOUD and CLOSE!")
                    elif not key_down:
                        self._key_is_pressed = False
                except Exception:
                    pass
                time.sleep(0.02)
        except Exception as e:
            logger.error(f"PTT win32 error: {e}, fallback to keyboard")
            self._use_keyboard_lib = True
            self._monitor_loop_keyboard()

    def _monitor_loop_keyboard(self):
        try:
            import keyboard
            last_trigger = 0.0
            debounce = 0.4
            def on_key_event(event):
                nonlocal last_trigger
                now = time.time()
                if now - last_trigger < debounce:
                    return
                if event.event_type != 'down':
                    return
                last_trigger = now
                if self._is_toggle_on:
                    self._is_toggle_on = False
                    self.is_pressed = False
                    duration = now - (self.press_time or now)
                    if self.event_bus and EventType:
                        try:
                            self.event_bus.emit(EventType.PTT_RELEASED, {"duration": duration}, "PTTManager")
                        except Exception:
                            pass
                    logger.info("PTT OFF (keyboard)")
                else:
                    self._is_toggle_on = True
                    self.is_pressed = True
                    self.press_time = now
                    if self.event_bus and EventType:
                        try:
                            self.event_bus.emit(EventType.PTT_PRESSED, source="PTTManager")
                        except Exception:
                            pass
                    logger.info("PTT ON (keyboard) - Speak LOUD!")
            try:
                keyboard.on_press_key(self.keyboard_key, on_key_event, suppress=False)
            except Exception:
                keyboard.on_press(on_key_event)
            while self._running:
                time.sleep(0.1)
        except ImportError:
            logger.error("keyboard lib not installed - pip install keyboard")
            while self._running:
                time.sleep(1)
        except Exception as e:
            logger.error(f"PTT keyboard error: {e}")
            while self._running:
                time.sleep(0.5)
