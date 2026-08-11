"""
Tests for the Research Agent (Away Mode).
Run: python -m pytest omni_v2/tests/test_research.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_kb_")))

from omni_v2.away.research import ResearchAgent, ResearchFinding, ResearchReport
from omni_v2.away.knowledge_base import KnowledgeBase
from omni_v2.memory.hybrid_memory import HybridMemory


def _fake_search(query):
    return [
        ResearchFinding(query=query, url="https://example.com/a",
                        title=f"Result for {query}", snippet=f"About {query}: facts here."),
        ResearchFinding(query=query, url="https://example.com/b",
                        title="Second", snippet="more detail"),
    ]


def test_research_collects_findings():
    agent = ResearchAgent(search_fn=_fake_search)
    report = agent.research("solar panels")
    assert report.status == "done"
    assert len(report.findings) >= 2
    assert report.to_markdown().startswith("# Research Report")


def test_research_writes_to_kb():
    with tempfile.TemporaryDirectory() as tmp:
        mem = HybridMemory(persist_dir=Path(tmp) / "kb")
        kb = KnowledgeBase(memory=mem)
        agent = ResearchAgent(search_fn=_fake_search, knowledge_base=kb)
        agent.research("deep learning")
        assert kb.query("deep learning")["hit_count"] >= 1


def test_research_empty_provider():
    agent = ResearchAgent(search_fn=lambda q: [])
    report = agent.research("nothing")
    assert report.status == "done"
    assert len(report.findings) == 0


def test_research_query_builder():
    agent = ResearchAgent(search_fn=_fake_search)
    queries = agent.query_builder("autonomous vehicles")
    assert len(queries) >= 2
    assert "autonomous vehicles" in queries[0].lower()


def test_research_dedupes_urls():
    def dup_search(q):
        return [
            ResearchFinding(query=q, url="https://dup.com", title="x", snippet="one"),
            ResearchFinding(query=q, url="https://dup.com", title="x", snippet="two"),
        ]
    agent = ResearchAgent(search_fn=dup_search)
    report = agent.research("topic")
    urls = [f.url for f in report.findings]
    assert len(urls) == len(set(urls))


def test_research_report_to_dict():
    r = ResearchReport(topic="t")
    r.findings.append(ResearchFinding(query="q", url="u", snippet="s"))
    d = r.to_dict()
    assert d["topic"] == "t"
    assert d["findings"][0]["url"] == "u"


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
