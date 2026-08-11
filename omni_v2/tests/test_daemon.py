"""
Tests for the OMNI Daemon + AutoStart (Phase 14, #1).
Run: python -m pytest omni_v2/tests/test_daemon.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_daemon_")))

from omni_v2.daemon.daemon import (
    AutoStartManager, DaemonController, PlatformBackend,
    LinuxDesktopBackend,
)


class FakeBackend(PlatformBackend):
    name = "fake"
    def __init__(self):
        self.installed = False
        self.last_cmd = None
    def install(self, label, command):
        self.installed = True
        self.last_cmd = command
        return True
    def uninstall(self, label):
        self.installed = False
        return True
    def is_installed(self, label):
        return self.installed


def test_autostart_enable_disable():
    b = FakeBackend()
    asm = AutoStartManager(backend=b, label="omni")
    res = asm.enable(command="/usr/bin/omni")
    assert res["ok"] is True
    assert b.installed is True
    assert b.last_cmd == "/usr/bin/omni"
    assert asm.status()["installed"] is True
    asm.disable()
    assert asm.status()["installed"] is False


def test_linux_desktop_backend_writes_file():
    with tempfile.TemporaryDirectory() as tmp:
        class TmpDesktop(LinuxDesktopBackend):
            def _auto_dir(self):
                return Path(tmp)
        b = TmpDesktop()
        assert b.install("omni", "/bin/true") is True
        assert b.is_installed("omni") is True
        assert (Path(tmp) / "omni.desktop").exists()
        assert b.uninstall("omni") is True
        assert not (Path(tmp) / "omni.desktop").exists()


def test_daemon_start_stop():
    calls = []
    def svc():
        calls.append("started")
        return "handle"
    d = DaemonController(services={"guardian": svc})
    res = d.start()
    assert res["started"] == ["guardian"]
    assert d.running is True
    assert calls == ["started"]
    d.stop()
    assert d.running is False


def test_daemon_service_error_not_fatal():
    def bad():
        raise RuntimeError("boom")
    def good():
        return "ok"
    d = DaemonController(services={"bad": bad, "good": good})
    res = d.start()
    assert res["started"] == ["good"]  # bad skipped, good started
    assert d.running is True


def test_daemon_idempotent_start():
    d = DaemonController(services={"x": lambda: "h"})
    d.start()
    res = d.start()
    assert res["detail"] == "already running"


def test_daemon_stats():
    d = DaemonController(services={"a": lambda: "h", "b": lambda: "h"})
    d.start()
    st = d.stats()
    assert st["running"] is True
    assert len(st["services"]) == 2


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
