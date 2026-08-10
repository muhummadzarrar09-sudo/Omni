"""
OMNI RESEARCH AGENT - autonomous, multi-step web research that runs unattended.

Given a topic/question, it:
  1. Generates a set of search queries (LLM if available, else deterministic).
  2. Runs each query through a search provider (browser tool or a simple
     fetcher). Default provider is offline-testable; real provider uses the
     OMNI browser tools.
  3. Collects findings into a structured ResearchReport.
  4. Stores every finding into the knowledge base (hybrid RAG+CAG memory) so
     future questions benefit from it.
  5. Returns a markdown report ready for the Reporter/messenger.

The research loop is provider-agnostic: swap in a live provider (Playwright /
browser_v3) for real use; tests use a FakeProvider. Everything degrades
gracefully offline (a provider that returns [] just yields empty findings).
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("ResearchAgent")

try:
    from omni_v2.away.knowledge_base import KnowledgeBase
except Exception:  # pragma: no cover
    KnowledgeBase = None


@dataclass
class ResearchFinding:
    query: str
    url: str = ""
    title: str = ""
    snippet: str = ""
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchReport:
    topic: str
    findings: List[ResearchFinding] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    status: str = "pending"  # pending | done | error

    def to_markdown(self) -> str:
        lines = [f"# Research Report: {self.topic}", ""]
        if not self.findings:
            lines.append("_No findings returned. The search provider returned no results._")
        for i, f in enumerate(self.findings, 1):
            lines.append(f"## {i}. {f.title or f.url or f.query}")
            if f.url:
                lines.append(f"Source: {f.url}")
            if f.snippet:
                lines.append(f.snippet)
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "status": self.status,
            "findings": [f.to_dict() for f in self.findings],
        }


class ResearchAgent:
    """Runs autonomous research, writes findings to the knowledge base."""

    def __init__(
        self,
        search_fn: Optional[Callable[[str], List[ResearchFinding]]] = None,
        knowledge_base: Optional[KnowledgeBase] = None,
        query_builder: Optional[Callable[[str], List[str]]] = None,
        max_queries: int = 4,
    ):
        self.search_fn = search_fn or self._default_search
        self.kb = knowledge_base
        self.query_builder = query_builder or self._build_queries
        self.max_queries = max_queries

    # -- query generation -------------------------------------------------
    def _build_queries(self, topic: str) -> List[str]:
        """Deterministic fallback query builder (works with no LLM)."""
        t = topic.strip().strip("?.")
        variants = [
            f"{t}",
            f"what is {t}",
            f"how does {t} work",
            f"{t} overview 2026",
        ]
        return variants[: self.max_queries]

    # -- search providers ---------------------------------------------------
    def _default_search(self, query: str) -> List[ResearchFinding]:
        """
        Default search provider: try OMNI's browser tools, else return [].
        Override `search_fn` for a live provider.
        """
        try:
            from omni_v2.tools.browser_v3 import BrowserToolV3
            browser = BrowserToolV3()
            res = browser.search(query)
            if isinstance(res, dict) and res.get("success") and res.get("data"):
                return self._parse_search_results(res["data"], query)
        except Exception as e:
            logger.debug(f"Research default search unavailable: {e}")
        # Playwright-based fallback
        try:
            from omni_v2.tools.browser_playwright import PlaywrightBrowser
            browser = PlaywrightBrowser()
            results = browser.search(query)
            return self._parse_search_results(results, query)
        except Exception as e:
            logger.debug(f"Research playwright search unavailable: {e}")
        return []

    @staticmethod
    def _parse_search_results(data: Any, query: str) -> List[ResearchFinding]:
        findings: List[ResearchFinding] = []
        # accept list of {title,url,snippet} or {title,link,description}
        items = data if isinstance(data, list) else data.get("results", [])
        for it in items or []:
            if not isinstance(it, dict):
                continue
            url = it.get("url") or it.get("link") or it.get("href") or ""
            title = it.get("title") or ""
            snippet = it.get("snippet") or it.get("description") or it.get("text") or ""
            if not url and not snippet:
                continue
            findings.append(ResearchFinding(
                query=query, url=url, title=title, snippet=snippet,
            ))
        return findings

    # -- main loop ----------------------------------------------------------
    def research(self, topic: str) -> ResearchReport:
        report = ResearchReport(topic=topic)
        queries = self.query_builder(topic)
        seen_urls = set()
        for q in queries:
            try:
                results = self.search_fn(q) or []
            except Exception as e:
                logger.warning(f"Research query '{q}' failed: {e}")
                continue
            for f in results:
                if f.url and f.url in seen_urls:
                    continue
                if f.url:
                    seen_urls.add(f.url)
                report.findings.append(f)
        report.status = "done"
        report.completed_at = time.time()

        # Store findings into the knowledge base (hybrid RAG+CAG memory)
        if self.kb is not None:
            try:
                for f in report.findings:
                    if f.snippet:
                        self.kb.add_text(
                            f.snippet,
                            source=f.url or f.query,
                            title=f.title or f.query,
                        )
            except Exception as e:
                logger.warning(f"Research KB ingest failed: {e}")

        logger.info(f"Research done for '{topic}': {len(report.findings)} findings")
        return report


def get_research_agent(**kwargs) -> ResearchAgent:
    return ResearchAgent(**kwargs)
