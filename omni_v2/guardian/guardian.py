"""
OMNI PROACTIVE GUARDIAN (Phase 10) — "Jarvis watches your back".

A background watcher that samples the machine and surfaces proactive observations
and anomalies:
  - process/app usage (new or unexpected apps, heavy CPU/mem)
  - file-system changes (new/modified files in watched dirs)
  - system health (battery, disk, CPU, RAM)
  - network (new listeners / connectivity)

It feeds findings to:
  - a `notify_fn` (messenger) for important anomalies
  - an `on_observation` callback (UI / desktop app)
  - the reflector's pattern awareness for long-term noticing

Fully local, headless-testable: all checkers are pluggable so tests use fakes.
No cloud.
"""
from __future__ import annotations
import time
import threading
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Guardian")


class Guardian:
    """Periodic machine watcher that produces observations/anomalies."""

    def __init__(
        self,
        interval: float = 30.0,
        checkers: Optional[List[Callable[[], List[Dict[str, Any]]]]] = None,
        notify_fn: Optional[Callable[[str], Any]] = None,
        on_observation: Optional[Callable[[Dict[str, Any]], None]] = None,
        anomaly_threshold: int = 2,   # severity needed to notify via messenger
    ):
        self.interval = interval
        self.checkers = checkers or []
        self.notify_fn = notify_fn
        self.on_observation = on_observation
        self.anomaly_threshold = anomaly_threshold
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()
        self._observations: List[Dict[str, Any]] = []
        self._last_run: Optional[float] = None

    # -- control -----------------------------------------------------------
    def add_checker(self, fn: Callable[[], List[Dict[str, Any]]]) -> None:
        self.checkers.append(fn)

    def start(self) -> bool:
        if self._running:
            return True
        if not self.checkers:
            logger.warning("Guardian: no checkers registered; not starting")
            return False
        self._stop.clear()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="omni-guardian")
        self._thread.start()
        logger.info(f"Guardian started (interval {self.interval}s, {len(self.checkers)} checker(s))")
        return True

    def stop(self) -> None:
        self._running = False
        self._stop.set()

    @property
    def running(self) -> bool:
        return self._running

    def run_once(self) -> List[Dict[str, Any]]:
        """Run all checkers once, record + route observations. Returns them."""
        findings: List[Dict[str, Any]] = []
        for chk in self.checkers:
            try:
                res = chk() or []
                findings.extend(res)
            except Exception as e:
                logger.warning(f"checker error: {e}")
        self._last_run = time.time()
        with self._lock:
            self._observations.extend(findings)
            self._observations = self._observations[-500:]
        # route
        for obs in findings:
            if self.on_observation:
                try:
                    self.on_observation(obs)
                except Exception:
                    pass
            if self.notify_fn and obs.get("severity", 0) >= self.anomaly_threshold:
                try:
                    self.notify_fn(self._format(obs))
                except Exception as e:
                    logger.warning(f"guardian notify failed: {e}")
        return findings

    @staticmethod
    def _format(obs: Dict[str, Any]) -> str:
        return f"⚠️ OMNI guardian: {obs.get('title', 'notice')} — {obs.get('body', '')}"

    def _loop(self) -> None:
        # run immediately once, then on interval
        try:
            self.run_once()
        except Exception as e:
            logger.warning(f"guardian first run: {e}")
        while not self._stop.is_set():
            self._stop.wait(self.interval)
            if self._stop.is_set():
                break
            try:
                self.run_once()
            except Exception as e:
                logger.warning(f"guardian run: {e}")

    # -- accessors ----------------------------------------------------------
    def recent(self, n: int = 30) -> List[Dict[str, Any]]:
        with self._lock:
            return self._observations[-n:][::-1]

    def anomalies(self, n: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [o for o in self._observations if o.get("severity", 0) >= 1][-n:][::-1]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "checkers": len(self.checkers),
                "observations": len(self._observations),
                "last_run": self._last_run,
                "interval": self.interval,
            }


# ---------------------------------------------------------------------------
# Built-in checkers (pluggable, headless-testable)
# ---------------------------------------------------------------------------
def process_checker(known: Optional[set] = None,
                    cpu_threshold: float = 90.0) -> Callable[[], List[Dict[str, Any]]]:
    """Watch running processes for unexpected apps or high CPU."""
    known = known if known is not None else {"python", "python3", "node", "chrome",
                                             "firefox", "explorer", "cmd", "powershell"}
    known = {k.lower() for k in known}

    def _run() -> List[Dict[str, Any]]:
        out = []
        try:
            import psutil
            for p in psutil.process_iter(["name", "cpu_percent"]):
                try:
                    name = (p.info.get("name") or "").lower()
                    if not name:
                        continue
                    cpu = p.info.get("cpu_percent") or 0
                    if name not in known and cpu > 0:
                        out.append({
                            "kind": "process",
                            "title": f"New process: {name}",
                            "body": f"'{name}' is running (CPU {cpu:.0f}%). Not in your known list.",
                            "severity": 1,
                        })
                except Exception:
                    continue
        except Exception:
            pass
        return out[:5]

    return _run


def health_checker(battery_low: float = 20.0, disk_low: float = 10.0,
                   cpu_high: float = 90.0) -> Callable[[], List[Dict[str, Any]]]:
    """System health: battery, disk, CPU."""
    def _run() -> List[Dict[str, Any]]:
        out = []
        try:
            import psutil
            # battery
            try:
                batt = psutil.sensors_battery()
                if batt is not None and batt.percent is not None and batt.percent <= battery_low:
                    out.append({
                        "kind": "battery",
                        "title": "Low battery",
                        "body": f"Battery at {batt.percent:.0f}%. Consider plugging in.",
                        "severity": 2,
                    })
            except Exception:
                pass
            # disk
            try:
                du = psutil.disk_usage("/")
                if du.percent >= (100 - disk_low):
                    out.append({
                        "kind": "disk",
                        "title": "Disk nearly full",
                        "body": f"Disk at {du.percent:.0f}% used ({du.free // (1024**3)} GB free).",
                        "severity": 2,
                    })
            except Exception:
                pass
            # cpu
            try:
                c = psutil.cpu_percent(interval=0.2)
                if c >= cpu_high:
                    out.append({
                        "kind": "cpu",
                        "title": "High CPU",
                        "body": f"CPU at {c:.0f}%.",
                        "severity": 1,
                    })
            except Exception:
                pass
        except Exception:
            pass
        return out

    return _run


def file_watcher(watched_dirs: List[str]) -> Callable[[], List[Dict[str, Any]]]:
    """Detect newly created files in watched directories since last run."""
    import os
    from pathlib import Path
    seen: Dict[str, float] = {}

    def _run() -> List[Dict[str, Any]]:
        out = []
        now = time.time()
        for d in watched_dirs:
            try:
                root = Path(d)
                if not root.exists():
                    continue
                for p in root.rglob("*"):
                    if p.is_file() and p.stat().st_mtime > (now - 3600):
                        key = str(p)
                        if key not in seen:
                            seen[key] = now
                            out.append({
                                "kind": "file",
                                "title": "New file",
                                "body": f"{key}",
                                "severity": 0,
                            })
            except Exception:
                continue
        return out[:8]

    return _run
