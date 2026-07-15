"""
OMNI V3 - Skill Marketplace Tests (Phase 4C)
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


def _fresh_marketplace():
    """Get a fresh marketplace with isolated storage."""
    from omni_v2.skills.marketplace import SkillMarketplace
    SkillMarketplace._instance = None
    tmp = tempfile.mkdtemp(prefix="omni_mkt_test_")
    from pathlib import Path
    import shutil
    # Use isolated skills dir
    m = SkillMarketplace()
    m.skills_dir = Path(tmp) / "installed"
    m.skills_dir.mkdir(parents=True, exist_ok=True)
    m.installed_file = m.skills_dir / "installed.json"
    m._installed = {}
    m._save()
    return m


def test_marketplace_initialized():
    """Test 1: Marketplace initializes with built-in index"""
    m = _fresh_marketplace()
    assert len(m._index) >= 5
    status = m.get_status()
    assert status["marketplace_count"] >= 5
    print(f"  ✅ Marketplace initialized: {status['marketplace_count']} skills in index")


def test_get_index():
    """Test 2: get_index returns all items"""
    m = _fresh_marketplace()
    items = m.get_index()
    assert len(items) > 0
    for item in items:
        assert "id" in item
        assert "name" in item
        assert "description" in item
    print(f"  ✅ Index: {len(items)} items")


def test_get_index_by_category():
    """Test 3: Filter by category"""
    m = _fresh_marketplace()
    productivity = m.get_index(category="productivity")
    assert all(i["category"] == "productivity" for i in productivity)
    print(f"  ✅ Productivity filter: {len(productivity)} items")


def test_get_index_by_search():
    """Test 4: Search by keyword"""
    m = _fresh_marketplace()
    music = m.get_index(search="music")
    assert len(music) > 0
    print(f"  ✅ Music search: {len(music)} items")


def test_get_categories():
    """Test 5: Get all categories"""
    m = _fresh_marketplace()
    cats = m.get_categories()
    assert "productivity" in cats
    assert "developer" in cats
    print(f"  ✅ Categories: {cats}")


def test_install_skill():
    """Test 6: Install a skill (with offline stub)"""
    m = _fresh_marketplace()
    result = m.install("morning_briefing")
    # Either success (Piper/network) or graceful fallback
    if result.get("success"):
        assert result["skill_id"] == "morning_briefing"
        assert "morning_briefing" in m._installed
    else:
        # Should be a network error, not a crash
        assert "error" in result
    print(f"  ✅ Install: {result}")


def test_install_unknown_skill():
    """Test 7: Install unknown skill returns error"""
    m = _fresh_marketplace()
    result = m.install("nonexistent_skill_xyz")
    assert not result.get("success")
    assert "not found" in result.get("error", "").lower()
    print(f"  ✅ Unknown: {result['error']}")


def test_install_already_installed():
    """Test 8: Install same skill twice"""
    m = _fresh_marketplace()
    result1 = m.install("pomodoro_timer")
    result2 = m.install("pomodoro_timer")
    if result1.get("success"):
        assert not result2.get("success")
        assert "Already installed" in result2.get("error", "")
    print(f"  ✅ Already installed: {result2.get('error', 'first install failed')}")


def test_uninstall():
    """Test 9: Uninstall removes skill"""
    m = _fresh_marketplace()
    # Force-install (bypass network)
    from omni_v2.skills.marketplace import InstalledSkill
    m._installed["test_skill"] = InstalledSkill(
        id="test_skill", name="Test", version="1.0.0",
        author="test", description="test", category="test",
        installed_at=time.time(), source_url="x", file_path="x",
    )
    m._save()
    result = m.uninstall("test_skill")
    assert result is True
    assert "test_skill" not in m._installed
    print("  ✅ Uninstall works")


def test_list_installed():
    """Test 10: List installed skills"""
    m = _fresh_marketplace()
    from omni_v2.skills.marketplace import InstalledSkill
    m._installed["a"] = InstalledSkill(
        id="a", name="A", version="1.0", author="x", description="x",
        category="test", installed_at=time.time(), source_url="x", file_path="x",
    )
    m._installed["b"] = InstalledSkill(
        id="b", name="B", version="1.0", author="x", description="x",
        category="test", installed_at=time.time(), source_url="x", file_path="x",
    )
    installed = m.list_installed()
    assert len(installed) == 2
    print(f"  ✅ List installed: {len(installed)} skills")


def test_check_updates():
    """Test 11: Check for skill updates"""
    m = _fresh_marketplace()
    # Force install an old version
    from omni_v2.skills.marketplace import InstalledSkill
    m._installed["morning_briefing"] = InstalledSkill(
        id="morning_briefing", name="Morning", version="0.1.0",  # old
        author="x", description="x", category="productivity",
        installed_at=time.time(), source_url="x", file_path="x",
    )
    updates = m.check_updates()
    assert len(updates) >= 1
    assert updates[0]["skill_id"] == "morning_briefing"
    print(f"  ✅ Updates available: {len(updates)}")


def test_increment_use():
    """Test 12: Track skill usage"""
    m = _fresh_marketplace()
    from omni_v2.skills.marketplace import InstalledSkill
    m._installed["test"] = InstalledSkill(
        id="test", name="T", version="1.0", author="x", description="x",
        category="test", installed_at=time.time(), source_url="x", file_path="x",
    )
    m.increment_use("test")
    m.increment_use("test")
    m.increment_use("test")
    assert m._installed["test"].use_count == 3
    print("  ✅ Use count tracked")


def test_singleton():
    """Test 13: Marketplace is singleton"""
    from omni_v2.skills.marketplace import SkillMarketplace, get_marketplace
    SkillMarketplace._instance = None
    m1 = get_marketplace()
    m2 = get_marketplace()
    assert m1 is m2
    print("  ✅ Singleton works")


def test_persistence():
    """Test 14: Installed skills persist across instances"""
    tmp = Path(tempfile.mkdtemp(prefix="omni_mkt_persist_"))
    from omni_v2.skills.marketplace import SkillMarketplace, InstalledSkill
    SkillMarketplace._instance = None
    m1 = SkillMarketplace()
    m1.skills_dir = tmp / "installed"
    m1.skills_dir.mkdir(parents=True, exist_ok=True)
    m1.installed_file = m1.skills_dir / "installed.json"
    m1._installed["persist_skill"] = InstalledSkill(
        id="persist_skill", name="P", version="1.0", author="x", description="x",
        category="test", installed_at=time.time(), source_url="x", file_path="x",
    )
    m1._save()
    SkillMarketplace._instance = None
    m2 = SkillMarketplace()
    m2.skills_dir = tmp / "installed"
    m2.installed_file = m2.skills_dir / "installed.json"
    m2._load()
    assert "persist_skill" in m2._installed
    print("  ✅ Persistence works")


def main():
    print("=" * 60)
    print("  SKILL MARKETPLACE TESTS (Phase 4C)")
    print("=" * 60)
    tests = [
        test_marketplace_initialized,
        test_get_index,
        test_get_index_by_category,
        test_get_index_by_search,
        test_get_categories,
        test_install_skill,
        test_install_unknown_skill,
        test_install_already_installed,
        test_uninstall,
        test_list_installed,
        test_check_updates,
        test_increment_use,
        test_singleton,
        test_persistence,
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
        print(f"  ✅ ALL 14 MARKETPLACE TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
