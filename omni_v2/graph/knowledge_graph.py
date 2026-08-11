"""
OMNI KNOWLEDGE GRAPH (Phase 11) — visualize your memory as a graph.

Builds an interactive graph from the RAG+CAG memory and session data:
  - nodes: entities, topics, files, tools, people, commands
  - edges: co-occurrence / connections ("you always work on X after Y")

Output is a simple JSON graph {nodes, edges} that any UI (web / desktop) can
render. A lightweight web viewer is included (see knowledge_graph_viewer.py).

Fully local, headless-testable: the graph builder works purely from data.
"""
from __future__ import annotations
import re
import json
import time
import threading
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("KnowledgeGraph")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path.cwd() / "data"


class KnowledgeGraphBuilder:
    """Builds a node/edge graph from memory + session data."""

    # node kinds
    KIND_TOPIC = "topic"
    KIND_FILE = "file"
    KIND_TOOL = "tool"
    KIND_COMMAND = "command"
    KIND_PERSON = "person"
    KIND_ENTITY = "entity"

    _TOPIC_STOP = {
        "the", "and", "for", "you", "your", "omni", "open", "please", "with",
        "that", "this", "from", "have", "what", "how", "can", "want", "need",
        "about", "into", "after", "should", "could", "please", "would", "there",
    }

    def __init__(self, memory=None, session_memory=None):
        self.memory = memory          # HybridMemory (optional)
        self.session = session_memory  # SessionMemoryStore (optional)

    # -- node/edge helpers -------------------------------------------------
    @staticmethod
    def _hash(name: str, kind: str) -> str:
        return f"{kind}:{name.lower()[:64]}"

    def _add_node(self, nodes: Dict[str, Dict], name: str, kind: str) -> str:
        nid = self._hash(name, kind)
        if nid not in nodes:
            nodes[nid] = {"id": nid, "name": name, "kind": kind, "weight": 0}
        nodes[nid]["weight"] += 1
        return nid

    def _add_edge(self, edges: Dict[Tuple, Dict], a: str, b: str, kind: str = "co") -> None:
        key = tuple(sorted([a, b]))
        if key not in edges:
            edges[key] = {"source": key[0], "target": key[1], "kind": kind, "weight": 0}
        edges[key]["weight"] += 1

    # -- topics / entities ---------------------------------------------------
    @staticmethod
    def _extract_topics(text: str) -> List[str]:
        words = re.findall(r"[a-z][a-z0-9\-]{2,}", text.lower())
        return [w for w in words if w not in KnowledgeGraphBuilder._TOPIC_STOP]

    @staticmethod
    def _extract_files(text: str) -> List[str]:
        # match paths like /x/y.py, C:\x\y, x.py, x.md
        return re.findall(r"(?:[A-Za-z]:[/\\]|[/\\~]|\./)?[\w.\-/\\]+\.(?:py|md|txt|js|ts|json|html|css|sh|bat|yml|yaml|toml|ini)", text)

    @staticmethod
    def _extract_tools(text: str) -> List[str]:
        return re.findall(r"(?:browser|files|windows|system|vscode|media|integrations|ai)_[a-z_]+", text)

    # -- build ----------------------------------------------------------------
    def build(self, limit_memory: int = 200) -> Dict[str, Any]:
        """Build the graph from memory + sessions. Returns {nodes, edges, stats}."""
        nodes: Dict[str, Dict] = {}
        edges: Dict[Tuple, Dict] = {}

        # 1) from memory items (long-term RAG facts, episodic, documents)
        items = []
        if self.memory is not None:
            try:
                items = list(self.memory._items.values())  # noqa: SLF001
                if len(items) > limit_memory:
                    items = items[-limit_memory:]
            except Exception as e:
                logger.warning(f"memory read failed: {e}")
        for it in items:
            text = it.text
            src = it.source or ""
            kind = it.kind
            # file node from source
            files = self._extract_files(text) + ([src] if src and "." in src else [])
            for f in files:
                self._add_node(nodes, f, self.KIND_FILE)
            # topics
            topics = self._extract_topics(text)
            for t in topics[:8]:
                self._add_node(nodes, t, self.KIND_TOPIC)
            # connect topics to each other and to file
            for a, b in zip(topics[:8], topics[1:8]):
                self._add_edge(edges, self._hash(a, self.KIND_TOPIC), self._hash(b, self.KIND_TOPIC))
            for f in files[:3]:
                for t in topics[:4]:
                    self._add_edge(edges, self._hash(f, self.KIND_FILE), self._hash(t, self.KIND_TOPIC))
            if src:
                self._add_node(nodes, src, self.KIND_FILE)

        # 2) from session data (commands, tools, topics)
        sessions = []
        if self.session is not None:
            try:
                sessions = self.session.recall_sessions(days=14) or []
            except Exception as e:
                logger.warning(f"session recall failed: {e}")
        for s in sessions:
            d = s.to_dict() if hasattr(s, "to_dict") else s
            commands = d.get("commands", []) or []
            tool_calls = d.get("tool_calls", []) or []
            for c in commands:
                self._add_node(nodes, c[:60], self.KIND_COMMAND)
                for t in self._extract_topics(c)[:5]:
                    self._add_node(nodes, t, self.KIND_TOPIC)
                    self._add_edge(edges, self._hash(c[:60], self.KIND_COMMAND),
                                   self._hash(t, self.KIND_TOPIC))
            for tl in tool_calls:
                self._add_node(nodes, tl, self.KIND_TOOL)
            # connect tools used together (co-occurrence)
            if len(tool_calls) >= 2:
                for i in range(len(tool_calls) - 1):
                    self._add_edge(edges, self._hash(tool_calls[i], self.KIND_TOOL),
                                   self._hash(tool_calls[i + 1], self.KIND_TOOL), kind="seq")

        # prune low-weight topics to keep the graph browsable
        nodes = {k: v for k, v in nodes.items() if v["kind"] != self.KIND_TOPIC or v["weight"] > 0}
        node_list = sorted(nodes.values(), key=lambda n: -n["weight"])
        edge_list = sorted(edges.values(), key=lambda e: -e["weight"])
        return {
            "nodes": node_list,
            "edges": edge_list,
            "stats": {"nodes": len(node_list), "edges": len(edge_list),
                      "memory_items": len(items), "sessions": len(sessions)},
        }

    def to_json(self, path: Optional[Any] = None) -> str:
        data = self.build()
        js = json.dumps(data, indent=2)
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(js, encoding="utf-8")
        return js

    def stats(self) -> Dict[str, Any]:
        g = self.build()
        return g["stats"]


def get_knowledge_graph(**kwargs) -> KnowledgeGraphBuilder:
    return KnowledgeGraphBuilder(**kwargs)
