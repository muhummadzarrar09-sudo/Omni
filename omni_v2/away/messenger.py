"""
OMNI MESSENGER - local bridge for sending reports / receiving remote commands.

One abstraction, three providers:
  * FileMessenger      - ALWAYS works (writes to data/messenger/). No network.
  * WhatsAppMessenger  - local WhatsApp Web via pywhatkit (good in Pakistan,
                         no Telegram needed). Outbound reports + alerts.
  * TelegramMessenger  - python-telegram-bot. Outbound reports AND inbound
                         remote commands (requires Telegram + a proxy if you
                         are in a region where Telegram is blocked).

Design: a `MessengerRouter` picks the active provider from config
(data/config.json -> "away.messenger"). If the configured provider isn't
installed/configured, we gracefully fall back to FileMessenger so the away
pipeline never crashes and the report is still saved locally.

Phone push format is short (reports are saved fully to disk; only a summary
plus the local path is pushed).
"""
from __future__ import annotations
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Messenger")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

MESSENGER_DIR = DATA_DIR / "messenger"
OUTBOX_DIR = MESSENGER_DIR / "outbox"
INBOX_DIR = MESSENGER_DIR / "inbox"


@dataclass
class OutboundMessage:
    text: str
    channel: str = "file"
    sent_at: float = time.time()
    ok: bool = False
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text, "channel": self.channel,
            "sent_at": self.sent_at, "ok": self.ok, "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# Provider base
# ---------------------------------------------------------------------------
class BaseMessenger:
    name = "base"

    def send_text(self, text: str) -> OutboundMessage:
        raise NotImplementedError

    def send_report(self, summary: str, path: str = "") -> OutboundMessage:
        msg = summary
        if path:
            msg += f"\n📄 Saved locally: {path}"
        return self.send_text(msg)

    def poll_commands(self) -> List[Dict[str, str]]:
        """Return incoming remote commands as [{sender, text}]. Default: none."""
        return []


# ---------------------------------------------------------------------------
# File provider (always works)
# ---------------------------------------------------------------------------
class FileMessenger(BaseMessenger):
    name = "file"

    def __init__(self, outbox: Optional[Path] = None, inbox: Optional[Path] = None):
        self.outbox = Path(outbox) if outbox else OUTBOX_DIR
        self.inbox = Path(inbox) if inbox else INBOX_DIR
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)

    def send_text(self, text: str) -> OutboundMessage:
        stamp = int(time.time() * 1000)
        path = self.outbox / f"{stamp}.json"
        try:
            path.write_text(json.dumps(OutboundMessage(text=text, channel="file", ok=True, detail=str(path)).to_dict()), encoding="utf-8")
            return OutboundMessage(text=text, channel="file", ok=True, detail=str(path))
        except Exception as e:
            return OutboundMessage(text=text, channel="file", ok=False, detail=str(e))


# ---------------------------------------------------------------------------
# WhatsApp provider (local WhatsApp Web via pywhatkit) — works in Pakistan,
# WhatsApp is NOT blocked here (unlike Telegram), so no proxy is needed.
# ---------------------------------------------------------------------------
# Standardize a Pakistani phone number to international format (+92...).
def normalize_phone(number: str) -> str:
    num = (number or "").strip()
    num = "".join(ch for ch in num if ch.isdigit() or ch == "+")
    if num.startswith("+"):
        num = num[1:]
    if num.startswith("00"):
        num = num[2:]
    if num.startswith("0") and len(num) == 11:  # 03xxxxxxxxx
        num = "92" + num[1:]
    if not num.startswith("92"):
        num = "92" + num  # default to Pakistan country code
    return "+" + num


