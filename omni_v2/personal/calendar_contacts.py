"""
OMNI PERSONAL CONTEXT (Phase 14, #5) — local calendar + contacts.

Makes OMNI aware of YOUR actual schedule and people, so the morning briefing and
proactive guardian reference real data instead of placeholders.

Calendar:
  - Parse local .ics files (RFC 5545) with a lightweight parser (no external dep;
    falls back gracefully if the `icalendar` lib is available).
  - List today's / upcoming events, events at a given time.

Contacts:
  - Parse simple contact files (.vcf) or a JSON contacts store.
  - Look up by name; resolve "call/email/text <person>" to a number/email.

All local, headless-testable with fixture files.
"""
from __future__ import annotations
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Personal")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

PERSONAL_DIR = DATA_DIR / "personal"
CAL_DIR = PERSONAL_DIR / "calendar"
CONTACTS_FILE = PERSONAL_DIR / "contacts.json"


class CalendarParser:
    """Parse .ics files into events. Lightweight + dependency-free."""

    def __init__(self, calendar_dir: Optional[Path] = None):
        self.calendar_dir = Path(calendar_dir) if calendar_dir else CAL_DIR
        self.calendar_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _parse_ics(text: str) -> List[Dict[str, Any]]:
        events = []
        current = {}
        in_event = False
        for raw in text.splitlines():
            line = raw.rstrip("\r")
            if not line:
                continue
            # unfold continuation lines
            if line.startswith(" "):
                if current:
                    last = current.get("_last", "")
                    current[last] = current.get(last, "") + line[1:]
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            if key == "BEGIN" and value == "VEVENT":
                current, in_event = {}, True
                continue
            if key == "END" and value == "VEVENT":
                if in_event:
                    events.append(current)
                    current, in_event = {}, False
                continue
            if in_event:
                current[key] = value
                current["_last"] = key
        return events

    @staticmethod
    def _parse_dt(value: str) -> Optional[datetime]:
        # supports 20260811T100000Z and date-only
        m = re.match(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})", value or "")
        if m:
            return datetime(*[int(x) for x in m.groups()])
        m = re.match(r"(\d{4})(\d{2})(\d{2})", value or "")
        if m:
            return datetime(*[int(x) for x in m.groups()])
        return None

    def add_ics_file(self, path: Path) -> int:
        """Ingest an .ics file. Returns event count."""
        if not path.exists():
            raise FileNotFoundError(path)
        events = self._parse_ics(path.read_text(encoding="utf-8", errors="ignore"))
        # persist parsed events to a JSON mirror for quick lookup
        mirror = self.calendar_dir / (path.stem + ".json")
        mirror.write_text(json.dumps(events, indent=2), encoding="utf-8")
        logger.info(f"calendar: parsed {len(events)} event(s) from {path.name}")
        return len(events)

    def all_events(self) -> List[Dict[str, Any]]:
        events = []
        for f in self.calendar_dir.glob("*.json"):
            try:
                events.extend(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
        return events

    def upcoming(self, hours: int = 24, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        now = now or datetime.now()
        out = []
        for e in self.all_events():
            dt = self._parse_dt(e.get("DTSTART", ""))
            if dt and now <= dt <= now + timedelta(hours=hours):
                out.append({
                    "summary": e.get("SUMMARY", e.get("SUMMARY_", "(no title)")),
                    "start": dt.isoformat(),
                    "location": e.get("LOCATION", ""),
                    "description": e.get("DESCRIPTION", "")[:120],
                })
        return sorted(out, key=lambda x: x["start"])

    def events_today(self) -> List[Dict[str, Any]]:
        return self.upcoming(hours=24)

    def stats(self) -> Dict[str, Any]:
        return {"events_total": len(self.all_events()),
                "files": len(list(self.calendar_dir.glob("*.json")))}


class ContactStore:
    """Parse + query local contacts."""

    def __init__(self, contacts_file: Optional[Path] = None):
        self.contacts_file = Path(contacts_file) if contacts_file else CONTACTS_FILE
        self.contacts_file.parent.mkdir(parents=True, exist_ok=True)
        self._contacts: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.contacts_file.exists():
                self._contacts = json.loads(self.contacts_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"contacts load failed: {e}")

    def _save(self) -> None:
        try:
            self.contacts_file.write_text(json.dumps(self._contacts, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"contacts save failed: {e}")

    def import_vcf(self, path: Path) -> int:
        """Parse a .vcf file and add contacts."""
        if not path.exists():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        contacts = []
        current = {}
        for line in text.splitlines():
            line = line.rstrip("\r")
            if line.upper() == "BEGIN:VCARD":
                current = {}
            elif line.upper() == "END:VCARD":
                if current.get("name"):
                    contacts.append(current)
                current = {}
            else:
                key, _, val = line.partition(":")
                key = key.split(";")[0].upper()
                if key == "FN":
                    current["name"] = val
                elif key == "TEL":
                    current["phone"] = val.split(";")[0]
                elif key == "EMAIL":
                    current["email"] = val
                elif key == "N":
                    parts = val.split(";")
                    if not current.get("name"):
                        current["name"] = " ".join(x for x in reversed(parts) if x)
        added = 0
        for c in contacts:
            if c.get("name"):
                self._contacts.append(c)
                added += 1
        self._save()
        logger.info(f"contacts: imported {added} from {path.name}")
        return added

    def add_contact(self, name: str, phone: str = "", email: str = "") -> Dict[str, Any]:
        c = {"name": name, "phone": phone, "email": email}
        self._contacts.append(c)
        self._save()
        return c

    def lookup(self, name: str) -> Optional[Dict[str, Any]]:
        name_l = name.lower()
        for c in self._contacts:
            if name_l in c.get("name", "").lower():
                return c
        return None

    def all(self) -> List[Dict[str, Any]]:
        return self._contacts

    def stats(self) -> Dict[str, Any]:
        return {"contacts": len(self._contacts), "file": str(self.contacts_file)}


def get_calendar(**kwargs) -> CalendarParser:
    return CalendarParser(**kwargs)


def get_contacts(**kwargs) -> ContactStore:
    return ContactStore(**kwargs)
