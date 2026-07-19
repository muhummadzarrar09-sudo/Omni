"""
OMNI V3 - E2E Sync (Phase 4E: "Sync between devices")

Encrypted sync of memory + personality + skills between your devices.
XChaCha20-Poly1305 AEAD for encryption.
Conflict resolution: last-write-wins on timestamp.

NOTE: This is a stub for the AIM. The full implementation would require:
  - Encryption key exchange (X25519)
  - Reliable cloud relay (or peer-to-peer via libp2p)
  - Conflict resolution

For now, the API is in place and ready to wire.
"""
from __future__ import annotations
import time
import json
import hashlib
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("E2ESync")

try:
    from omni_v2.core.paths import DATA_DIR
except Exception:
    DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class E2ESyncService:
    """
    End-to-end encrypted sync between OMNI devices.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.sync_dir = DATA_DIR / "sync"
        self.sync_dir.mkdir(parents=True, exist_ok=True)
        self.devices_file = self.sync_dir / "devices.json"
        self._devices: Dict[str, Dict] = {}
        self._load()
        self._initialized = True
        logger.info(f"🔄 E2ESync initialized (devices: {len(self._devices)})")

    def _load(self):
        if self.devices_file.exists():
            try:
                self._devices = json.loads(self.devices_file.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save(self):
        try:
            self.devices_file.write_text(
                json.dumps(self._devices, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Sync save: {e}")

    def register_device(self, device_id: str, name: str, platform: str = "unknown") -> Dict[str, Any]:
        """Register a new device for sync."""
        with self._lock:
            self._devices[device_id] = {
                "device_id": device_id,
                "name": name,
                "platform": platform,
                "last_sync": 0.0,
                "registered_at": time.time(),
            }
            self._save()
            return self._devices[device_id]

    def list_devices(self) -> List[Dict[str, Any]]:
        return list(self._devices.values())

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": False,  # Not fully wired yet
            "devices": len(self._devices),
            "sync_dir": str(self.sync_dir),
        }


def get_sync() -> E2ESyncService:
    return E2ESyncService()
