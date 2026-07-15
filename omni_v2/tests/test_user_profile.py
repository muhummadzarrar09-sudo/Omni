"""
OMNI V3 - User Profile Tests (Phase 1A)
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


def _fresh_store():
    """Get a fresh UserProfileStore with isolated storage."""
    from omni_v2.agents.user_profile import UserProfileStore
    # Reset singleton to get a fresh instance
    UserProfileStore._instance = None
    tmp = tempfile.mkdtemp(prefix="omni_profile_test_")
    return UserProfileStore(profile_dir=Path(tmp))


def test_profile_creation():
    """Test 1: Profile is created on first load"""
    store = _fresh_store()
    assert store.get("name") == ""
    assert store.get("timezone") == "UTC"
    assert store.get("formality") == "casual"
    print("  ✅ Profile created with defaults")


def test_set_get_roundtrip():
    """Test 2: Set and get values"""
    store = _fresh_store()
    assert store.set("name", "Zarrar")
    assert store.get("name") == "Zarrar"
    assert store.set("pronouns", "he/him")
    assert store.set("favorite_voice", "friday")
    assert store.get("favorite_voice") == "friday"
    print("  ✅ Set/get roundtrip works")


def test_set_many():
    """Test 3: Set multiple fields at once"""
    store = _fresh_store()
    results = store.set_many(
        name="Alice",
        timezone="America/New_York",
        work_start_hour=8,
        hobbies=["coding", "music"],
    )
    assert all(results.values())
    assert store.get("name") == "Alice"
    assert store.get("timezone") == "America/New_York"
    assert store.get("work_start_hour") == 8
    assert store.get("hobbies") == ["coding", "music"]
    print("  ✅ set_many works")


def test_forget_field():
    """Test 4: Forgetting a field reverts to default"""
    store = _fresh_store()
    store.set("name", "Zarrar")
    store.set("favorite_music", "jazz")
    assert store.get("name") == "Zarrar"
    assert store.get("favorite_music") == "jazz"
    store.forget("name")
    assert store.get("name") == ""
    store.forget("favorite_music")
    assert store.get("favorite_music") == "lo-fi"
    print("  ✅ Forget reverts to default")


def test_persistence():
    """Test 5: Profile persists across instances"""
    tmp = tempfile.mkdtemp(prefix="omni_persist_")
    from omni_v2.agents.user_profile import UserProfileStore
    UserProfileStore._instance = None
    s1 = UserProfileStore(profile_dir=Path(tmp))
    s1.set("name", "Zarrar")
    s1.set("favorite_voice", "friday")
    # Force a save
    s1._save()
    UserProfileStore._instance = None
    s2 = UserProfileStore(profile_dir=Path(tmp))
    assert s2.get("name") == "Zarrar"
    assert s2.get("favorite_voice") == "friday"
    print("  ✅ Profile persists across instances")


def test_corruption_recovery():
    """Test 6: Corrupted JSON is recovered gracefully"""
    tmp = tempfile.mkdtemp(prefix="omni_corrupt_")
    Path(tmp, "user.json").write_text("{ this is { not valid json", encoding="utf-8")
    from omni_v2.agents.user_profile import UserProfileStore
    UserProfileStore._instance = None
    store = UserProfileStore(profile_dir=Path(tmp))
    assert store.get("name") == ""
    backup = Path(tmp, "user.corrupted.json")
    assert backup.exists()
    print("  ✅ Corrupted profile recovered")


def test_behavioral_learning():
    """Test 7: Recording commands and tool usage updates stats"""
    store = _fresh_store()
    for _ in range(15):
        store.record_command("open github")
    for _ in range(5):
        store.record_tool_usage("browser_navigate")
    for _ in range(3):
        store.record_tool_usage("vscode_open")
    store.record_session_duration(45)
    store.record_peak_hour(10)
    store.record_peak_hour(15)
    stats = store.get_stats()
    assert stats["total_commands"] >= 15
    assert stats["longest_session_min"] == 45
    assert 10 in stats["peak_hours"]
    assert 15 in stats["peak_hours"]
    top_tools = store.get_top_tools(2)
    assert top_tools[0][0] == "browser_navigate"
    assert top_tools[0][1] == 5
    print("  ✅ Behavioral learning works")


def test_unknown_field():
    """Test 8: Setting unknown field is rejected"""
    store = _fresh_store()
    result = store.set("nonexistent_field_xyz", "value")
    assert result is False
    print("  ✅ Unknown fields rejected")


def test_get_all():
    """Test 9: get_all returns full profile"""
    store = _fresh_store()
    store.set("name", "Zarrar")
    data = store.get_all()
    assert isinstance(data, dict)
    assert data["name"] == "Zarrar"
    assert "version" in data
    assert "hobbies" in data
    print("  ✅ get_all returns full dict")


def test_greeting_name():
    """Test 10: Greeting name extraction"""
    store = _fresh_store()
    assert store.greeting_name() == ""
    store.set("name", "Zarrar")
    assert store.greeting_name() == "Zarrar"
    print("  ✅ Greeting name extraction works")


def test_concurrent_access():
    """Test 11: Thread-safe concurrent updates"""
    import threading
    store = _fresh_store()
    errors = []
    def worker(i):
        try:
            for j in range(10):
                store.record_command(f"thread-{i}-cmd-{j}")
                store.record_tool_usage(f"tool-{i}-{j}")
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Thread errors: {errors}"
    assert store.get("total_commands") >= 50
    print("  ✅ Concurrent access is thread-safe")


def test_reset_all():
    """Test 12: reset_all() clears everything"""
    store = _fresh_store()
    store.set("name", "Zarrar")
    store.set("favorite_voice", "friday")
    store.record_command("test")
    store.reset_all()
    assert store.get("name") == ""
    assert store.get("favorite_voice") == "jarvis"
    assert store.get("total_commands") == 0
    print("  ✅ reset_all works")


def main():
    print("=" * 60)
    print("  USER PROFILE TESTS (Phase 1A)")
    print("=" * 60)
    tests = [
        test_profile_creation,
        test_set_get_roundtrip,
        test_set_many,
        test_forget_field,
        test_persistence,
        test_corruption_recovery,
        test_behavioral_learning,
        test_unknown_field,
        test_get_all,
        test_greeting_name,
        test_concurrent_access,
        test_reset_all,
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
        print(f"  ✅ ALL 12 USER PROFILE TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
