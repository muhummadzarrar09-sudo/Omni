"""
Tests for the Vision GUI Agent (Phase 16, #4).
Run: python -m pytest omni_v2/tests/test_gui_agent.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_gui_")))

from omni_v2.gui.gui_agent import GuiAgent, GuiAction, SAFE_ACTIONS
from omni_v2.history.action_journal import ActionJournal


def _agent(actions, journal=None, driver=None):
    acts = list(actions)
    def decide(desc):
        return acts.pop(0) if acts else GuiAction("done")
    return GuiAgent(capture=lambda: "img", vision=lambda i: "a screen",
                    decide=decide, driver=driver, journal=journal, max_steps=10)


def test_run_performs_actions_until_done():
    a = _agent([GuiAction("click", {"x": 10, "y": 20}), GuiAction("done")])
    res = a.run("click the button")
    assert res["count"] == 1
    assert res["steps"][0]["action"]["kind"] == "click"


def test_blocks_unsafe_action():
    a = _agent([GuiAction("rm_rf", {}), GuiAction("done")])
    res = a.run("danger")
    assert res["steps"][0]["blocked"] is True


def test_safe_driver_blocks_unknown():
    driver = GuiAgent._safe_driver
    assert driver(GuiAction("screenshot"))["ok"] is True
    assert driver(GuiAction("bad"))["blocked"] is True


def test_max_steps_bounded():
    a = _agent([GuiAction("click") for _ in range(50)])  # never done
    res = a.run("loop")
    assert res["count"] <= 10  # max_steps


def test_no_decider_halts():
    a = GuiAgent(capture=lambda: "img", vision=lambda i: "x", decide=None)
    res = a.run("x")
    assert res["ok"] is True


def test_journal_records_actions():
    with tempfile.TemporaryDirectory() as tmp:
        j = ActionJournal(path=Path(tmp) / "j.json")
        a = _agent([GuiAction("click", {"x": 1}), GuiAction("done")], journal=j)
        a.run("do it")
        assert j.stats()["records"] >= 1


def test_custom_driver_used():
    calls = []
    def driver(action):
        calls.append(action.kind)
        return {"ok": True}
    a = _agent([GuiAction("click"), GuiAction("done")], driver=driver)
    a.run("x")
    assert "click" in calls


def test_stats_and_history():
    a = _agent([GuiAction("click"), GuiAction("done")])
    a.run("x")
    assert len(a.history()) >= 1
    assert a.stats()["steps_done"] >= 1
    assert "screenshot" in a.stats()["safe_actions"]


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
