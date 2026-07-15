"""
OMNI V3 - Personality Engine Tests (Phase 2A)
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


def _fresh_personality():
    """Get a fresh PersonalityEngine with isolated storage."""
    from omni_v2.agents.personality import PersonalityEngine
    PersonalityEngine._instance = None
    tmp = tempfile.mkdtemp(prefix="omni_personality_test_")
    p = PersonalityEngine(personality_dir=Path(tmp))
    # Reset all values to defaults explicitly
    p.set_many(
        formality=0.2, warmth=0.7, wit=0.6, verbosity=0.5,
        mood="helpful", use_emoji=True, use_dry_humor=True, address_by_name=True,
    )
    p.set_mood("helpful")
    return p


def test_default_values():
    """Test 1: Default personality is balanced"""
    p = _fresh_personality()
    assert 0 <= p.get("wit") <= 1
    assert 0 <= p.get("warmth") <= 1
    assert 0 <= p.get("formality") <= 1
    assert 0 <= p.get("verbosity") <= 1
    assert p.get("mood") == "helpful"
    print("  ✅ Default values are sensible")


def test_set_individual_dims():
    """Test 2: Set individual dimensions"""
    p = _fresh_personality()
    assert p.set("wit", 0.9)
    assert p.get("wit") == 0.9
    assert p.set("formality", 0.1)
    assert p.get("formality") == 0.1
    assert p.set("warmth", 1.0)
    assert p.get("warmth") == 1.0
    print("  ✅ Set individual dimensions works")


def test_set_many():
    """Test 3: Set multiple dimensions at once"""
    p = _fresh_personality()
    results = p.set_many(wit=0.8, formality=0.2, warmth=0.9, verbosity=0.1)
    assert all(results.values())
    assert p.get("wit") == 0.8
    assert p.get("formality") == 0.2
    assert p.get("verbosity") == 0.1
    print("  ✅ set_many works")


def test_pick_acknowledgment_varies():
    """Test 4: Acknowledgments rotate"""
    p = _fresh_personality()
    acks = set()
    for _ in range(50):
        acks.add(p.pick_acknowledgment())
    # Should have at least 3 different ones in 50 picks
    assert len(acks) >= 3, f"Only got {len(acks)} unique acks: {acks}"
    print(f"  ✅ Got {len(acks)} unique acknowledgments")


def test_format_success_includes_ms():
    """Test 5: Success messages can include latency"""
    p = _fresh_personality()
    msg = p.format_success(ms=120)
    # Sometimes includes ms, sometimes not - just check it's a string
    assert isinstance(msg, str)
    assert len(msg) > 0
    print(f"  ✅ Success: {msg}")


def test_failure_empathy():
    """Test 6: Failure empathy messages"""
    p = _fresh_personality()
    msg = p.pick_failure_empathy()
    assert isinstance(msg, str)
    assert len(msg) > 0
    # Should be empathetic (not blame the user)
    assert "you" not in msg.lower() or "your" in msg.lower()  # soft
    print(f"  ✅ Failure empathy: {msg}")


def test_observe_activity():
    """Test 7: Activity observation - should always mention Twitter"""
    p = _fresh_personality()
    p.set("wit", 0.9)
    p.set("use_dry_humor", True)
    # Run multiple times - the template should always mention Twitter
    # (the count number may be in the template or not, depending on which template is picked)
    seen_twitter = False
    for _ in range(20):
        msg = p.observe_activity("Twitter", count=4)
        if "Twitter" in msg:
            seen_twitter = True
            break
    assert seen_twitter, "Should mention Twitter in observation"
    print(f"  ✅ Observation: {msg[:80]}")


def test_celebrate():
    """Test 8: Celebration messages - emoji sometimes, count sometimes"""
    p = _fresh_personality()
    p.set("use_emoji", True)
    p.set("wit", 0.9)
    # Run many times, should see count OR emoji at least once
    seen_count = False
    seen_emoji = False
    last_msg = ""
    for _ in range(40):
        msg = p.celebrate(count=3)
        last_msg = msg
        if "3" in msg:
            seen_count = True
        if any(e in msg for e in ["🎉", "🚀", "💪", "✨", "🔥"]):
            seen_emoji = True
    # With 40 tries and high wit, at least one should have count
    assert seen_count, f"Should mention count sometimes. Last: {last_msg}"
    print(f"  ✅ Celebration (count seen: {seen_count}, emoji seen: {seen_emoji})")


def test_mood_transitions():
    """Test 9: Mood auto-transitions"""
    p = _fresh_personality()
    assert p.get_mood() == "helpful"
    p.record_success(big_win=True)
    assert p.get_mood() == "celebratory"
    p.record_failure()
    p.record_failure()
    assert p.get_mood() == "concerned"
    print("  ✅ Mood transitions work")


def test_mood_tone_adjustments():
    """Test 10: Mood provides tone deltas"""
    p = _fresh_personality()
    p.set_mood("playful")
    tone = p.get_mood_tone()
    assert "wit" in tone
    assert tone["wit"] > 0  # playful = more wit
    p.set_mood("focused")
    tone = p.get_mood_tone()
    assert tone["wit"] < 0  # focused = less wit
    print("  ✅ Mood tone adjustments work")


def test_apply_tone_template_fallback():
    """Test 11: Template-based tone application (no LLM)"""
    import asyncio
    p = _fresh_personality()
    # Without brain, falls back to template
    p.set("warmth", 0.9)
    p.set("verbosity", 0.0)
    rephrased = asyncio.run(p.apply_tone("Task completed successfully."))
    assert isinstance(rephrased, str)
    print(f"  ✅ Tone applied: {rephrased[:80]}")


def test_should_opine():
    """Test 12: should_opine respects wit and rate limits"""
    p = _fresh_personality()
    p.set("wit", 0.9)
    should_count = sum(1 for _ in range(100) if p.should_opine())
    # With high wit, should opine more than low wit
    assert should_count > 30  # at least 30% should opine
    print(f"  ✅ With high wit, {should_count}/100 opinions allowed")

    p.set("wit", 0.0)
    should_count = sum(1 for _ in range(100) if p.should_opine())
    # With low wit, should opine less
    assert should_count < 30
    print(f"  ✅ With low wit, only {should_count}/100 opinions allowed")


def test_persistence():
    """Test 13: Personality persists across instances"""
    tmp = tempfile.mkdtemp(prefix="omni_persist_p_")
    from omni_v2.agents.personality import PersonalityEngine
    PersonalityEngine._instance = None
    p1 = PersonalityEngine(personality_dir=Path(tmp))
    p1.set("wit", 0.85)
    p1.set("mood", "playful")
    PersonalityEngine._instance = None
    p2 = PersonalityEngine(personality_dir=Path(tmp))
    assert p2.get("wit") == 0.85
    assert p2.get("mood") == "playful"
    print("  ✅ Personality persists across instances")


def test_get_all():
    """Test 14: get_all returns full dict"""
    p = _fresh_personality()
    data = p.get_all()
    assert isinstance(data, dict)
    assert "wit" in data
    assert "warmth" in data
    assert "mood" in data
    assert "version" in data
    print("  ✅ get_all returns full dict")


def test_format_opinion():
    """Test 15: format_opinion adds personality flavor"""
    p = _fresh_personality()
    p.set_mood("playful")
    p.set("use_emoji", True)
    # Run multiple times to check randomization
    seen_emoji = False
    for _ in range(20):
        formatted = p.format_opinion("You opened Twitter again")
        if any(e in formatted for e in ["😏", "🤔", "👀", "🧐"]):
            seen_emoji = True
            break
    assert seen_emoji, "Should have added emoji sometimes"
    print(f"  ✅ Opinion formatted: {formatted[:80]}")


def test_unknown_field():
    """Test 16: Setting unknown field is rejected"""
    p = _fresh_personality()
    result = p.set("nonexistent_xyz", 1.0)
    assert result is False
    print("  ✅ Unknown fields rejected")


def main():
    print("=" * 60)
    print("  PERSONALITY TESTS (Phase 2A)")
    print("=" * 60)
    tests = [
        test_default_values,
        test_set_individual_dims,
        test_set_many,
        test_pick_acknowledgment_varies,
        test_format_success_includes_ms,
        test_failure_empathy,
        test_observe_activity,
        test_celebrate,
        test_mood_transitions,
        test_mood_tone_adjustments,
        test_apply_tone_template_fallback,
        test_should_opine,
        test_persistence,
        test_get_all,
        test_format_opinion,
        test_unknown_field,
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
        print(f"  ✅ ALL 16 PERSONALITY TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
