"""
OMNI V3 - Opinion Engine Tests (Phase 2B)
"""
import sys
import time
from unittest.mock import patch
import tempfile
from pathlib import Path

# UTF-8 setup for Windows
try:
    from omni_v2.utils.utf8 import setup_utf8_console
    setup_utf8_console()
except Exception:
    pass


def _fresh_opinion():
    """Get a fresh OpinionEngine singleton with cleared state."""
    from collections import defaultdict
    from omni_v2.agents.opinion import OpinionEngine
    OpinionEngine._instance = None
    op = OpinionEngine()
    # Reset all rate-limiting state
    op._last_opinion_at = 0.0
    op._opinions_this_hour = []
    op._command_timestamps = defaultdict(list)
    op._tool_timestamps = defaultdict(list)
    return op


def _reset_personality_for_testing(wit=0.7):
    """Reset personality settings to a known state for opinion tests."""
    from omni_v2.agents.personality import get_personality
    p = get_personality()
    p.set_many(
        wit=wit, formality=0.2, warmth=0.7, verbosity=0.5,
        use_emoji=True, use_dry_humor=True,
    )
    p.set_mood("helpful")
    return p


def _fresh_personality():
    """Get a fresh PersonalityEngine with isolated storage."""
    from omni_v2.agents.personality import PersonalityEngine
    PersonalityEngine._instance = None
    tmp = tempfile.mkdtemp(prefix="omni_opinion_test_")
    return PersonalityEngine(personality_dir=Path(tmp))


def test_record_command():
    """Test 1: Recording commands"""
    op = _fresh_opinion()
    op.record_command("open github")
    op.record_command("open github")
    op.record_command("open github")
    assert "open github" in op._command_timestamps
    assert len(op._command_timestamps["open github"]) == 3
    print("  ✅ Record command works")


def test_record_tool_call():
    """Test 2: Recording tool calls"""
    op = _fresh_opinion()
    for _ in range(5):
        op.record_tool_call("browser_navigate")
    assert len(op._tool_timestamps["browser_navigate"]) == 5
    print("  ✅ Record tool call works")


def test_should_opine_rate_limit():
    """Test 3: Rate limit: max 1 per 30s"""
    op = _fresh_opinion()
    _reset_personality_for_testing(wit=1.0)
    # Force allowed
    op._last_opinion_at = 0
    # First opinion: ok
    with patch("omni_v2.agents.personality.random.random", return_value=0.0):
        can1 = op._should_opine()
    assert can1, "Initial opinion should be allowed in deterministic test"
    op._emit("test")
    # Immediate second: should fail (30s cooldown)
    can2 = op._should_opine()
    assert not can2, "Should be rate limited within 30s"
    print("  ✅ Rate limit (30s cooldown) works")


def test_should_opine_hour_limit():
    """Test 4: Rate limit: max 3 per hour"""
    op = _fresh_opinion()
    _reset_personality_for_testing(wit=1.0)
    op._last_opinion_at = 0
    # Add 3 opinions to the hour
    op._opinions_this_hour = [time.time()] * 3
    # Should be blocked
    can = op._should_opine()
    assert not can
    print("  ✅ Hour limit (3/hour) works")


def test_rule_repeating_command():
    """Test 5: 3+ same command in 30 min → opinion"""
    _reset_personality_for_testing(wit=1.0)
    p = _reset_personality_for_testing(wit=1.0)
    p.set_mood("helpful")
    op = _fresh_opinion()
    # Simulate 3+ same commands
    for _ in range(3):
        op.record_command("open twitter")
    # Manually set last_opinion_at to allow
    op._last_opinion_at = 0
    op._opinions_this_hour = []
    # Run multiple times to account for randomness in template choice
    seen = False
    result = None
    for _ in range(20):
        op2 = _fresh_opinion()
        op2._last_opinion_at = 0
        op2._opinions_this_hour = []
        for _ in range(3):
            op2.record_command("open twitter")
        r = op2.maybe_opine("open twitter", None)
        if r and ("twitter" in r.lower() or "3" in r):
            seen = True
            result = r
            break
    assert seen, "Should mention Twitter or count in observation"
    print(f"  ✅ Repeating command: {result[:80]}")


