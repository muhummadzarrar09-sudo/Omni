"""
OMNI V3 - Geofence Engine (Phase 5C)

The brain knows where you are. The phone tells it. The brain acts on it.

This module:
  - Tracks the phone's current location (lat/lon)
  - Maintains a list of named places (Home, Work, Gym, etc) with lat/lon + radius
  - Maintains a list of rules (place + event + command to fire)
  - Fires rules when the user arrives at, departs from, or dwells at a place
  - Logs all location history for "where was I at 2pm Tuesday?" queries
  - Persists everything to JSON (atomic writes)

Privacy:
  - All location data stays on the laptop
  - Phone only pushes when the user taps "send location" OR on geofence events
  - User can disable / clear history anytime
  - No GPS tracking unless user opts in

Geofence math:
  - Uses Haversine for distance (accurate to ~0.5% over short distances)
  - Place radius is in meters (default 100m)
  - Dwell time: how long you've been inside the place
  - Cooldown: don't fire the same rule twice in N seconds (default 30 min)
"""
from __future__ import annotations
import math
import time
import json
import threading
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Geofence")


# Earth radius in meters (mean)
EARTH_RADIUS_M = 6_371_000.0

# Default dwell time to fire "dwell" events (seconds)
DEFAULT_DWELL_SEC = 5 * 60  # 5 minutes

# Default cooldown to prevent rule re-firing
DEFAULT_COOLDOWN_SEC = 30 * 60  # 30 minutes

# Max location history to keep per place
MAX_HISTORY_PER_PLACE = 100

# Max total history entries (oldest get pruned)
MAX_TOTAL_HISTORY = 1000


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance between two (lat, lon) points, in meters.
    Uses the Haversine formula — accurate to ~0.5% for typical use.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def is_inside(lat: float, lon: float, place_lat: float, place_lon: float, radius_m: float) -> bool:
    """True if (lat, lon) is within radius_m of (place_lat, place_lon)."""
    return haversine_m(lat, lon, place_lat, place_lon) <= radius_m


# ---------- Data classes ----------

@dataclass
class Place:
    """A named location with a radius."""
    id: str
    name: str                  # "Home", "Work", "Gym", "Coffee Shop"
    lat: float
    lon: float
    radius_m: float = 100.0    # Default 100m
    icon: str = "📍"           # Emoji icon for UI
    address: str = ""          # Optional human-readable address
    notes: str = ""            # User notes
    created_at: float = field(default_factory=time.time)
    # Stats
    total_arrivals: int = 0
    total_departures: int = 0
    total_dwell_min: float = 0.0
    last_visited: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeofenceRule:
    """A rule: when [event] happens at [place], run [command]."""
    id: str
    place_id: str              # FK to Place.id
    event: str                 # "arrive" | "depart" | "dwell"
    command: str               # Command to run ("play workout playlist")
    label: str = ""            # UI label ("Start workout music")
    cooldown_sec: float = DEFAULT_COOLDOWN_SEC
    dwell_sec: float = DEFAULT_DWELL_SEC  # only for "dwell" event
    enabled: bool = True
    # Trigger history
    last_fired: float = 0.0
    fire_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LocationFix:
    """A single location reading from the phone."""
    lat: float
    lon: float
    accuracy_m: Optional[float] = None  # GPS accuracy
    source: str = "phone"              # "phone" | "manual" | "ip"
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeofenceEvent:
    """A fired rule: when it happened, what place, what command."""
    id: str
    place_id: str
    place_name: str
    event: str                 # "arrive" | "depart" | "dwell"
    command: str
    ts: float = field(default_factory=time.time)
    rule_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------- Engine ----------

