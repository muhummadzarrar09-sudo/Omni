"""
OMNI KNOWLEDGE GRAPH (Phase 11) — visualize your memory as a graph.

Builds an interactive node/edge graph from the RAG+CAG memory and session data.
Output is JSON {nodes, edges} renderable by any UI. Fully local, headless-testable.
"""
from omni_v2.graph.knowledge_graph import KnowledgeGraphBuilder, get_knowledge_graph

__all__ = ["KnowledgeGraphBuilder", "get_knowledge_graph"]