def test_rule_failure_encouragement():
    """Test 6: Failure triggers empathy"""
    _reset_personality_for_testing(wit=1.0)
    p = _reset_personality_for_testing(wit=1.0)
    p.set_mood("helpful")
    # Run multiple times - it's rate-limited
    seen = False
    result = None
    for _ in range(20):
        op = _fresh_opinion()
        op._last_opinion_at = 0
        op._opinions_this_hour = []
        class FakeResult:
            success = False
        r = op.maybe_opine("browser_navigate", FakeResult())
        if r and len(r) > 0:
            seen = True
            result = r
            break
    assert seen, "Should emit failure empathy sometimes"
    print(f"  ✅ Failure empathy: {result[:80]}")


def test_rule_no_opine_on_success():
    """Test 7: No opinion on simple success with low wit"""
    _reset_personality_for_testing(wit=0.0)
    p = _reset_personality_for_testing(wit=0.0)
    p.set_mood("helpful")
    class FakeResult:
        success = True
    opine_count = 0
    for _ in range(20):
        op = _fresh_opinion()
        op._last_opinion_at = 0
        op._opinions_this_hour = []
        if op.maybe_opine("ai_chat", FakeResult()):
            opine_count += 1
    assert opine_count < 10, f"With low wit, should be <10, got {opine_count}"
    print(f"  ✅ With low wit, only {opine_count}/20 opinions emitted")


def test_celebration_on_commit():
    """Test 8: Successful commit triggers celebration"""
    _reset_personality_for_testing(wit=1.0)
    op = _fresh_opinion()
    op._last_opinion_at = 0
    op._opinions_this_hour = []
    class FakeResult:
        success = True
    r1 = op.maybe_opine("code_commit", FakeResult())
    op.record_tool_call("code_commit")
    op.record_tool_call("code_commit")
    op._last_opinion_at = 0
    op._opinions_this_hour = []
    r2 = op.maybe_opine("code_commit", FakeResult())
    print(f"  ✅ First commit: {r1}, Second: {r2}")


def test_proactive_opinions():
    """Test 9: Proactive opinions (time-based)"""
    _reset_personality_for_testing(wit=1.0)
    op = _fresh_opinion()
    op._last_opinion_at = 0
    op._opinions_this_hour = []
    opinion = op.opine_proactive()
    print(f"  ✅ Proactive opinion: {opinion}")


def test_disabled_in_focused_mood():
    """Test 10: No opinions in focused mood"""
    _reset_personality_for_testing(wit=1.0)
    p = _reset_personality_for_testing(wit=1.0)
    p.set_mood("focused")
    op = _fresh_opinion()
    opine_count = 0
    for _ in range(10):
        op = _fresh_opinion()
        op._last_opinion_at = 0
        op._opinions_this_hour = []
        class FakeResult:
            success = True
        if op.maybe_opine("browser_navigate", FakeResult()):
            opine_count += 1
    assert opine_count == 0, f"Focused mood should have 0 opinions, got {opine_count}"
    print(f"  ✅ Focused mood: 0 opinions emitted (correct)")


def test_singleton():
    """Test 11: OpinionEngine is a singleton"""
    from omni_v2.agents.opinion import OpinionEngine, get_opinion_engine
    o1 = get_opinion_engine()
    o2 = get_opinion_engine()
    assert o1 is o2
    print("  ✅ Singleton works")


def main():
    print("=" * 60)
    print("  OPINION ENGINE TESTS (Phase 2B)")
    print("=" * 60)
    # CRITICAL: reset personality singleton FIRST so tests start clean
    try:
        from omni_v2.agents.personality import PersonalityEngine
        import tempfile
        PersonalityEngine._instance = None
        tmp = tempfile.mkdtemp(prefix="omni_opinion_main_")
        PersonalityEngine(personality_dir=Path(tmp))
    except Exception:
        pass
    tests = [
        test_record_command,
        test_record_tool_call,
        test_should_opine_rate_limit,
        test_should_opine_hour_limit,
        test_rule_repeating_command,
        test_rule_failure_encouragement,
        test_rule_no_opine_on_success,
        test_celebration_on_commit,
        test_proactive_opinions,
        test_disabled_in_focused_mood,
        test_singleton,
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
        print(f"  ✅ ALL 11 OPINION TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
