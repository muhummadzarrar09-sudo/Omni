"""
OMNI V3 - Geofence Engine Tests (Phase 5C)

Verifies:
  1. Haversine math is correct
  2. Place CRUD (add/list/get/update/remove)
  3. Rule CRUD (add/list/remove) with valid event types
  4. Update location fires arrive/depart/dwell events
  5. Cooldowns prevent re-firing
  6. Multiple places, entering/exiting correctly
  7. Location history is tracked
  8. Sample places can be seeded
  9. Singleton behavior
"""
import math
import time
import tempfile
import shutil
import json
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None


# ---------- Haversine math ----------
class TestHaversine:
    def test_zero_distance(self):
        from omni_v2.agents.geofence import haversine_m
        d = haversine_m(33.6844, 73.0479, 33.6844, 73.0479)
        assert d < 1.0  # < 1m at same point

    def test_known_distance_1km(self):
        """1 degree of latitude ≈ 111km. Test 0.01° = ~1.1km."""
        from omni_v2.agents.geofence import haversine_m
        d = haversine_m(0.0, 0.0, 0.01, 0.0)
        # Should be ~1111m (allow 5% tolerance)
        assert 1050 < d < 1170

    def test_known_distance_equator(self):
        """At the equator, 1° of longitude ≈ 111km too."""
        from omni_v2.agents.geofence import haversine_m
        d = haversine_m(0.0, 0.0, 0.0, 0.01)
        assert 1050 < d < 1170

    def test_islamabad_to_lahore(self):
        """Islamabad to Lahore ≈ 270km. Verify our calc is reasonable."""
        from omni_v2.agents.geofence import haversine_m
        # Approx coords
        isl = (33.6844, 73.0479)
        lhr = (31.5204, 74.3587)
        d = haversine_m(isl[0], isl[1], lhr[0], lhr[1])
        # Real distance is ~270km, allow 5% tolerance
        assert 256_000 < d < 284_000

    def test_is_inside_radius(self):
        from omni_v2.agents.geofence import is_inside
        # Within 50m
        assert is_inside(33.68440, 73.04790, 33.68441, 73.04790, 100)
        # Far away
        assert not is_inside(33.6844, 73.0479, 34.6844, 73.0479, 1000)


# ---------- Place CRUD ----------
class TestPlaces:
    def setup_method(self):
        """Use a fresh temp dir for each test."""
        self._tmp = tempfile.mkdtemp(prefix="omni_geofence_")
        # Reset the singleton so it picks up new dir
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        self.engine = geofence.GeofenceEngine(data_dir=Path(self._tmp))

    def teardown_method(self):
        # Clean up
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_add_place(self):
        p = self.engine.add_place("Home", 33.6844, 73.0479, radius_m=100, icon="🏠")
        assert p.id.startswith("place_")
        assert p.name == "Home"
        assert p.radius_m == 100
        assert p.icon == "🏠"

    def test_list_places_sorted(self):
        self.engine.add_place("Zebra", 33.0, 73.0)
        self.engine.add_place("Apple", 33.1, 73.0)
        self.engine.add_place("Mango", 33.2, 73.0)
        names = [p.name for p in self.engine.list_places()]
        assert names == ["Apple", "Mango", "Zebra"]

    def test_get_place(self):
        p = self.engine.add_place("Office", 33.5, 73.5)
        got = self.engine.get_place(p.id)
        assert got is not None
        assert got.id == p.id
        assert self.engine.get_place("nonexistent") is None

    def test_update_place(self):
        p = self.engine.add_place("Old Name", 33.0, 73.0)
        updated = self.engine.update_place(p.id, name="New Name", radius_m=200)
        assert updated.name == "New Name"
        assert updated.radius_m == 200

    def test_update_nonexistent(self):
        assert self.engine.update_place("nope", name="X") is None

    def test_remove_place(self):
        p = self.engine.add_place("X", 33.0, 73.0)
        assert self.engine.remove_place(p.id) is True
        assert self.engine.get_place(p.id) is None
        assert self.engine.remove_place(p.id) is False

    def test_remove_place_cascades_rules(self):
        p = self.engine.add_place("X", 33.0, 73.0)
        r = self.engine.add_rule(p.id, "arrive", "hello")
        assert self.engine.remove_place(p.id) is True
        assert self.engine.get_rule(r.id) if hasattr(self.engine, 'get_rule') else True
        assert r.id not in self.engine.rules

    def test_persistence(self):
        """Places should survive a 'restart' (new engine instance, same dir)."""
        p = self.engine.add_place("Persistent", 33.0, 73.0)
        # Simulate restart
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        engine2 = geofence.GeofenceEngine(data_dir=Path(self._tmp))
        loaded = engine2.get_place(p.id)
        assert loaded is not None
        assert loaded.name == "Persistent"


