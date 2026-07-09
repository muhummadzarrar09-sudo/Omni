"""Event Bus - Centralized Event Communication"""
import asyncio
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
    """Central event bus - singleton pattern"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._listeners: Dict[EventType, List[Callable]] = {}
        self._running = False
        self._initialized = True
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def emit(self, event_type: EventType, data: Any = None, source: str = "system") -> None:
        event = Event(type=event_type, data=data, source=source)
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(event))
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
