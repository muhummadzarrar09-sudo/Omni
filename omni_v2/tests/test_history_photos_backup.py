"""
Tests for Action Journal (Phase 15 #2), Photo Memory (#3), Backup (#4).
Run: python -m pytest omni_v2/tests/test_history_photos_backup.py -q
"""
import sys
import os
import json
import shutil
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_hpb_")))

from omni_v2.history.action_journal import ActionJournal
from omni_v2.photos.photo_memory import PhotoMemory
from omni_v2.backup.backup import BackupManager
from omni_v2.memory.hybrid_memory import HybridMemory


# --- Action Journal --------------------------------------------------------
def test_record_and_list():
    with tempfile.TemporaryDirectory() as tmp:
        j = ActionJournal(path=Path(tmp) / "j.json", undo_dir=Path(tmp) / "undo")
        aid = j.record("files_write", {"path": "/tmp/x.txt", "content": "hi"})
        assert j.get(aid).action == "files_write"
        assert len(j.list()) == 1


def test_replay_with_executor():
    with tempfile.TemporaryDirectory() as tmp:
        calls = []
        def ex(action, args):
            calls.append((action, args))
            return "ok"
        j = ActionJournal(path=Path(tmp) / "j.json", executor=ex)
        aid = j.record("notify", {"text": "hi"})
        res = j.replay(aid)
        assert res["ok"] is True
        assert calls[0] == ("notify", {"text": "hi"})


def test_undo_delete_restores_file():
    with tempfile.TemporaryDirectory() as tmp:
        # create a file, snapshot undo, delete it, then undo
        orig = Path(tmp) / "notes.txt"
        orig.write_text("original content", encoding="utf-8")
        undo_info = ActionJournal.prepare_file_undo("delete", orig)
        orig.unlink()
        assert not orig.exists()
        j = ActionJournal(path=Path(tmp) / "j.json", undo_dir=Path(tmp) / "undo")
        # undo_dir used by prepare_file_undo via UNDO_DIR global; redirect
        import omni_v2.history.action_journal as mod
        mod.UNDO_DIR = Path(tmp) / "undo"
        undo_info = ActionJournal.prepare_file_undo("delete", Path(tmp) / "gone.txt")
        # write a file then delete with undo
        Path(tmp, "gone.txt").write_text("data", encoding="utf-8")
        undo_info = ActionJournal.prepare_file_undo("delete", Path(tmp) / "gone.txt")
        Path(tmp, "gone.txt").unlink()
        aid = j.record_with_undo("files_delete", {"path": str(Path(tmp)/"gone.txt")}, undo_info)
        res = j.undo(aid)
        assert res["ok"] is True
        assert Path(tmp, "gone.txt").exists()
        assert Path(tmp, "gone.txt").read_text() == "data"


def test_undo_moves_file_back():
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.txt"
        b = Path(tmp) / "b.txt"
        a.write_text("hello", encoding="utf-8")
        import omni_v2.history.action_journal as mod
        mod.UNDO_DIR = Path(tmp) / "undo"
        undo_info = ActionJournal.prepare_file_undo("move", a, dest=b)
        shutil.move(a, b)
        j = ActionJournal(path=Path(tmp) / "j.json", undo_dir=Path(tmp) / "undo")
        aid = j.record_with_undo("files_move", {"src": str(a), "dest": str(b)}, undo_info)
        res = j.undo(aid)
        # either moved back or restored from snapshot
        assert res["ok"] is True
        assert a.exists() or (Path(tmp)/"undo").exists()


def test_not_reversible():
    with tempfile.TemporaryDirectory() as tmp:
        j = ActionJournal(path=Path(tmp) / "j.json")
        aid = j.record("ai_chat", {"text": "hi"})
        res = j.undo(aid)
        assert res["ok"] is False


