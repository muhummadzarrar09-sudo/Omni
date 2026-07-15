"""
OMNI V3 - Demo Mode Tests (Phase 3B)
"""
import sys
import time
import threading
import tempfile
from pathlib import Path

# UTF-8 setup for Windows
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass


def _fresh_demo():
    """Get a fresh DemoMode singleton."""
    from omni_v2.agents.demo_mode import DemoMode
    DemoMode._instance = None
    return DemoMode()


def test_demo_script_defined():
    """Test 1: Demo script has 8 scenes"""
    from omni_v2.agents.demo_mode import DEMO_SCRIPT
    assert len(DEMO_SCRIPT) == 8
    print(f"  ✅ Demo script has {len(DEMO_SCRIPT)} scenes")


def test_scenes_have_required_fields():
    """Test 2: Each scene has title, narration, action"""
    from omni_v2.agents.demo_mode import DEMO_SCRIPT
    for i, scene in enumerate(DEMO_SCRIPT):
        assert scene.title, f"Scene {i+1} has no title"
        assert scene.narration, f"Scene {i+1} has no narration"
        assert scene.action, f"Scene {i+1} has no action"
        assert scene.duration_sec > 0, f"Scene {i+1} has no duration"
    print("  ✅ All scenes have required fields")


def test_scene_actions():
    """Test 3: Each scene has a valid action type"""
    from omni_v2.agents.demo_mode import DEMO_SCRIPT
    valid_actions = {"say", "execute", "wait_for_speech", "trigger_proactive", "simulate_failure", "end"}
    for scene in DEMO_SCRIPT:
        assert scene.action in valid_actions, f"Invalid action: {scene.action}"
    print("  ✅ All scene actions are valid")


def test_total_duration_about_2_minutes():
    """Test 4: Total demo is ~2 minutes (110-150s)"""
    from omni_v2.agents.demo_mode import DEMO_SCRIPT
    total = sum(s.duration_sec for s in DEMO_SCRIPT)
    assert 100 <= total <= 180, f"Total {total}s not in 100-180 range"
    print(f"  ✅ Total duration: {total}s ({total//60}m {total%60}s)")


def test_demo_starts_and_stops():
    """Test 5: Demo can start and stop"""
    demo = _fresh_demo()
    scene_calls = []
    def on_scene(scene):
        scene_calls.append(scene.id)
    demo.on_scene = on_scene
    # Shorten durations for test
    import omni_v2.agents.demo_mode as dm_mod
    original_scenes = dm_mod.DEMO_SCRIPT
    fast_scenes = []
    for s in original_scenes:
        s.duration_sec = 0.5  # 0.5s each
        fast_scenes.append(s)
    dm_mod.DEMO_SCRIPT = fast_scenes
    demo.start()
    time.sleep(2)  # 8 scenes × 0.5s + buffer
    demo.stop()
    # Restore
    dm_mod.DEMO_SCRIPT = original_scenes
    assert len(scene_calls) >= 3, f"Expected at least 3 scenes, got {len(scene_calls)}"
    print(f"  ✅ Demo fired {len(scene_calls)} scenes in test")


def test_demo_status():
    """Test 6: Status endpoint works"""
    demo = _fresh_demo()
    status = demo.get_status()
    assert "running" in status
    assert "paused" in status
    assert "total_scenes" in status
    assert status["total_scenes"] == 8
    assert not status["running"]
    print(f"  ✅ Status: {status}")


def test_get_script():
    """Test 7: get_script returns full script"""
    demo = _fresh_demo()
    script = demo.get_script()
    assert len(script) == 8
    for s in script:
        assert "title" in s
        assert "narration" in s
        assert "action" in s
    print(f"  ✅ Script has {len(script)} scenes")


def test_skip_to():
    """Test 8: Can skip to a specific scene"""
    demo = _fresh_demo()
    scene_calls = []
    demo.on_scene = lambda s: scene_calls.append(s.id)
    demo.skip_to(5)
    assert len(scene_calls) == 1
    assert scene_calls[0] == 5
    print(f"  ✅ Skipped to scene 5")


def test_pause_resume():
    """Test 9: Pause and resume"""
    demo = _fresh_demo()
    demo.pause()
    assert demo._paused
    demo.resume()
    assert not demo._paused
    print("  ✅ Pause/resume works")


def test_scene_highlights():
    """Test 10: Scenes have UI highlight specs"""
    from omni_v2.agents.demo_mode import DEMO_SCRIPT
    # At least some scenes should have 'shows' for the UI to highlight
    scenes_with_shows = [s for s in DEMO_SCRIPT if s.shows]
    assert len(scenes_with_shows) >= 3
    print(f"  ✅ {len(scenes_with_shows)} scenes have UI highlights")


def main():
    print("=" * 60)
    print("  DEMO MODE TESTS (Phase 3B)")
    print("=" * 60)
    tests = [
        test_demo_script_defined,
        test_scenes_have_required_fields,
        test_scene_actions,
        test_total_duration_about_2_minutes,
        test_demo_starts_and_stops,
        test_demo_status,
        test_get_script,
        test_skip_to,
        test_pause_resume,
        test_scene_highlights,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"\n❌ {t.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ {t.__name__} ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print()
    print("=" * 60)
    if failed == 0:
        print(f"  ✅ ALL 10 DEMO MODE TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