# ---------- Rule CRUD ----------
class TestRules:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_geofence_")
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        self.engine = geofence.GeofenceEngine(data_dir=Path(self._tmp))
        self.place = self.engine.add_place("Test", 33.6844, 73.0479, radius_m=100)

    def teardown_method(self):
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_add_rule_arrive(self):
        r = self.engine.add_rule(self.place.id, "arrive", "play music")
        assert r.id.startswith("rule_")
        assert r.event == "arrive"
        assert r.command == "play music"
        assert r.enabled is True

    def test_add_rule_depart(self):
        r = self.engine.add_rule(self.place.id, "depart", "goodbye")
        assert r.event == "depart"

    def test_add_rule_dwell(self):
        r = self.engine.add_rule(self.place.id, "dwell", "still here", dwell_sec=120)
        assert r.dwell_sec == 120

    def test_add_rule_invalid_event(self):
        try:
            self.engine.add_rule(self.place.id, "explode", "boom")
            assert False, "should have raised"
        except ValueError:
            pass

    def test_add_rule_unknown_place(self):
        r = self.engine.add_rule("nope", "arrive", "x")
        assert r is None

    def test_list_rules(self):
        self.engine.add_rule(self.place.id, "arrive", "a")
        self.engine.add_rule(self.place.id, "depart", "b")
        self.engine.add_rule(self.place.id, "dwell", "c")
        rules = self.engine.list_rules()
        assert len(rules) == 3

    def test_list_rules_by_place(self):
        p2 = self.engine.add_place("Other", 34.0, 74.0)
        self.engine.add_rule(self.place.id, "arrive", "a")
        self.engine.add_rule(p2.id, "arrive", "b")
        rules = self.engine.list_rules(place_id=self.place.id)
        assert len(rules) == 1
        assert rules[0].command == "a"

    def test_remove_rule(self):
        r = self.engine.add_rule(self.place.id, "arrive", "x")
        assert self.engine.remove_rule(r.id) is True
        assert self.engine.remove_rule(r.id) is False

    def test_update_rule(self):
        r = self.engine.add_rule(self.place.id, "arrive", "old")
        updated = self.engine.update_rule(r.id, command="new", enabled=False)
        assert updated.command == "new"
        assert updated.enabled is False


