"""
OMNI REPORTER - builds and archives markdown/HTML reports and digests.

Reports land in data/reports/{YYYY-MM-DD}/{slug}.md so they're always
available locally. The Reporter also renders a short text summary that the
messenger can push to your phone (WhatsApp/Telegram).
"""
from __future__ import annotations
import time
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Reporter")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"

REPORTS_DIR = DATA_DIR / "reports"


@dataclass
class Report:
    title: str
    markdown: str
    summary: str
    path: Optional[Path] = None
    created_at: float = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "path": str(self.path) if self.path else None,
            "created_at": self.created_at,
        }


class Reporter:
    """Builds, saves and summarizes reports."""

    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = Path(reports_dir) if reports_dir else REPORTS_DIR

    def _slug(self, title: str) -> str:
        s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return s or "report"

    def save_report(self, title: str, markdown: str) -> Report:
        day = datetime.now().strftime("%Y-%m-%d")
        out_dir = self.reports_dir / day
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = self._slug(title)
        path = out_dir / f"{slug}.md"
        path.write_text(markdown, encoding="utf-8")
        report = Report(
            title=title,
            markdown=markdown,
            summary=self.summarize(markdown),
            path=path,
        )
        logger.info(f"Report saved: {path}")
        return report

    def build_research_report(self, report_data: Any) -> Report:
        """Wrap a ResearchReport into a saved Report."""
        md = report_data.to_markdown() if hasattr(report_data, "to_markdown") else str(report_data)
        n = len(getattr(report_data, "findings", []))
        title = f"Research: {report_data.topic}"
        summary = f"Research complete on '{report_data.topic}' — {n} finding(s) gathered. Full report saved locally."
        return self.save_report(title, md)

    def build_digest(self, memory_summary: str, label: str = "digest") -> Report:
        now = datetime.now().strftime("%A %B %d, %Y %H:%M")
        title = f"OMNI Away Digest {label}"
        md = (
            f"# OMNI Away Digest — {label}\n\n"
            f"_Generated {now}_\n\n"
            f"{memory_summary}\n"
        )
        return self.save_report(title, md)

    @staticmethod
    def summarize(markdown: str, max_chars: int = 400) -> str:
        """Short plain-text summary of a markdown report for phone push."""
        text = re.sub(r"[#>*`_\[\]()]+", " ", markdown)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + "…"

    def list_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        out = []
        for path in sorted(self.reports_dir.rglob("*.md"), reverse=True):
            try:
                title = path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
            except Exception:
                title = path.name
            out.append({"title": title, "path": str(path)})
            if len(out) >= n:
                break
        return out


def get_reporter(reports_dir: Optional[Path] = None) -> Reporter:
    return Reporter(reports_dir=reports_dir)
