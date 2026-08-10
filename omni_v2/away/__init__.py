"""
OMNI AWAY MODE - unattended research, hybrid RAG+CAG knowledge base,
and phone reports/commands, all fully local.

Modules:
  hybrid_memory      -> (omni_v2.memory) LONG-term RAG + SHORT-term CAG cache
  knowledge_base     -> ingest files/folders/URLs into hybrid memory
  research           -> autonomous multi-step research agent
  reporter           -> build + save markdown reports & digests
  messenger          -> WhatsApp / Telegram / file report bridge
  away_agent         -> persistent unattended task queue + runner
  command_channel    -> remote commands from your phone
"""
from omni_v2.away.knowledge_base import KnowledgeBase, get_knowledge_base
from omni_v2.away.research import ResearchAgent, ResearchReport
from omni_v2.away.reporter import Reporter, Report
from omni_v2.away.away_agent import AwayAgent, AwayTask, get_away_agent
from omni_v2.away.command_channel import CommandRouter, CommandPoller

__all__ = [
    "KnowledgeBase", "get_knowledge_base",
    "ResearchAgent", "ResearchReport",
    "Reporter", "Report",
    "AwayAgent", "AwayTask", "get_away_agent",
    "CommandRouter", "CommandPoller",
]
