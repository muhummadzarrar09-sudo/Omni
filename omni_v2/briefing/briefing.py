"""
OMNI MORNING BRIEFING (Phase 11) — "Jarvis greets you by name with real intel."

A scheduled agent that gathers, in one shot:
  - your open goals (from the goal stack)
  - yesterday's recap (from episodic reflection / session memory)
  - a fresh research brief (from the research agent, e.g. your top topics)

Then it renders a structured markdown briefing and delivers it via the messenger
(WhatsApp / Telegram / file) AND saves it as a report. Ready to be scheduled.

Fully local, headless-testable: all inputs are pluggable, so tests use fakes.
"""
from __future__ import annotations
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Briefing")


class MorningBriefing:
    """Gathers intel and renders a structured daily briefing."""

    def __init__(
        self,
        goals=None,           # GoalStack (optional)
        reflector=None,       # Reflector (optional) for yesterday recap
        research=None,        # ResearchAgent (optional) for fresh brief
        reporter=None,        # Reporter (optional) to save the report
        messenger=None,       # Messenger (optional) to deliver
        identity=None,        # IdentityCore (optional) for greeting by name
    ):
        self.goals = goals
        self.reflector = reflector
        self.research = research
        self.reporter = reporter
        self.messenger = messenger
        self.identity = identity

    def build(self, research_topic: str = "", max_goals: int = 8,
              max_findings: int = 5) -> Dict[str, Any]:
        """Assemble the briefing data and markdown. Returns dict."""
        now = datetime.now()
        user_name = ""
        if self.identity is not None:
            try:
                user_name = self.identity.user.name or ""
            except Exception:
                pass
        greeting = f"Good morning{f', {user_name}' if user_name else ''}."

        # 1) open goals
        goals_list = []
        if self.goals is not None:
            try:
                for g in self.goals.list_goals(limit=max_goals):
                    if g.status in ("active", "pending", "blocked"):
                        goals_list.append({
                            "title": g.title,
                            "status": g.status,
                            "progress": g.progress,
                            "next_step": g.steps[0].desc if g.steps else "",
                        })
            except Exception as e:
                logger.warning(f"briefing goals failed: {e}")

        # 2) yesterday recap
        recap = ""
        if self.reflector is not None:
            try:
                eps = self.reflector.episodes(3)
                if eps:
                    recap = eps[0].summary  # most recent episode
            except Exception as e:
                logger.warning(f"briefing recap failed: {e}")

        # 3) fresh research brief
        findings = []
        if self.research is not None and research_topic:
            try:
                report = self.research.research(research_topic)
                findings = [f.to_dict() for f in report.findings[:max_findings]]
            except Exception as e:
                logger.warning(f"briefing research failed: {e}")

        markdown = self._render(greeting, goals_list, recap, findings, research_topic)
        return {
            "greeting": greeting,
            "user_name": user_name,
            "goals": goals_list,
            "recap": recap,
            "findings": findings,
            "research_topic": research_topic,
            "markdown": markdown,
            "generated_at": now.isoformat(),
        }

    @staticmethod
    def _render(greeting, goals, recap, findings, research_topic) -> str:
        lines = [f"# ☀️ {greeting}", ""]
        if goals:
            lines += ["## 🎯 Your goals", ""]
            for g in goals:
                lines.append(f"- **{g['title']}** ({g['status']}, {g['progress']:.0%})")
                if g.get("next_step"):
                    lines.append(f"  - next: {g['next_step']}")
        else:
            lines += ["## 🎯 Goals", "- No open goals.", ""]
        if recap:
            lines += ["## 🧠 Yesterday", "", recap, ""]
        if research_topic:
            lines += [f"## 🔬 Research: {research_topic}", ""]
            if findings:
                for f in findings:
                    lines.append(f"- **{f.get('title') or f.get('url', '')}**")
                    if f.get("snippet"):
                        lines.append(f"  {f['snippet'][:120]}")
            else:
                lines.append("- No fresh findings this morning.")
            lines.append("")
        lines += ["---", f"_Generated {datetime.now().strftime('%A %B %d, %H:%M')}_"]
        return "\n".join(lines)

    def deliver(self, research_topic: str = "", save_report: bool = True,
                push: bool = True) -> Dict[str, Any]:
        """Build + save + push the briefing. Returns result dict."""
        data = self.build(research_topic=research_topic)
        saved_path = ""
        if save_report and self.reporter is not None:
            try:
                rep = self.reporter.save_report("Morning Briefing", data["markdown"])
                saved_path = str(rep.path)
            except Exception as e:
                logger.warning(f"briefing save failed: {e}")
        pushed = False
        if push and self.messenger is not None:
            try:
                # push a concise version (messenger is short-form)
                short = data["markdown"]
                if len(short) > 3500:
                    short = short[:3500] + "\n… (full briefing saved locally)"
                res = self.messenger.send_text(short)
                pushed = res.ok
            except Exception as e:
                logger.warning(f"briefing push failed: {e}")
        return {**data, "saved_path": saved_path, "pushed": pushed}


def get_morning_briefing(**kwargs) -> MorningBriefing:
    return MorningBriefing(**kwargs)
