"""
Tests for OMNI Mesh sync (Phase 16, #3).
Run: python -m pytest omni_v2/tests/test_mesh.py -q
"""
import sys
import os
import json
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_mesh_")))

from omni_v2.mesh.mesh_sync import MeshSync


def _state(tmp):
    d = Path(tmp) / "data"
    (d / "brain").mkdir(parents=True)
    return d, MeshSync(data_dir=d)


def test_export_import_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        d, m = _state(tmp)
        (d / "brain" / "goals.json").write_text(json.dumps({"g1": {"id": "g1", "updated_at": 100}}))
        state = m.export_state()
        assert "goals" in state["collections"]
        # import into a fresh dir
        d2 = Path(tmp) / "data2"
        m2 = MeshSync(data_dir=d2)
        res = m2.import_state(state)
        assert res["ok"] is True
        assert (d2 / "brain" / "goals.json").exists()


def test_export_empty():
    with tempfile.TemporaryDirectory() as tmp:
        d, m = _state(tmp)
        state = m.export_state()
        assert state["collections"] == {}
        assert "config" not in state


def test_import_does_not_overwrite_by_default_flag():
    with tempfile.TemporaryDirectory() as tmp:
        d, m = _state(tmp)
        (d / "brain" / "goals.json").write_text(json.dumps({"g": {"updated_at": 1}}))
        state = m.export_state()
        # import into same dir with overwrite=False keeps existing
        m2 = MeshSync(data_dir=d)
        res = m2.import_state(state, overwrite=False)
        assert (d / "brain" / "goals.json").exists()


def test_reconcile_merges_records_newest_wins():
    with tempfile.TemporaryDirectory() as tmp:
        d, m = _state(tmp)
        (d / "brain" / "goals.json").write_text(json.dumps({
            "g1": {"id": "g1", "updated_at": 100, "title": "local"},
        }))
        remote_state = {"collections": {"goals": {
            "g1": {"id": "g1", "updated_at": 200, "title": "remote"},
            "g2": {"id": "g2", "updated_at": 150, "title": "new"},
        }}}
        res = m.reconcile(remote_state)
        assert res["reconciled_collections"] >= 1
        merged = json.loads((d / "brain" / "goals.json").read_text())
        # g1 newest is remote (200)
        assert merged["g1"]["title"] == "remote"
        # g2 present
        assert "g2" in merged


def test_reconcile_preserves_local_when_newer():
    with tempfile.TemporaryDirectory() as tmp:
        d, m = _state(tmp)
        (d / "brain" / "goals.json").write_text(json.dumps({
            "g1": {"id": "g1", "updated_at": 300, "title": "local-newer"},
        }))
        remote_state = {"collections": {"goals": {
            "g1": {"id": "g1", "updated_at": 100, "title": "remote-older"},
        }}}
        m.reconcile(remote_state)
        merged = json.loads((d / "brain" / "goals.json").read_text())
        assert merged["g1"]["title"] == "local-newer"


def test_ts_key():
    assert MeshSync._ts_key({"updated_at": 42}) == 42.0
    assert MeshSync._ts_key({"created_at": 7}) == 7.0
    assert MeshSync._ts_key({"foo": 1}) == 0.0


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        _, m = _state(tmp)
        st = m.stats()
        assert "goals" in st["collections_supported"]


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