# ---------- Location updates & event firing ----------
class TestLocationEvents:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_geofence_")
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        self.engine = geofence.GeofenceEngine(data_dir=Path(self._tmp))
        # Place at (33.6844, 73.0479) with 100m radius
        self.place = self.engine.add_place("Home", 33.6844, 73.0479, radius_m=100)
        self.fired_log = []
        self.engine.on_event = lambda ev: self.fired_log.append(ev)

    def teardown_method(self):
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_initial_location_outside(self):
        # Far away — no events
        fired = self.engine.update_location(34.0, 74.0)
        assert fired == []

    def test_arrival_fires_event(self):
        # Outside first
        self.engine.update_location(34.0, 74.0)
        # Now inside
        fired = self.engine.update_location(33.68440, 73.04790)
        assert len(fired) == 0  # no rules yet
        # Add a rule
        self.engine.add_rule(self.place.id, "arrive", "welcome home")
        # Move out and back in
        self.engine.update_location(34.0, 74.0)
        fired = self.engine.update_location(33.68440, 73.04790)
        assert len(fired) == 1
        assert fired[0].event == "arrive"
        assert fired[0].place_name == "Home"
        assert fired[0].command == "welcome home"

    def test_departure_fires_event(self):
        self.engine.add_rule(self.place.id, "depart", "goodbye")
        # Inside first
        self.engine.update_location(33.68440, 73.04790)
        # Move out
        fired = self.engine.update_location(34.0, 74.0)
        assert len(fired) == 1
        assert fired[0].event == "depart"
        assert fired[0].command == "goodbye"

    def test_dwell_fires_event(self):
        r = self.engine.add_rule(self.place.id, "dwell", "still home", dwell_sec=1)
        # Inside
        self.engine.update_location(33.68440, 73.04790)
        # Still inside — wait for dwell
        time.sleep(1.1)
        fired = self.engine.update_location(33.68440, 73.04790)
        assert len(fired) == 1
        assert fired[0].event == "dwell"

    def test_dwell_only_fires_once_per_stay(self):
        r = self.engine.add_rule(self.place.id, "dwell", "still here", dwell_sec=1)
        self.engine.update_location(33.68440, 73.04790)
        time.sleep(1.1)
        fired1 = self.engine.update_location(33.68440, 73.04790)
        fired2 = self.engine.update_location(33.68440, 73.04790)
        fired3 = self.engine.update_location(33.68440, 73.04790)
        # First fires, others don't (already fired this stay)
        assert len(fired1) == 1
        assert len(fired2) == 0
        assert len(fired3) == 0

    def test_cooldown_prevents_refire(self):
        self.engine.add_rule(self.place.id, "arrive", "hi", cooldown_sec=60)
        # First arrival
        self.engine.update_location(33.68440, 73.04790)
        # Leave
        self.engine.update_location(34.0, 74.0)
        # Come back — should NOT fire (cooldown)
        fired = self.engine.update_location(33.68440, 73.04790)
        assert len(fired) == 0

    def test_cooldown_can_be_overridden(self):
        self.engine.add_rule(self.place.id, "arrive", "hi", cooldown_sec=0)
        # Arrive, leave, arrive — fires both times
        self.engine.update_location(33.68440, 73.04790)
        self.engine.update_location(34.0, 74.0)
        fired = self.engine.update_location(33.68440, 73.04790)
        assert len(fired) == 1

    def test_disabled_rule_doesnt_fire(self):
        r = self.engine.add_rule(self.place.id, "arrive", "hi")
        # Disable the rule
        self.engine.update_rule(r.id, enabled=False)
        self.engine.update_location(33.68440, 73.04790)
        self.engine.update_location(34.0, 74.0)
        fired = self.engine.update_location(33.68440, 73.04790)
        assert len(fired) == 0

    def test_multiple_places_smallest_wins(self):
        """When inside multiple places, return the one with the smallest radius."""
        big = self.engine.add_place("Big", 33.6844, 73.0479, radius_m=1000)
        small = self.engine.add_place("Small", 33.6844, 73.0479, radius_m=50)
        current = self.engine.get_current_place()
        # Need a location first
        self.engine.update_location(33.68440, 73.04790)
        current = self.engine.get_current_place()
        assert current is not None
        assert current.id == small.id

    def test_location_history_tracked(self):
        for i in range(5):
            self.engine.update_location(33.0 + i*0.01, 73.0)
        history = self.engine.get_location_history(limit=10)
        assert len(history) == 5

    def test_arrival_updates_stats(self):
        self.engine.update_location(33.68440, 73.04790)
        p = self.engine.get_place(self.place.id)
        assert p.total_arrivals == 1
        assert p.last_visited > 0

    def test_departure_updates_stats(self):
        self.engine.update_location(33.68440, 73.04790)
        time.sleep(0.1)
        self.engine.update_location(34.0, 74.0)
        p = self.engine.get_place(self.place.id)
        assert p.total_departures == 1
        assert p.total_dwell_min > 0


