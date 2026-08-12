"""
Tests for Personal Context (Phase 14, #5) - local calendar + contacts
and KnowledgeBase citations (Phase 14, #6).
Run: python -m pytest omni_v2/tests/test_personal.py -q
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_personal_")))

from omni_v2.personal.calendar_contacts import CalendarParser, ContactStore
from omni_v2.away.knowledge_base import KnowledgeBase
from omni_v2.memory.hybrid_memory import HybridMemory


ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Team Standup
DTSTART:20260811T100000Z
LOCATION:Zoom
END:VEVENT
BEGIN:VEVENT
SUMMARY:Doctor
DTSTART:20990101T090000Z
END:VEVENT
END:VCALENDAR
"""

VCF = """BEGIN:VCARD
VERSION:3.0
FN:Zarrar
TEL:+923001234567
EMAIL:z@x.com
END:VCARD
BEGIN:VCARD
VERSION:3.0
FN:Ali
TEL:+923009998877
END:VCARD
"""


def test_parse_ics_events():
    events = CalendarParser._parse_ics(ICS)
    assert len(events) == 2
    summaries = [e.get("SUMMARY") for e in events]
    assert "Team Standup" in summaries


def test_upcoming_events():
    with tempfile.TemporaryDirectory() as tmp:
        cal = CalendarParser(calendar_dir=Path(tmp) / "cal")
        ics = Path(tmp) / "cal.ics"
        upcoming_start = (datetime.now() + timedelta(minutes=5)).strftime("%Y%m%dT%H%M%SZ")
        ics.write_text(ICS.replace("20260811T100000Z", upcoming_start), encoding="utf-8")
        cal.add_ics_file(ics)
        events = cal.events_today()
        assert len(events) >= 1


def test_import_vcf_contacts():
    with tempfile.TemporaryDirectory() as tmp:
        cs = ContactStore(contacts_file=Path(tmp) / "contacts.json")
        vcf = Path(tmp) / "c.vcf"
        vcf.write_text(VCF, encoding="utf-8")
        n = cs.import_vcf(vcf)
        assert n == 2
        assert cs.lookup("zarrar") is not None
        assert cs.lookup("zarrar")["phone"] == "+923001234567"


def test_contact_lookup_phone():
    with tempfile.TemporaryDirectory() as tmp:
        cs = ContactStore(contacts_file=Path(tmp) / "contacts.json")
        cs.add_contact("Mom", phone="+923001112233")
        c = cs.lookup("mom")
        assert c is not None
        assert c["phone"] == "+923001112233"


def test_contacts_persist():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "contacts.json"
        c1 = ContactStore(contacts_file=f)
        c1.add_contact("Bob", phone="123")
        c2 = ContactStore(contacts_file=f)
        assert c2.lookup("bob")["phone"] == "123"


# --- RAG citations (#6) ---------------------------------------------------
def test_query_with_citations():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        kb = KnowledgeBase(memory=mem)
        kb.add_text("Deploy with docker compose and nginx.", source="docs/deploy.md", title="deploy")
        kb.add_text("Auth uses JWT with a secret in env.", source="docs/auth.md", title="auth")
        res = kb.query_with_citations("how do i deploy")
        assert res["hit_count"] >= 1
        # citations carry the source
        assert any("deploy.md" in c["source"] for c in res["citations"])
        assert "source:" in res["context"]


def test_query_with_citations_empty():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        kb = KnowledgeBase(memory=mem)
        res = kb.query_with_citations("nothing here at all")
        assert res["hit_count"] == 0
        assert "no relevant knowledge" in res["context"]


def test_citations_include_snippet():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        kb = KnowledgeBase(memory=mem)
        kb.add_text("Postgres uses indexes for fast lookups.", source="db.md")
        res = kb.query_with_citations("postgres")
        assert res["citations"][0]["snippet"]
        assert res["citations"][0]["source"] == "db.md"


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
