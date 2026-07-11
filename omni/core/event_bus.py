"""Event Bus - Centralized Event Communication (Winning Robust Edition)"""
import asyncio
import threading
from typing import Callable, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from loguru import logger
from datetime import datetime

class EventType(Enum):
    PTT_PRESSED = auto()
    PTT_RELEASED = auto()
    TRANSCRIPTION_COMPLETE = auto()
    COMMAND_EXECUTING = auto()
    COMMAND_COMPLETE = auto()
    COMMAND_FAILED = auto()
    TTS_START = auto()
    TTS_END = auto()
    STATUS_UPDATE = auto()
    ERROR = auto()

@dataclass
class Event:
    type: EventType
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"

class EventBus:
    """Central event bus - singleton with thread-safe emission and async/sync handling"""
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
        self._running = False
        self._initialized = True
        logger.info("EventBus initialized (thread-safe)")
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            # Prevent duplicate subscriptions
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)
                logger.debug(f"Subscribed {callback.__name__ if hasattr(callback, '__name__') else str(callback)} to {event_type}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        with self._lock:
            if event_type in self._listeners and callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)
    
    def emit(self, event_type: EventType, data: Any = None, source: str = "system") -> None:
        event = Event(type=event_type, data=data, source=source)
        listeners = []
        with self._lock:
            listeners = list(self._listeners.get(event_type, []))
        
        if not listeners:
            logger.debug(f"Event {event_type} emitted with no listeners (data={str(data)[:100]})")
            return
            
        for callback in listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Try to schedule async callback
                    try:
                        loop = asyncio.get_running_loop()
                        if loop.is_running():
                            loop.create_task(callback(event))
                        else:
                            # No running loop, run in new thread pool via asyncio.run is not ideal
                            # Fallback: try to run sync
                            asyncio.run_coroutine_threadsafe(callback(event), loop)
                    except RuntimeError:
                        # No loop - try to get event loop or run directly in thread
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.run_coroutine_threadsafe(callback(event), loop)
                            else:
                                # Run synchronously in this thread using asyncio.run
                                # But avoid nested loop issues - just log and try sync wrapper
                                logger.debug(f"Async callback {callback} without running loop - attempting run")
                                # Start new loop in daemon thread
                                def run_async():
                                    try:
                                        asyncio.run(callback(event))
                                    except Exception as e:
                                        logger.error(f"Async event handler error (threaded): {e}")
                                threading.Thread(target=run_async, daemon=True).start()
                        except Exception as e:
                            logger.error(f"Failed to emit async event {event_type}: {e}")
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")

    def clear(self):
        """Clear all listeners (useful for tests)"""
        with self._lock:
            self._listeners.clear()