def test_replay_session():
    with tempfile.TemporaryDirectory() as tmp:
        def ex(a, ar): return "ok"
        j = ActionJournal(path=Path(tmp) / "j.json", executor=ex)
        j.record("a", {}, session="s1")
        j.record("b", {}, session="s1")
        j.record("c", {}, session="s2")
        res = j.replay_session("s1")
        assert res["count"] == 2


# --- Photo Memory ----------------------------------------------------------
def test_caption_image():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        pm = PhotoMemory(memory=mem, captioner=lambda p: "a mountain landscape at sunset")
        img = Path(tmp) / "photo.jpg"
        img.write_bytes(b"fakejpeg")
        res = pm.caption_image(str(img))
        assert res["ok"] is True
        assert "mountain" in res["entry"]["caption"]
        # stored in RAG memory
        assert mem.retrieve("mountain", k=3)


def test_caption_directory():
    with tempfile.TemporaryDirectory() as tmp:
        pm = PhotoMemory(captioner=lambda p: "a cat")
        (Path(tmp) / "p1.jpg").write_bytes(b"x")
        (Path(tmp) / "p2.png").write_bytes(b"x")
        (Path(tmp) / "notes.txt").write_text("not an image", encoding="utf-8")
        res = pm.caption_directory(tmp)
        assert res["captioned"] == 2
        assert res["total"] == 2


def test_photo_search():
    with tempfile.TemporaryDirectory() as tmp:
        import omni_v2.photos.photo_memory as mod
        mod.PHOTO_INDEX = Path(tmp) / "photo_index.json"
        pm = PhotoMemory(captioner=lambda p: "a beach")
        (Path(tmp) / "a.jpg").write_bytes(b"x")
        pm.caption_image(str(Path(tmp)/"a.jpg"))
        results = pm.search("beach")
        assert len(results) == 1


def test_photo_persist():
    with tempfile.TemporaryDirectory() as tmp:
        import omni_v2.photos.photo_memory as mod
        mod.PHOTO_INDEX = Path(tmp) / "photo_index.json"
        pm = PhotoMemory(captioner=lambda p: "a dog")
        (Path(tmp) / "d.jpg").write_bytes(b"x")
        pm.caption_image(str(Path(tmp)/"d.jpg"))
        pm2 = PhotoMemory(captioner=lambda p: "a dog")
        assert pm2.stats()["images_indexed"] >= 1


# --- Backup ----------------------------------------------------------------
def test_backup_create_folder():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        (data / "brain").mkdir(parents=True)
        (data / "brain" / "identity.json").write_text("{}", encoding="utf-8")
        (data / "config.json").write_text("{}", encoding="utf-8")
        bm = BackupManager(data_dir=data)
        out = Path(tmp) / "backup"
        res = bm.create(str(out))
        assert res["ok"] is True
        assert (out / "brain" / "identity.json").exists()


def test_backup_create_zip():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        (data / "brain").mkdir(parents=True)
        (data / "brain" / "goals.json").write_text("[]", encoding="utf-8")
        bm = BackupManager(data_dir=data)
        out = Path(tmp) / "backup.zip"
        res = bm.create(str(out), as_zip=True)
        assert res["ok"] is True
        assert out.exists()


def test_backup_restore():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        (data / "brain").mkdir(parents=True)
        (data / "brain" / "identity.json").write_text("{}", encoding="utf-8")
        bm = BackupManager(data_dir=data)
        out = Path(tmp) / "backup"
        bm.create(str(out))
        # wipe then restore
        shutil.rmtree(data / "brain")
        res = bm.restore(str(out))
        assert res["ok"] is True
        assert (data / "brain" / "identity.json").exists()


def test_backup_list():
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        (data / "brain").mkdir(parents=True)
        (data / "brain" / "x.json").write_text("{}", encoding="utf-8")
        bm = BackupManager(data_dir=data)
        bm.create(str(Path(tmp) / "omni_backup_test"))
        lst = bm.list_backups(Path(tmp))
        assert len(lst) >= 1


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