def whatsapp_setup_guide() -> str:
    """Step-by-step WhatsApp Web setup, tuned for Pakistan (no proxy needed)."""
    return (
        "WHATSAPP WEB SETUP FOR OMNI (works in Pakistan — WhatsApp is not blocked)\n"
        "=====================================================================\n"
        "1. Install pywhatkit:\n"
        "      pip install pywhatkit\n"
        "2. Open WhatsApp Web in your DEFAULT browser and log in ONCE:\n"
        "      - Go to https://web.whatsapp.com\n"
        "      - On your phone: WhatsApp -> Settings (⋮) -> Linked devices\n"
        "        -> Link a device -> scan the QR code on the laptop.\n"
        "      - Leave this tab OPEN / keep the browser signed in.\n"
        "   (pywhatkit drives this same signed-in browser, so it must stay logged in.)\n"
        "3. IMPORTANT: the recipient's number must be saved as a CONTACT on the\n"
        "   phone number that owns this WhatsApp account, and the recipient must\n"
        "   also have your number saved (WhatsApp needs the chat to resolve).\n"
        "4. Configure OMNI with your number (use +92... for Pakistan):\n"
        "      omni messenger whatsapp-set <+923001234567>\n"
        "      omni messenger test\n"
        "5. Optional — make it reliable:\n"
        "      - Keep your laptop awake while OMNI works (disable sleep/screen-off).\n"
        "      - pywhatkit opens a fresh WhatsApp Web tab per message; if you see\n"
        "        an 'unexpected QR' screen, re-link the device once and retry.\n"
    )


class WhatsAppMessenger(BaseMessenger):
    name = "whatsapp"

    def __init__(self, phone_number: str = "", hours: int = 12, minutes: int = 0,
                 close_tab: bool = True):
        self.phone_number = normalize_phone(phone_number) if phone_number else ""
        self.hours = hours
        self.minutes = minutes
        self.close_tab = close_tab
        self._pywhatkit = None

    @property
    def available(self) -> bool:
        try:
            import pywhatkit  # noqa: PLC0415
            self._pywhatkit = pywhatkit
            return bool(self.phone_number)
        except Exception:
            return False

    def check_ready(self) -> Dict[str, Any]:
        """Return a readiness checklist for diagnostics / the setup UI."""
        checks = {
            "pywhatkit_installed": False,
            "phone_number_set": bool(self.phone_number),
            "phone_number": self.phone_number or "(not set)",
            "message": "",
        }
        try:
            import pywhatkit  # noqa: PLC0415
            checks["pywhatkit_installed"] = True
        except Exception:
            checks["message"] = "pywhatkit is not installed. Run: pip install pywhatkit"
            return checks
        if not self.phone_number:
            checks["message"] = "No phone number set. Configure with +92... (see omni messenger setup-whatsapp)"
        else:
            checks["message"] = "Prerequisites met. Run 'omni messenger test' to verify."
        return checks

    def send_text(self, text: str) -> OutboundMessage:
        if not self.available:
            return OutboundMessage(text=text, channel="whatsapp", ok=False,
                                   detail="pywhatkit missing or no phone number configured")
        try:
            # sendwhatmsg_instantly opens WhatsApp Web in the default browser and sends.
            self._pywhatkit.sendwhatmsg_instantly(
                self.phone_number, text,
                wait_time=20,  # seconds to let WhatsApp Web load before typing
                tab_close=self.close_tab,
                close_time=5,
            )
            return OutboundMessage(text=text, channel="whatsapp", ok=True,
                                   detail=f"queued to WhatsApp Web {self.phone_number}")
        except Exception as e:
            logger.warning(f"WhatsApp send failed: {e}")
            return OutboundMessage(text=text, channel="whatsapp", ok=False, detail=str(e))


