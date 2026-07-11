"""Event Bus V2 - Thread-safe, async/sync, never crashes"""
import asyncio
import threading
from typing import Callable, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("EventBusV2")

class EventType(Enum):
    PTT_PRESSED = auto()
    PTT_RELEASED = auto()
    WAKEWORD_DETECTED = auto()
    TRANSCRIPTION_COMPLETE = auto()
    COMMAND_EXECUTING = auto()
    COMMAND_COMPLETE = auto()
    COMMAND_FAILED = auto()
    TTS_START = auto()
    TTS_END = auto()
    STATUS_UPDATE = auto()
    ERROR = auto()
    CHAIN_START = auto()
    CHAIN_STEP = auto()
    CHAIN_COMPLETE = auto()

@dataclass
class Event:
    type: EventType
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"

class EventBus:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._listeners: Dict[EventType, List[Callable]] = {}
        self._initialized = True
        logger.info("EventBus V2 initialized (thread-safe, chain-aware)")

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)

    def emit(self, event_type: EventType, data: Any = None, source: str = "system") -> None:
        event = Event(type=event_type, data=data, source=source)
        listeners = []
        with self._lock:
            listeners = list(self._listeners.get(event_type, []))
        
        for callback in listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    try:
                        loop = asyncio.get_running_loop()
                        if loop.is_running():
                            loop.create_task(callback(event))
                        else:
                            import threading
                            def run_async():
                                try:
                                    asyncio.run(callback(event))
                                except Exception as e:
                                    logger.error(f"Async handler error: {e}")
                            threading.Thread(target=run_async, daemon=True).start()
                    except RuntimeError:
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.run_coroutine_threadsafe(callback(event), loop)
                            else:
                                def run_async():
                                    try:
                                        asyncio.run(callback(event))
                                    except Exception as e:
                                        logger.error(f"Async handler threaded error: {e}")
                                threading.Thread(target=run_async, daemon=True).start()
                        except Exception as e:
                            logger.error(f"Emit async error: {e}")
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event handler error {event_type}: {e}")
