"""
Tests for NL File Manager (Phase 15 #5) + Remote Control (#6).
Run: python -m pytest omni_v2/tests/test_nlfiles_remote.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_nlfiles_")))

from omni_v2.files.nl_files import NLFileManager, parse_intent
from omni_v2.history.action_journal import ActionJournal


def _setup(tmp):
    root = Path(tmp) / "home"
    (root / "Downloads").mkdir(parents=True)
    (root / "Documents").mkdir(parents=True)
    (root / "Downloads" / "a.pdf").write_bytes(b"pdf")
    (root / "Downloads" / "b.pdf").write_bytes(b"pdf")
    (root / "Downloads" / "c.txt").write_text("txt", encoding="utf-8")
    return root


def test_parse_intent_move_pdfs():
    p = parse_intent("move all PDFs from Downloads to Documents")
    assert p["op"] == "move"
    assert p["ext"] == ".pdf"
    assert "downloads" in p["src"]
    assert "documents" in p["dest"]


def test_parse_intent_delete():
    p = parse_intent("delete all .txt files")
    assert p["op"] == "delete"
    assert p["ext"] == ".txt"


def test_move_pdfs():
    with tempfile.TemporaryDirectory() as tmp:
        root = _setup(tmp)
        m = NLFileManager(allowed_root=root)
        res = m.execute("move all PDFs from Downloads to Documents")
        assert res["ok"] is True
        assert res["succeeded"] == 2
        assert (root / "Documents" / "a.pdf").exists()
        assert not (root / "Downloads" / "a.pdf").exists()


def test_copy_txt():
    with tempfile.TemporaryDirectory() as tmp:
        root = _setup(tmp)
        m = NLFileManager(allowed_root=root)
        res = m.execute("copy all .txt files from Downloads to Documents")
        assert res["succeeded"] == 1
        # copy leaves original
        assert (root / "Downloads" / "c.txt").exists()
        assert (root / "Documents" / "c.txt").exists()


def test_delete_txt_with_undo():
    with tempfile.TemporaryDirectory() as tmp:
        root = _setup(tmp)
        import omni_v2.history.action_journal as hjmod
        hjmod.UNDO_DIR = Path(tmp) / "undo"
        j = ActionJournal(path=Path(tmp) / "j.json", undo_dir=Path(tmp) / "undo")
        m = NLFileManager(allowed_root=root, journal=j)
        res = m.execute("delete all .txt files from Downloads")
        assert res["succeeded"] == 1
        assert not (root / "Downloads" / "c.txt").exists()
        # undo via journal
        undo_id = res["results"][0]["undo_id"]
        ures = j.undo(undo_id)
        assert ures["ok"] is True
        assert (root / "Downloads" / "c.txt").exists()


def test_blocked_outside_root():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "home"
        root.mkdir()
        m = NLFileManager(allowed_root=root)
        res = m.execute("delete all files from /etc")
        assert res["ok"] is False
        assert "outside" in res.get("error", "").lower() or "source not found" in res.get("error", "")


def test_safe_path_check():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "home"
        root.mkdir()
        m = NLFileManager(allowed_root=root)
        assert m._safe(root / "x.txt") is True
        assert m._safe(Path("/etc/passwd")) is False


def test_list():
    with tempfile.TemporaryDirectory() as tmp:
        root = _setup(tmp)
        m = NLFileManager(allowed_root=root)
        res = m.execute("list PDFs from Downloads")
        assert res["matched"] == 2


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
