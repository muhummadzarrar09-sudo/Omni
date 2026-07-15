"""
OMNI V3 - mDNS Service Discovery (Phase 5A)

Auto-discovery of OMNI brains on the local network.

**Why custom mDNS?** Most mDNS libraries (zeroconf, avahi) require installation.
We want zero external dependencies. So we implement a minimal HTTP-based
discovery protocol on top of UDP broadcast — simpler, works everywhere.

Protocol:
  - Laptop broadcasts a UDP packet to 255.255.255.255:47624 every 5s
  - Phone listens, finds laptops, gets info
  - Phone connects via WebSocket

This is NOT real mDNS/Bonjour. It's "mDNS-style" — same purpose, simpler.
For real mDNS, install zeroconf and use OMNIMDNSDiscoveryZeroconf (future).
"""
from __future__ import annotations
import socket
import json
import time
import threading
import logging
import struct
from typing import Optional, List, Dict, Any, Callable
from dataclasses import asdict

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("OMNIMDNS")

from omni_v2.network.discovery import (
    NetworkInfo,
    SERVICE_TYPE,
    SERVICE_PORT,
    TXT_VERSION,
    TXT_MODEL,
    TXT_NAME,
    TXT_CAPABILITIES,
    TXT_API,
    TXT_VERSION_VALUE,
    TXT_MODEL_DEFAULT,
    TXT_API_VALUE,
)


# Discovery protocol constants
DISCOVERY_PORT = 47624
DISCOVERY_MAGIC = b"OMNI-DISCOVER-v1"
DISCOVERY_INTERVAL_SEC = 5.0
DISCOVERY_TIMEOUT_SEC = 2.0


class OMNIMDNSBroadcaster:
    """
    Laptop-side: broadcasts OMNI presence on the local network.
    Sends a UDP broadcast packet every 5 seconds with brain info.
    """

    def __init__(self, port: int = SERVICE_PORT, name: str = "OMNI", capabilities: Optional[List[str]] = None):
        self.port = port
        self.name = name
        self.capabilities = capabilities or ["voice", "vision", "wake_word", "memory", "personality"]
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None
        self._announce_count = 0
        logger.info(f"📡 mDNS Broadcaster initialized (port {port}, name '{name}')")

    def start(self) -> None:
        """Start broadcasting in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="MDNS-Broadcast", daemon=True)
        self._thread.start()
        logger.info("🟢 mDNS Broadcaster started")

    def stop(self) -> None:
        """Stop broadcasting."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        logger.info("🔴 mDNS Broadcaster stopped")

    def _get_local_ip(self) -> str:
        """Get the primary local IP address (not 127.0.0.1)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            # Doesn't actually connect, just resolves the route
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _build_packet(self) -> bytes:
        """Build the discovery broadcast packet."""
        ip = self._get_local_ip()
        payload = {
            "magic": "OMNI-DISCOVER-v1",
            "name": self.name,
            "host": ip,
            "port": self.port,
            "version": TXT_VERSION_VALUE,
            "model": TXT_MODEL_DEFAULT,
            "api": TXT_API_VALUE,
            "caps": self.capabilities,
            "ts": time.time(),
        }
        return json.dumps(payload).encode("utf-8")

    def _loop(self) -> None:
        """Main broadcast loop."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._sock.settimeout(2.0)
        except Exception as e:
            logger.error(f"mDNS socket create failed: {e}")
            self._running = False
            return

        while self._running:
            try:
                packet = self._build_packet()
                self._sock.sendto(packet, ("<broadcast>", DISCOVERY_PORT))
                self._announce_count += 1
            except Exception as e:
                logger.debug(f"Broadcast error: {e}")
            time.sleep(DISCOVERY_INTERVAL_SEC)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "name": self.name,
            "host": self._get_local_ip(),
            "port": self.port,
            "announce_count": self._announce_count,
            "interval_sec": DISCOVERY_INTERVAL_SEC,
        }


class OMNIMDNSDiscovery:
    """
    Phone-side: scans the local network for OMNI brains.
    Listens for UDP broadcast packets and returns found brains.
    """

    def __init__(self, callback: Optional[Callable[[NetworkInfo], None]] = None):
        self._callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None
        self._found: Dict[str, NetworkInfo] = {}  # keyed by host:port
        self._lock = threading.Lock()
        logger.info("📡 mDNS Discovery initialized (phone-side)")

    def start(self) -> None:
        """Start listening for OMNI broadcasts."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="MDNS-Discover", daemon=True)
        self._thread.start()
        logger.info("🟢 mDNS Discovery started (listening)")

    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        logger.info("🔴 mDNS Discovery stopped")

    def get_found(self) -> List[NetworkInfo]:
        """Get list of found OMNI brains."""
        with self._lock:
            return list(self._found.values())

    def clear(self) -> None:
        """Clear found list."""
        with self._lock:
            self._found.clear()

    def _loop(self) -> None:
        """Main listener loop."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # On macOS/Linux, also need SO_REUSEPORT
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except Exception:
                    pass
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._sock.bind(("", DISCOVERY_PORT))
            self._sock.settimeout(1.0)
        except Exception as e:
            logger.error(f"mDNS listener socket failed: {e}")
            self._running = False
            return

        while self._running:
            try:
                data, addr = self._sock.recvfrom(4096)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.debug(f"Listen error: {e}")
                continue
            self._handle_packet(data, addr)

    def _handle_packet(self, data: bytes, addr: tuple) -> None:
        """Parse a received discovery packet."""
        try:
            payload = json.loads(data.decode("utf-8"))
        except Exception:
            return
        if payload.get("magic") != "OMNI-DISCOVER-v1":
            return
        # Build NetworkInfo
        host = payload.get("host", addr[0])
        port = int(payload.get("port", SERVICE_PORT))
        key = f"{host}:{port}"
        # Skip stale (older than 30s)
        if time.time() - payload.get("ts", 0) > 30:
            return
        info = NetworkInfo(
            name=payload.get("name", "OMNI"),
            host=host,
            port=port,
            version=payload.get("version", "unknown"),
            model=payload.get("model", "unknown"),
            capabilities=payload.get("caps", []),
        )
        with self._lock:
            is_new = key not in self._found
            self._found[key] = info
        if is_new and self._callback:
            try:
                self._callback(info)
            except Exception as e:
                logger.debug(f"Callback error: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "found_count": len(self.get_found()),
            "found": [info.to_dict() for info in self.get_found()],
        }