# ---------------------------------------------------------------------------
# Telegram provider (outbound + inbound remote commands)
# ---------------------------------------------------------------------------
class TelegramMessenger(BaseMessenger):
    name = "telegram"

    def __init__(self, token: str = "", chat_id: str = "", poll_interval: float = 5.0):
        self.token = token
        self.chat_id = chat_id
        self.poll_interval = poll_interval
        self._last_update_id = 0
        self._bot = None

    @property
    def available(self) -> bool:
        if not (self.token and self.chat_id):
            return False
        try:
            import telegram  # noqa: F401
            return True
        except Exception:
            return False

    def _get_bot(self):
        if self._bot is None and self.available:
            from telegram import Bot
            self._bot = Bot(token=self.token)
        return self._bot

    def send_text(self, text: str) -> OutboundMessage:
        bot = self._get_bot()
        if bot is None:
            return OutboundMessage(text=text, channel="telegram", ok=False,
                                   detail="telegram not configured/installed")
        try:
            bot.send_message(chat_id=self.chat_id, text=text)
            return OutboundMessage(text=text, channel="telegram", ok=True, detail="sent")
        except Exception as e:
            return OutboundMessage(text=text, channel="telegram", ok=False, detail=str(e))

    def poll_commands(self) -> List[Dict[str, str]]:
        """Poll the bot for new messages (inbound remote commands)."""
        bot = self._get_bot()
        if bot is None:
            return []
        try:
            updates = bot.get_updates(offset=self._last_update_id, timeout=1)
            commands = []
            for u in updates:
                self._last_update_id = u.update_id + 1
                msg = getattr(u, "message", None)
                if msg is None:
                    continue
                text = (getattr(msg, "text", "") or "").strip()
                if text:
                    sender = (getattr(msg.from_user, "username", None) or
                              str(getattr(msg.from_user, "id", "")))
                    commands.append({"sender": sender, "text": text})
            return commands
        except Exception as e:
            logger.warning(f"Telegram poll failed: {e}")
            return []


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
class MessengerRouter:
    """Chooses the active provider from config, with graceful fallback."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_away_config()
        self.provider = self._build()

    def _build(self) -> BaseMessenger:
        messenger_cfg = self.config.get("messenger", {})
        kind = messenger_cfg.get("provider", "file")
        if kind == "whatsapp":
            m = WhatsAppMessenger(
                phone_number=messenger_cfg.get("phone_number", ""),
            )
            if m.available:
                return m
            logger.warning("WhatsApp provider configured but not ready -> file fallback")
        elif kind == "telegram":
            m = TelegramMessenger(
                token=messenger_cfg.get("token", ""),
                chat_id=str(messenger_cfg.get("chat_id", "")),
            )
            if m.available:
                return m
            logger.warning("Telegram provider configured but not ready -> file fallback")
        return FileMessenger()

    def send_text(self, text: str) -> OutboundMessage:
        return self.provider.send_text(text)

    def send_report(self, summary: str, path: str = "") -> OutboundMessage:
        return self.provider.send_report(summary, path=path)

    def poll_commands(self) -> List[Dict[str, str]]:
        return self.provider.poll_commands()

    @property
    def channel(self) -> str:
        return self.provider.name


def load_away_config() -> Dict[str, Any]:
    """Load the away-mode + messenger config from data/config.json."""
    config_path = DATA_DIR / "config.json"
    default = {
        "messenger": {"provider": "file", "phone_number": "", "token": "", "chat_id": ""},
        "away": {
            "auto_start": False,
            "research_max_queries": 4,
            "report_on_complete": True,
            "send_digests": False,
            "digest_interval_minutes": 60,
        },
    }
    try:
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
            away = data.get("away", {})
            default["away"].update(away)
            default["messenger"].update(data.get("messenger", {}))
    except Exception as e:
        logger.warning(f"load_away_config failed: {e}")
    return default


def save_away_config(config: Dict[str, Any]) -> None:
    """Persist away-mode + messenger config into data/config.json."""
    config_path = DATA_DIR / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = {}
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
        data["away"] = config.get("away", {})
        data["messenger"] = config.get("messenger", {})
        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Saved away config to {config_path}")
    except Exception as e:
        logger.warning(f"save_away_config failed: {e}")


def get_messenger(config: Optional[Dict[str, Any]] = None) -> BaseMessenger:
    return MessengerRouter(config=config).provider
