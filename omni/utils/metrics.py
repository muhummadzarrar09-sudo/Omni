"""OMNI Metrics - Performance tracking"""
import time
from collections import defaultdict
import threading

class MetricsCollector:
    """Collects and tracks OMNI performance metrics."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._timers = {}
        self._counters = defaultdict(int)
        self._lock = threading.Lock()
        self._initialized = True
    
    def start_timer(self, name: str) -> None:
        self._timers[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        if name in self._timers:
            duration = time.time() - self._timers[name]
            del self._timers[name]
            return duration
        return 0.0
    
    def increment(self, name: str, count: int = 1) -> None:
        with self._lock:
            self._counters[name] += count
    
    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)
    
    def summary(self) -> dict:
        return {"counters": dict(self._counters), "active_timers": len(self._timers)}
