"""
Tests for Automation Triggers (Phase 13, #5) - webhook/schedule/file wake OMNI.
Run: python -m pytest omni_v2/tests/test_automation.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_auto_")))

from omni_v2.automation.triggers import TriggerManager, make_runner
from omni_v2.brain.goals import GoalStack


def _mgr(tmp, runner=None):
    return TriggerManager(runner=runner, triggers_path=Path(tmp) / "triggers.json")


def test_add_and_get():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mgr(tmp)
        a = m.add("deploy", "webhook", "goal", {"intent": "deploy the app"})
        assert m.get("deploy").name == "deploy"
        assert a.action == "goal"


def test_fire_runs_runner():
    with tempfile.TemporaryDirectory() as tmp:
        calls = []
        def runner(action, args):
            calls.append((action, args))
            return {"ok": True}
        m = _mgr(tmp, runner=runner)
        m.add("hook", "webhook", "notify", {"text": "hello"})
        res = m.fire("hook", {"text": "overridden"})
        assert res["ok"] is True
        # payload overrides action_args
        assert calls[0][1]["text"] == "overridden"


def test_fire_disabled():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mgr(tmp, runner=lambda a, ar: {"ok": True})
        m.add("x", "webhook", "notify", {})
        m.get("x").enabled = False
        m._save()
        res = m.fire("x")
        assert res["ok"] is False


def test_fire_unknown():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mgr(tmp)
        res = m.fire("nope")
        assert res["ok"] is False


def test_webhook_secret():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mgr(tmp, runner=lambda a, ar: {"ok": True})
        m.add("sec", "webhook", "notify", {}, secret="abc")
        assert m.handle_webhook("sec", {}, token="wrong")["ok"] is False
        assert m.handle_webhook("sec", {}, token="abc")["ok"] is True


def test_persists_across_reload():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "triggers.json"
        m = TriggerManager(runner=lambda a, ar: {"ok": True}, triggers_path=p)
        m.add("keep", "schedule", "research", {"topic": "ai"})
        m.fire("keep")
        m2 = TriggerManager(runner=lambda a, ar: {"ok": True}, triggers_path=p)
        a = m2.get("keep")
        assert a is not None
        assert a.fire_count == 1  # persisted count


def test_make_runner_goal():
    with tempfile.TemporaryDirectory() as tmp:
        gs = GoalStack(goals_path=Path(tmp) / "goals.json")
        runner = make_runner(goals=gs)
        res = runner("goal", {"intent": "build a thing"})
        assert res["ok"] is True
        assert len(gs.list_goals()) == 1


def test_make_runner_unknown_action():
    runner = make_runner()
    res = runner("bogus", {})
    assert res["ok"] is False


def test_bad_trigger_and_action():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mgr(tmp)
        try:
            m.add("a", "badtrigger", "goal", {})
            assert False
        except ValueError:
            pass
        try:
            m.add("b", "webhook", "badaction", {})
            assert False
        except ValueError:
            pass


def test_stats_and_fired_log():
    with tempfile.TemporaryDirectory() as tmp:
        m = _mgr(tmp, runner=lambda a, ar: {"ok": True})
        m.add("a", "webhook", "notify", {})
        m.add("b", "schedule", "goal", {"intent": "x"})
        m.fire("a")
        m.fire("a")
        st = m.stats()
        assert st["triggers"] == 2
        assert st["fired"] == 2
        assert len(m.fired_log()) == 2


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
