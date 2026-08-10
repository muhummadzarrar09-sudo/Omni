"""
Tests for the Messenger providers + router (Away Mode).
Run: python -m pytest omni_v2/tests/test_messenger.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_kb_")))

from omni_v2.away.messenger import (
    FileMessenger, WhatsAppMessenger, TelegramMessenger, MessengerRouter,
    load_away_config, save_away_config, normalize_phone, whatsapp_setup_guide,
)


def test_file_messenger_sends():
    with tempfile.TemporaryDirectory() as tmp:
        m = FileMessenger(outbox=Path(tmp) / "out", inbox=Path(tmp) / "in")
        res = m.send_text("hello")
        assert res.ok is True
        assert res.text == "hello"
        assert "out" in res.detail
        # file written
        files = list((Path(tmp) / "out").glob("*.json"))
        assert len(files) == 1


def test_file_messenger_report():
    with tempfile.TemporaryDirectory() as tmp:
        m = FileMessenger(outbox=Path(tmp) / "out", inbox=Path(tmp) / "in")
        res = m.send_report("summary", path="/tmp/x.md")
        assert res.ok is True
        assert "/tmp/x.md" in res.text


def test_whatsapp_unavailable_degrades():
    m = WhatsAppMessenger(phone_number="")
    assert m.available is False
    res = m.send_text("hi")
    assert res.ok is False


def test_normalize_pakistani_phone():
    assert normalize_phone("03001234567") == "+923001234567"   # local 0-prefixed
    assert normalize_phone("+923001234567") == "+923001234567"
    assert normalize_phone("923001234567") == "+923001234567"
    assert normalize_phone("03001234567") == "+923001234567"


def test_whatsapp_check_ready_no_number():
    m = WhatsAppMessenger(phone_number="")
    chk = m.check_ready()
    assert chk["phone_number_set"] is False
    # message explains either the missing package or the missing number
    assert chk["message"] != ""


def test_whatsapp_setup_guide_mentions_pakistan():
    guide = whatsapp_setup_guide()
    assert "Pakistan" in guide
    assert "web.whatsapp.com" in guide


def test_telegram_unavailable_degrades():
    m = TelegramMessenger(token="", chat_id="")
    assert m.available is False
    res = m.send_text("hi")
    assert res.ok is False


def test_telegram_poll_empty_when_unavailable():
    m = TelegramMessenger()
    assert m.poll_commands() == []


def test_router_defaults_to_file():
    router = MessengerRouter(config={"messenger": {"provider": "file"}})
    assert router.channel == "file"


def test_router_falls_back_when_unconfigured():
    # configured telegram but no token -> file fallback
    router = MessengerRouter(config={"messenger": {"provider": "telegram", "token": "", "chat_id": ""}})
    assert router.channel == "file"


def test_config_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        # patch DATA_DIR for this test
        import omni_v2.away.messenger as msg_mod
        orig = msg_mod.DATA_DIR
        msg_mod.DATA_DIR = Path(tmp)
        try:
            cfg = {"away": {"auto_start": True}, "messenger": {"provider": "whatsapp", "phone_number": "123"}}
            save_away_config(cfg)
            loaded = load_away_config()
            assert loaded["away"]["auto_start"] is True
            assert loaded["messenger"]["provider"] == "whatsapp"
        finally:
            msg_mod.DATA_DIR = orig


def test_load_away_config_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        import omni_v2.away.messenger as msg_mod
        orig = msg_mod.DATA_DIR
        msg_mod.DATA_DIR = Path(tmp)
        try:
            cfg = load_away_config()
            assert cfg["away"]["auto_start"] is False
            assert cfg["messenger"]["provider"] == "file"
        finally:
            msg_mod.DATA_DIR = orig


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
