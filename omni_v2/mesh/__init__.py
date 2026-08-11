"""
OMNI MESH (Phase 16, #3) — multi-machine state sync.
Export/import/reconcile OMNI state across machines. Headless-testable.
"""
from omni_v2.mesh.mesh_sync import MeshSync, get_mesh

__all__ = ["MeshSync", "get_mesh"]