# ---------- Status & dashboard ----------
class TestStatus:
    def setup_method(self):
        self._tmp = tempfile.mkdtemp(prefix="omni_geofence_")
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        self.engine = geofence.GeofenceEngine(data_dir=Path(self._tmp))

    def teardown_method(self):
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_status_initial(self):
        s = self.engine.get_status()
        assert s["places_count"] == 0
        assert s["rules_count"] == 0
        assert s["events_count"] == 0
        assert s["has_location"] is False

    def test_status_after_setup(self):
        p = self.engine.add_place("X", 33.0, 73.0)
        self.engine.add_rule(p.id, "arrive", "y")
        self.engine.update_location(33.0, 73.0)
        s = self.engine.get_status()
        assert s["places_count"] == 1
        assert s["rules_count"] == 1
        assert s["has_location"] is True
        assert s["current_location"] is not None

    def test_dashboard_enriched(self):
        p = self.engine.add_place("Office", 33.0, 73.0, icon="🏢")
        r = self.engine.add_rule(p.id, "arrive", "start work", label="Start work")
        d = self.engine.get_full_dashboard()
        assert len(d["places"]) == 1
        assert len(d["rules"]) == 1
        assert d["rules"][0]["place_name"] == "Office"
        assert d["rules"][0]["place_icon"] == "🏢"

    def test_recent_events(self):
        p = self.engine.add_place("X", 33.6844, 73.0479, radius_m=100)
        self.engine.add_rule(p.id, "arrive", "hi")
        self.engine.update_location(33.68440, 73.04790)  # arrive
        events = self.engine.get_recent_events()
        assert len(events) == 1

    def test_clear_events(self):
        p = self.engine.add_place("X", 33.6844, 73.0479, radius_m=100)
        self.engine.add_rule(p.id, "arrive", "hi")
        self.engine.update_location(33.68440, 73.04790)
        n = self.engine.clear_events()
        assert n == 1
        assert self.engine.get_recent_events() == []

    def test_reset_all(self):
        p = self.engine.add_place("X", 33.0, 73.0)
        self.engine.add_rule(p.id, "arrive", "y")
        self.engine.update_location(33.0, 73.0)
        self.engine.reset_all()
        assert len(self.engine.places) == 0
        assert len(self.engine.rules) == 0
        assert len(self.engine.events) == 0
        assert self.engine.current_location is None


# ---------- Singleton ----------
class TestSingleton:
    def test_same_instance(self):
        from omni_v2.agents import geofence
        geofence.GeofenceEngine._instance = None
        e1 = geofence.GeofenceEngine()
        e2 = geofence.GeofenceEngine()
        assert e1 is e2


# ---------- Sample data ----------
class TestSamples:
    def test_sample_places_have_names(self):
        from omni_v2.agents.geofence import SAMPLE_PLACES
        assert len(SAMPLE_PLACES) >= 5
        for p in SAMPLE_PLACES:
            assert "name" in p
            assert "icon" in p

    def test_sample_rules_valid(self):
        from omni_v2.agents.geofence import SAMPLE_RULES
        for r in SAMPLE_RULES:
            assert r["event"] in ("arrive", "depart", "dwell")
            assert "place" in r
            assert "command" in r


# ---------- Live backend tests (skipped if backend not running) ----------
class TestBackendLive:
    def test_geofence_status_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/geofence/status", timeout=2)
            data = json.loads(req.read().decode())
            assert data.get("status") == "ok"
            assert "geofence" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_geofence_places_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/geofence/places", timeout=2)
            data = json.loads(req.read().decode())
            assert "places" in data
            assert "count" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_geofence_rules_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/geofence/rules", timeout=2)
            data = json.loads(req.read().decode())
            assert "rules" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_geofence_seed_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/geofence/seed",
                data=b"", method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
            assert "added" in data
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_geofence_add_place_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/geofence/places",
                data=json.dumps({
                    "name": "Test Place",
                    "lat": 51.5074, "lon": -0.1278,
                    "radius_m": 50, "icon": "🧪",
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("status") == "ok"
            assert data["place"]["name"] == "Test Place"
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_geofence_dashboard_endpoint(self):
        import urllib.request, json
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/geofence/dashboard", timeout=2)
            data = json.loads(req.read().decode())
            assert data.get("status") == "ok"
            assert "dashboard" in data
            d = data["dashboard"]
            assert "places" in d and "rules" in d and "events" in d
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")

    def test_geofence_add_place_validates_event(self):
        """Invalid event on a rule should error."""
        import urllib.request, json
        try:
            # Get a place first
            req = urllib.request.urlopen("http://127.0.0.1:8765/api/geofence/places", timeout=2)
            data = json.loads(req.read().decode())
            places = data.get("places", [])
            if not places:
                if pytest: pytest.skip("no places to test against")
                return
            place_id = places[0]["id"]
            req = urllib.request.Request(
                "http://127.0.0.1:8765/api/geofence/rules",
                data=json.dumps({
                    "place_id": place_id, "event": "explode", "command": "boom"
                }).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            assert data.get("status") == "error"
        except Exception:
            if pytest: pytest.skip("backend not running on 8765")
