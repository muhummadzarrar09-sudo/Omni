"""
OMNI V3 - Onboarding Tests (Phase 3A)
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


def _fresh_onboarding():
    """Get a fresh OnboardingState with isolated storage."""
    from omni_v2.agents.onboarding import OnboardingState
    OnboardingState._instance = None
    tmp = tempfile.mkdtemp(prefix="omni_onboarding_test_")
    return OnboardingState(state_dir=Path(tmp))


def test_initial_state():
    """Test 1: Initial state is not completed, step 1"""
    s = _fresh_onboarding()
    assert not s.completed
    assert not s.skipped
    assert s.current_step == 1
    assert s.should_show() is True
    print("  ✅ Initial state: step 1, not completed, should show")


def test_get_current_step():
    """Test 2: Get current step returns step 1"""
    s = _fresh_onboarding()
    step = s.get_current()
    assert step is not None
    assert step.id == 1
    assert "OMNI" in step.title or "local" in step.body.lower()
    print(f"  ✅ Current step: {step.title}")


def test_advance_through_steps():
    """Test 3: Advance through all 5 steps"""
    s = _fresh_onboarding()
    seen_ids = []
    while True:
        current = s.get_current()
        if current is None:
            break
        seen_ids.append(current.id)
        s.advance()
    assert seen_ids == [1, 2, 3, 4, 5]
    assert s.completed
    assert not s.should_show()
    print(f"  ✅ Advanced through steps: {seen_ids}")


def test_skip():
    """Test 4: Skip onboarding"""
    s = _fresh_onboarding()
    s.skip()
    assert s.skipped
    assert not s.should_show()
    print("  ✅ Skip works")


def test_reset():
    """Test 5: Reset onboarding (re-onboard)"""
    s = _fresh_onboarding()
    s.skip()
    assert s.skipped
    s.reset()
    assert not s.skipped
    assert not s.completed
    assert s.current_step == 1
    assert s.should_show()
    print("  ✅ Reset works")


def test_persistence():
    """Test 6: Onboarding state persists across instances"""
    tmp = tempfile.mkdtemp(prefix="omni_ob_persist_")
    from omni_v2.agents.onboarding import OnboardingState
    OnboardingState._instance = None
    s1 = OnboardingState(state_dir=Path(tmp))
    s1.advance(name="Zarrar")
    OnboardingState._instance = None
    s2 = OnboardingState(state_dir=Path(tmp))
    assert s2.current_step == 2
    assert s2.name == "Zarrar"
    print("  ✅ Onboarding state persists")


def test_to_dict():
    """Test 7: to_dict returns full state"""
    s = _fresh_onboarding()
    d = s.to_dict()
    assert "completed" in d
    assert "current_step" in d
    assert "skipped" in d
    assert "should_show" in d
    assert "current_step_data" in d
    print(f"  ✅ to_dict: step {d['current_step']}, should_show={d['should_show']}")


def test_get_step_by_id():
    """Test 8: Get a specific step by ID"""
    s = _fresh_onboarding()
    step = s.get_step(3)
    assert step is not None
    assert step.id == 3
    assert "name" in step.body.lower() or "call you" in step.body.lower()
    print(f"  ✅ Step 3: {step.title}")


def test_invalid_step_id():
    """Test 9: Invalid step ID returns None"""
    s = _fresh_onboarding()
    step = s.get_step(99)
    assert step is None
    print("  ✅ Invalid step returns None")


def test_advance_with_name():
    """Test 10: Advance with name updates the name field"""
    s = _fresh_onboarding()
    s.advance(name="Alice")
    assert s.name == "Alice"
    s.advance(name="")  # empty name shouldn't overwrite
    assert s.name == "Alice"
    print("  ✅ Name captured on advance")


def main():
    print("=" * 60)
    print("  ONBOARDING TESTS (Phase 3A)")
    print("=" * 60)
    tests = [
        test_initial_state,
        test_get_current_step,
        test_advance_through_steps,
        test_skip,
        test_reset,
        test_persistence,
        test_to_dict,
        test_get_step_by_id,
        test_invalid_step_id,
        test_advance_with_name,
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
        print(f"  ✅ ALL 10 ONBOARDING TESTS PASSED")
    else:
        print(f"  ❌ {failed} TEST(S) FAILED")
    print("=" * 60)
    return failed


if __name__ == "__main__":
    sys.exit(main())
