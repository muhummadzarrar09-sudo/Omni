"""
OMNI V3 - Stats Engine Tests (Phase 3C)
"""
import sys
import time
import tempfile
from pathlib import Path

# UTF-8 setup for Windows
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass


def _fresh_stats():
    """Get a fresh StatsEngine singleton."""
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    return StatsEngine()


def _setup_data():
    """Create some test data: profile + sessions."""
    from omni_v2.agents.user_profile import UserProfileStore
    from omni_v2.memory.session_memory import SessionMemoryStore
    UserProfileStore._instance = None
    SessionMemoryStore._instance = None
    tmp = tempfile.mkdtemp(prefix="omni_stats_test_")
    profile = UserProfileStore(profile_dir=Path(tmp))
    mem = SessionMemoryStore(memory_dir=Path(tmp))
    profile.set("name", "Test User")
    # Create sessions
    for i in range(3):
        mem.start_session()
        for j in range(5 + i):
            mem.record_command(f"open tool{j}")
            mem.record_tool_call(f"tool_{j % 3}", {}, "ok")
        mem.end_session()
    return profile, mem


def test_get_lifetime_stats():
    """Test 1: Lifetime stats aggregate correctly"""
    _setup_data()
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    s = StatsEngine()
    stats = s.get_lifetime_stats()
    assert stats["total_commands"] >= 15  # 3 sessions × 5 commands
    assert stats["total_sessions"] >= 3
    print(f"  ✅ Lifetime: {stats['total_commands']} cmds, {stats['total_sessions']} sessions")


def test_get_today_stats():
    """Test 2: Today's stats work"""
    _setup_data()
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    s = StatsEngine()
    today = s.get_today_stats()
    assert "date" in today
    assert "total_commands" in today
    assert today["total_commands"] >= 0
    print(f"  ✅ Today: {today['total_commands']} commands on {today['date']}")


def test_tool_breakdown():
    """Test 3: Tool usage breakdown"""
    _setup_data()
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    s = StatsEngine()
    breakdown = s.get_tool_breakdown(days=30)
    assert isinstance(breakdown, list)
    assert len(breakdown) > 0
    # First should be most-used
    if breakdown:
        assert breakdown[0][1] >= breakdown[-1][1]  # sorted desc
    print(f"  ✅ Tool breakdown: {len(breakdown)} tools, top: {breakdown[0] if breakdown else 'none'}")


def test_peak_hours():
    """Test 4: Peak hours returns 24-hour dict"""
    _setup_data()
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    s = StatsEngine()
    hours = s.get_peak_hours(days=7)
    assert len(hours) == 24
    # All keys are 0-23
    for h in range(24):
        assert h in hours
    print(f"  ✅ Peak hours: {len(hours)} hours tracked")


def test_weekly_chart():
    """Test 5: Weekly chart returns day breakdown"""
    _setup_data()
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    s = StatsEngine()
    chart = s.get_weekly_chart(days=7)
    assert isinstance(chart, dict)
    print(f"  ✅ Weekly chart: {len(chart)} days")


def test_estimate_time_saved():
    """Test 6: Time saved estimate"""
    _setup_data()
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    s = StatsEngine()
    saved = s.estimate_time_saved()
    assert "commands" in saved
    assert "seconds_saved" in saved
    assert "human_readable" in saved
    # Should be > 0 if there are commands
    if saved["commands"] > 0:
        assert saved["seconds_saved"] > 0
    print(f"  ✅ Time saved: {saved['human_readable']}")


def test_humanize_time():
    """Test 7: Humanize time formatting"""
    from omni_v2.agents.stats import StatsEngine
    s = StatsEngine()
    assert s._humanize_time(30) == "30s"
    assert s._humanize_time(60) == "1m 0s"
    assert s._humanize_time(90) == "1m 30s"
    assert s._humanize_time(3600) == "1h 0m"
    assert s._humanize_time(3660) == "1h 1m"
    print("  ✅ Humanize time works")


def test_get_full_dashboard():
    """Test 8: Full dashboard has all sections"""
    _setup_data()
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    s = StatsEngine()
    dash = s.get_full_dashboard()
    assert "lifetime" in dash
    assert "today" in dash
    assert "tool_breakdown" in dash
    assert "peak_hours" in dash
    assert "weekly_chart" in dash
    assert "time_saved" in dash
    print(f"  ✅ Dashboard: {len(dash)} sections")


def test_singleton():
    """Test 9: StatsEngine is singleton"""
    from omni_v2.agents.stats import StatsEngine, get_stats_engine
    StatsEngine._instance = None
    s1 = get_stats_engine()
    s2 = get_stats_engine()
    assert s1 is s2
    print("  ✅ Singleton works")


def test_empty_data_handling():
    """Test 10: Handles empty data gracefully"""
    from omni_v2.agents.user_profile import UserProfileStore
    from omni_v2.memory.session_memory import SessionMemoryStore
    UserProfileStore._instance = None
    SessionMemoryStore._instance = None
    tmp = tempfile.mkdtemp(prefix="omni_empty_stats_")
    UserProfileStore(profile_dir=Path(tmp))
    SessionMemoryStore(memory_dir=Path(tmp))
    from omni_v2.agents.stats import StatsEngine
    StatsEngine._instance = None
    s = StatsEngine()
    stats = s.get_lifetime_stats()
    # Should not crash with empty data
    assert stats["total_commands"] >= 0
    print("  ✅ Empty data handled gracefully")


def main():
    print("=" * 60)
    print("  STATS ENGINE TESTS (Phase 3C)")
    print("=" * 60)
    tests = [
        test_get_lifetime_stats,
        test_get_today_stats,
        test_tool_breakdown,
        test_peak_hours,
        test_weekly_chart,
        test_estimate_time_saved,
        test_humanize_time,
        test_get_full_dashboard,
        test_singleton,
        test_empty_data_handling,
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
        print(f"  ✅ ALL 10 STATS TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