class GeofenceEngine:
    """
    Singleton engine. Thread-safe. Persistent.
    Tracks the phone's location, fires rules on place enter/exit/dwell.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir: Optional[Path] = None):
        if self._initialized:
            return
        try:
            from omni_v2.core.paths import DATA_DIR
            base = Path(DATA_DIR) if not isinstance(DATA_DIR, str) else Path(DATA_DIR)
        except Exception:
            base = Path.cwd() / "data"
        self.data_dir = (data_dir or (base / "geofence"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.places_file = self.data_dir / "places.json"
        self.rules_file = self.data_dir / "rules.json"
        self.events_file = self.data_dir / "events.json"
        self.location_file = self.data_dir / "current_location.json"

        self._data_lock = threading.RLock()

        # State
        self.places: Dict[str, Place] = {}
        self.rules: Dict[str, GeofenceRule] = {}
        self.events: List[GeofenceEvent] = []
        self.current_location: Optional[LocationFix] = None
        self.location_history: List[LocationFix] = []

        # Per-place dwell tracking
        self._entered_at: Dict[str, float] = {}    # place_id -> timestamp when entered
        self._was_inside: Dict[str, bool] = {}     # place_id -> currently inside?
        self._dwell_fired: Dict[str, bool] = {}    # place_id -> dwell event fired this stay?

        # Hooks
        self.on_event: Optional[Callable[[GeofenceEvent], None]] = None

        self._load()
        self._initialized = True
        logger.info(f"📍 Geofence engine initialized ({len(self.places)} places, {len(self.rules)} rules)")

    # ===== Persistence =====

    def _load(self):
        with self._data_lock:
            try:
                if self.places_file.exists():
                    raw = json.loads(self.places_file.read_text(encoding="utf-8"))
                    for p in raw:
                        try:
                            place = Place(**p)
                            self.places[place.id] = place
                        except Exception as e:
                            logger.debug(f"Skipping bad place: {e}")
            except Exception as e:
                logger.warning(f"Load places: {e}")
            try:
                if self.rules_file.exists():
                    raw = json.loads(self.rules_file.read_text(encoding="utf-8"))
                    for r in raw:
                        try:
                            rule = GeofenceRule(**r)
                            self.rules[rule.id] = rule
                        except Exception as e:
                            logger.debug(f"Skipping bad rule: {e}")
            except Exception as e:
                logger.warning(f"Load rules: {e}")
            try:
                if self.events_file.exists():
                    raw = json.loads(self.events_file.read_text(encoding="utf-8"))
                    self.events = [GeofenceEvent(**e) for e in raw[-MAX_TOTAL_HISTORY:]]
            except Exception as e:
                logger.warning(f"Load events: {e}")
            try:
                if self.location_file.exists():
                    raw = json.loads(self.location_file.read_text(encoding="utf-8"))
                    self.current_location = LocationFix(**raw)
            except Exception as e:
                logger.debug(f"No current location: {e}")

    def _save_places(self):
        with self._data_lock:
            self._atomic_write(self.places_file, [p.to_dict() for p in self.places.values()])

    def _save_rules(self):
        with self._data_lock:
            self._atomic_write(self.rules_file, [r.to_dict() for r in self.rules.values()])

    def _save_events(self):
        with self._data_lock:
            # Prune oldest
            self.events = self.events[-MAX_TOTAL_HISTORY:]
            self._atomic_write(self.events_file, [e.to_dict() for e in self.events])

    def _save_location(self):
        with self._data_lock:
            if self.current_location:
                self._atomic_write(self.location_file, self.current_location.to_dict())

    def _atomic_write(self, path: Path, data: Any):
        try:
            fd, tmp = tempfile.mkstemp(
                dir=str(self.data_dir),
                prefix=f".{path.stem}_",
                suffix=".json.tmp",
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(tmp, path)
            except Exception:
                try: os.unlink(tmp)
                except Exception: pass
                raise
        except Exception as e:
            logger.error(f"Geofence write failed: {e}")

    # ===== Places =====

    def add_place(self, name: str, lat: float, lon: float, radius_m: float = 100.0,
                  icon: str = "📍", address: str = "", notes: str = "") -> Place:
        """Add a named place. Returns the created Place."""
        if not name or len(name) > 200:
            raise ValueError("place name is required and must be <= 200 characters")
        if not (-90 <= float(lat) <= 90) or not (-180 <= float(lon) <= 180):
            raise ValueError("latitude/longitude out of range")
        if not (0 < float(radius_m) <= 100000):
            raise ValueError("radius must be between 0 and 100000 meters")
        import math
        if not all(math.isfinite(float(v)) for v in (lat, lon, radius_m)):
            raise ValueError("coordinates and radius must be finite")
        import secrets
        pid = f"place_{secrets.token_hex(4)}"
        place = Place(
            id=pid, name=name, lat=lat, lon=lon,
            radius_m=radius_m, icon=icon, address=address, notes=notes,
        )
        with self._data_lock:
            self.places[pid] = place
            self._save_places()
        logger.info(f"📍 Added place: {name} ({lat:.4f}, {lon:.4f}) r={radius_m}m")
        return place

    def update_place(self, place_id: str, **kwargs) -> Optional[Place]:
        """Update a place's fields."""
        with self._data_lock:
            place = self.places.get(place_id)
            if not place:
                return None
            for k, v in kwargs.items():
                if hasattr(place, k) and k not in ("id", "created_at"):
                    setattr(place, k, v)
            self._save_places()
            return place

    def remove_place(self, place_id: str) -> bool:
        """Remove a place and any rules attached to it."""
        with self._data_lock:
            if place_id not in self.places:
                return False
            del self.places[place_id]
            # Cascade: remove rules for this place
            rules_to_remove = [r for r in self.rules.values() if r.place_id == place_id]
            for r in rules_to_remove:
                del self.rules[r.id]
            self._save_places()
            if rules_to_remove:
                self._save_rules()
        return True

    def list_places(self) -> List[Place]:
        with self._data_lock:
            return sorted(self.places.values(), key=lambda p: p.name.lower())

    def get_place(self, place_id: str) -> Optional[Place]:
        return self.places.get(place_id)

    # ===== Rules =====

    def add_rule(self, place_id: str, event: str, command: str,
                 label: str = "", cooldown_sec: float = DEFAULT_COOLDOWN_SEC,
                 dwell_sec: float = DEFAULT_DWELL_SEC) -> Optional[GeofenceRule]:
        """Add a rule. event is 'arrive' | 'depart' | 'dwell'."""
        if not command or len(command) > 2000:
            raise ValueError("rule command is required and must be <= 2000 characters")
        if cooldown_sec < 0 or dwell_sec < 0:
            raise ValueError("cooldown and dwell values cannot be negative")
        if event not in ("arrive", "depart", "dwell"):
            raise ValueError(f"event must be arrive|depart|dwell, got {event!r}")
        if place_id not in self.places:
            return None
        import secrets
        rid = f"rule_{secrets.token_hex(4)}"
        rule = GeofenceRule(
            id=rid, place_id=place_id, event=event, command=command,
            label=label or command, cooldown_sec=cooldown_sec, dwell_sec=dwell_sec,
        )
        with self._data_lock:
            self.rules[rid] = rule
            self._save_rules()
        logger.info(f"📍 Added rule: {event}@{self.places[place_id].name} -> {command}")
        return rule

    def update_rule(self, rule_id: str, **kwargs) -> Optional[GeofenceRule]:
        with self._data_lock:
            rule = self.rules.get(rule_id)
            if not rule:
                return None
            for k, v in kwargs.items():
                if hasattr(rule, k) and k not in ("id", "created_at"):
                    setattr(rule, k, v)
            self._save_rules()
            return rule

    def remove_rule(self, rule_id: str) -> bool:
        with self._data_lock:
            if rule_id not in self.rules:
                return False
            del self.rules[rule_id]
            self._save_rules()
        return True

    def list_rules(self, place_id: Optional[str] = None) -> List[GeofenceRule]:
        with self._data_lock:
            rules = list(self.rules.values())
            if place_id:
                rules = [r for r in rules if r.place_id == place_id]
            return sorted(rules, key=lambda r: r.created_at)

    # ===== Location =====

    def update_location(self, lat: float, lon: float, accuracy_m: Optional[float] = None,
                        source: str = "phone") -> List[GeofenceEvent]:
        """
        Update the current location. Returns any geofence events fired.
        This is the main entry point — call it whenever the phone sends a new fix.
        """
        fix = LocationFix(lat=lat, lon=lon, accuracy_m=accuracy_m, source=source)
        fired: List[GeofenceEvent] = []

        with self._data_lock:
            self.current_location = fix
            self.location_history.append(fix)
            # Prune history
            if len(self.location_history) > MAX_HISTORY_PER_PLACE * 10:
                self.location_history = self.location_history[-MAX_HISTORY_PER_PLACE * 10:]
            self._save_location()

            # Check each place
            for place in self.places.values():
                inside = is_inside(lat, lon, place.lat, place.lon, place.radius_m)
                was_inside = self._was_inside.get(place.id, False)
                self._was_inside[place.id] = inside

                if inside and not was_inside:
                    # ARRIVAL
                    place.total_arrivals += 1
                    place.last_visited = time.time()
                    self._entered_at[place.id] = time.time()
                    self._dwell_fired[place.id] = False
                    self._save_places()
                    fired.extend(self._fire_rules(place, "arrive"))
                elif not inside and was_inside:
                    # DEPARTURE
                    place.total_departures += 1
                    # Track dwell
                    entered = self._entered_at.pop(place.id, None)
                    if entered:
                        dwell_sec = time.time() - entered
                        place.total_dwell_min += dwell_sec / 60.0
                    self._dwell_fired[place.id] = False
                    self._save_places()
                    fired.extend(self._fire_rules(place, "depart"))
                elif inside and was_inside:
                    # Still inside — check dwell
                    entered = self._entered_at.get(place.id)
                    if entered and not self._dwell_fired.get(place.id, False):
                        elapsed = time.time() - entered
                        for rule in self.rules.values():
                            if (rule.place_id == place.id and rule.event == "dwell"
                                    and rule.enabled and elapsed >= rule.dwell_sec):
                                if self._cooldown_ok(rule):
                                    self._dwell_fired[place.id] = True
                                    fired.extend(self._fire_rules(place, "dwell"))
                                    break

        return fired

    def _fire_rules(self, place: Place, event: str) -> List[GeofenceEvent]:
        """Fire all rules for a (place, event). Returns fired events."""
        fired: List[GeofenceEvent] = []
        for rule in self.rules.values():
            if rule.place_id != place.id or rule.event != event or not rule.enabled:
                continue
            if not self._cooldown_ok(rule):
                continue
            import secrets
            ev = GeofenceEvent(
                id=f"evt_{secrets.token_hex(4)}",
                place_id=place.id,
                place_name=place.name,
                event=event,
                command=rule.command,
                rule_id=rule.id,
            )
            rule.last_fired = time.time()
            rule.fire_count += 1
            self.events.append(ev)
            fired.append(ev)
            logger.info(f"📍 FIRE: {event} @ {place.name} -> {rule.command}")
        if fired:
            self._save_events()
            self._save_rules()
            for ev in fired:
                if self.on_event:
                    try: self.on_event(ev)
                    except Exception: pass
        return fired

    def _cooldown_ok(self, rule: GeofenceRule) -> bool:
        return (time.time() - rule.last_fired) >= rule.cooldown_sec

    def get_current_location(self) -> Optional[LocationFix]:
        return self.current_location

    def get_location_history(self, limit: int = 50) -> List[LocationFix]:
        with self._data_lock:
            return list(self.location_history[-limit:])

    def get_current_place(self) -> Optional[Place]:
        """Return the place the user is currently inside, if any."""
        with self._data_lock:
            if not self.current_location:
                return None
            lat = self.current_location.lat
            lon = self.current_location.lon
            best = None
            for place in self.places.values():
                if is_inside(lat, lon, place.lat, place.lon, place.radius_m):
                    if best is None or place.radius_m < best.radius_m:
                        best = place
            return best

    # ===== Events =====

    def get_recent_events(self, limit: int = 20) -> List[GeofenceEvent]:
        with self._data_lock:
            return list(self.events[-limit:])

    def clear_events(self) -> int:
        with self._data_lock:
            n = len(self.events)
            self.events = []
            self._save_events()
            return n

    def clear_location_history(self) -> int:
        with self._data_lock:
            n = len(self.location_history)
            self.location_history = []
            return n

    # ===== Stats & Status =====

    def get_status(self) -> Dict[str, Any]:
        with self._data_lock:
            current_place = None
            if self.current_location:
                cp = self.get_current_place()
                if cp:
                    current_place = cp.to_dict()
            return {
                "places_count": len(self.places),
                "rules_count": len(self.rules),
                "events_count": len(self.events),
                "has_location": self.current_location is not None,
                "current_location": self.current_location.to_dict() if self.current_location else None,
                "current_place": current_place,
                "data_dir": str(self.data_dir),
            }

    def get_full_dashboard(self) -> Dict[str, Any]:
        """Detailed dashboard for the UI."""
        with self._data_lock:
            places = [p.to_dict() for p in self.places.values()]
            rules = []
            for r in self.rules.values():
                d = r.to_dict()
                place = self.places.get(r.place_id)
                d["place_name"] = place.name if place else "(deleted)"
                d["place_icon"] = place.icon if place else "❓"
                rules.append(d)
            return {
                "places": places,
                "rules": rules,
                "events": [e.to_dict() for e in self.events[-20:]],
                "status": self.get_status(),
                "current_place": self.get_current_place().to_dict() if self.get_current_place() else None,
            }

    def reverse_geocode_simple(self, lat: float, lon: float) -> str:
        """
        Best-effort place name. We don't ship with geocoding (no external API),
        so this just returns coordinates. The phone can send a name in payload.
        """
        return f"({lat:.4f}, {lon:.4f})"

    # ===== Bulk operations =====

    def reset_all(self) -> None:
        """Wipe everything. DESTRUCTIVE."""
        with self._data_lock:
            self.places.clear()
            self.rules.clear()
            self.events.clear()
            self.location_history.clear()
            self.current_location = None
            self._entered_at.clear()
            self._was_inside.clear()
            self._dwell_fired.clear()
            self._save_places()
            self._save_rules()
            self._save_events()
            try: self.location_file.unlink()
            except Exception: pass
        logger.warning("📍 Geofence engine: all data reset")


def get_geofence_engine() -> GeofenceEngine:
    """Get the singleton GeofenceEngine."""
    return GeofenceEngine()


# ---------- Built-in place suggestions ----------

# Common place templates for quick setup
SAMPLE_PLACES = [
    {"name": "Home", "icon": "🏠"},
    {"name": "Work", "icon": "🏢"},
    {"name": "Gym", "icon": "💪"},
    {"name": "Coffee Shop", "icon": "☕"},
    {"name": "Grocery Store", "icon": "🛒"},
    {"name": "Park", "icon": "🌳"},
    {"name": "Commute", "icon": "🚗"},
]


SAMPLE_RULES = [
    {"place": "Home", "event": "arrive", "command": "play my evening playlist"},
    {"place": "Home", "event": "arrive", "command": "what's on my calendar tomorrow"},
    {"place": "Work", "event": "arrive", "command": "brief me on today's meetings"},
    {"place": "Work", "event": "depart", "command": "wrap up my day and commit my work"},
    {"place": "Gym", "event": "arrive", "command": "start workout playlist"},
    {"place": "Gym", "event": "depart", "command": "log my workout and show progress"},
    {"place": "Grocery Store", "event": "arrive", "command": "show me my shopping list"},
]
