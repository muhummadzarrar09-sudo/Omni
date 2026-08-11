"""
Tests for the Recurring Scheduler (Phase 15, #1).
Run: python -m pytest omni_v2/tests/test_recurring.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_recur_")))

from omni_v2.schedule.recurring import RecurringScheduler, make_scheduler_runner


def _sched(tmp, runner=None):
    return RecurringScheduler(runner=runner or (lambda a, ar: {"ok": True}),
                              jobs_path=Path(tmp) / "recurring.json")


def test_add_cron():
    with tempfile.TemporaryDirectory() as tmp:
        s = _sched(tmp)
        j = s.add_cron("briefing", "0 8 * * *", "briefing")
        assert s.get("briefing").schedule_type == "cron"
        assert j.action == "briefing"


def test_add_interval():
    with tempfile.TemporaryDirectory() as tmp:
        s = _sched(tmp)
        s.add_interval("guardian", 3600, "guardian")
        assert s.get("guardian").schedule_value == "3600"


def test_fire_runs_runner():
    with tempfile.TemporaryDirectory() as tmp:
        calls = []
        def runner(action, args):
            calls.append(action)
            return {"ok": True}
        s = _sched(tmp, runner=runner)
        s.add_cron("briefing", "0 8 * * *", "briefing")
        res = s.fire("briefing")
        assert res["ok"] is True
        assert calls == ["briefing"]
        assert s.get("briefing").run_count == 1


def test_fire_disabled():
    with tempfile.TemporaryDirectory() as tmp:
        s = _sched(tmp)
        s.add_cron("x", "0 8 * * *", "notify")
        s.get("x").enabled = False
        s._save()
        assert s.fire("x")["ok"] is False


def test_persists():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "recurring.json"
        s1 = RecurringScheduler(runner=lambda a, ar: {"ok": True}, jobs_path=p)
        s1.add_cron("briefing", "0 8 * * *", "briefing")
        s1.fire("briefing")
        s2 = RecurringScheduler(runner=lambda a, ar: {"ok": True}, jobs_path=p)
        assert s2.get("briefing").run_count == 1


def test_remove_and_list():
    with tempfile.TemporaryDirectory() as tmp:
        s = _sched(tmp)
        s.add_cron("a", "0 8 * * *", "briefing")
        s.add_interval("b", 60, "guardian")
        assert len(s.list()) == 2
        assert s.remove("a") is True
        assert len(s.list()) == 1


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        s = _sched(tmp)
        s.add_cron("a", "0 8 * * *", "briefing")
        s.add_interval("b", 60, "guardian")
        st = s.stats()
        assert st["jobs"] == 2
        assert st["by_action"]["briefing"] == 1


def test_make_runner_notify():
    """make_scheduler_runner uses the DesktopController for real actions."""
    from omni_v2.schedule.recurring import make_scheduler_runner
    runner = make_scheduler_runner()
    # notify should route through messenger (file fallback -> ok)
    res = runner("notify", {"text": "test"})
    assert res["ok"] is True


def test_make_runner_unknown():
    from omni_v2.schedule.recurring import make_scheduler_runner
    runner = make_scheduler_runner()
    res = runner("bogus", {})
    assert res["ok"] is False


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
