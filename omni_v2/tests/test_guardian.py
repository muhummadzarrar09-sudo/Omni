"""
Tests for the Proactive Guardian (Phase 10) - headless with fake checkers.
Run: python -m pytest omni_v2/tests/test_guardian.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_guard_")))

from omni_v2.guardian.guardian import Guardian


def _obs(title="notice", sev=0, kind="generic"):
    return {"kind": kind, "title": title, "body": "body", "severity": sev}


def test_run_once_routes_observations():
    obs = [_obs("A"), _obs("B")]
    seen = []
    g = Guardian(checkers=[lambda: obs], on_observation=lambda o: seen.append(o))
    res = g.run_once()
    assert len(res) == 2
    assert len(seen) == 2


def test_notify_only_anomalies():
    sent = []
    obs = [_obs("low", sev=1), _obs("high", sev=2)]
    g = Guardian(checkers=[lambda: obs], notify_fn=lambda t: sent.append(t),
                 anomaly_threshold=2)
    g.run_once()
    assert len(sent) == 1
    assert "high" in sent[0]


def test_recent_and_anomalies():
    obs = [_obs("normal", sev=0), _obs("warn", sev=1), _obs("crit", sev=2)]
    g = Guardian(checkers=[lambda: obs])
    g.run_once()
    assert len(g.recent()) == 3
    assert len(g.anomalies()) == 2  # sev>=1


def test_start_requires_checkers():
    g = Guardian(checkers=[])
    assert g.start() is False


def test_stats():
    g = Guardian(checkers=[lambda: [_obs("x")]])
    g.run_once()
    st = g.stats()
    assert st["checkers"] == 1
    assert st["observations"] == 1
    assert st["last_run"] is not None


def test_format():
    txt = Guardian._format({"title": "Low battery", "body": "Battery at 10%", "severity": 2})
    assert "Low battery" in txt


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
