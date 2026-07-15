"""
OMNI V3 - Network Discovery Protocol

Shared data types for laptop-phone communication.

Discovery flow:
  1. Laptop broadcasts `_omni-brain._tcp.local.` via mDNS on port 8765
     - TXT records: version, model, name, capabilities
  2. Phone scans for `_omni-brain._tcp.local.` services
  3. Phone finds laptop, connects via WebSocket
  4. Phone shows QR code with: omni://pair?host=<ip>&port=8765&code=<6-digit>
  5. Laptop scans QR (or phone shows QR) → pairing complete

Privacy:
  - All on local WiFi
  - No data leaves devices
  - 6-digit pairing code expires in 5 minutes
"""
from __future__ import annotations
import secrets
import time
import hashlib
import string
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

# mDNS service type for OMNI brain discovery
SERVICE_TYPE = "_omni-brain._tcp.local."
SERVICE_PORT = 8765

# Discovery protocol constants
DISCOVERY_PORT = 47624
DISCOVERY_MAGIC = b"OMNI-DISCOVER-v1"
DISCOVERY_INTERVAL_SEC = 5.0
DISCOVERY_TIMEOUT_SEC = 2.0


@dataclass
class NetworkInfo:
    """Information about a discovered OMNI brain on the network."""
    name: str                       # User-friendly name ("Zarrar's OMNI")
    host: str                       # IP or hostname
    port: int                       # API port
    version: str                    # OMNI version
    model: str                      # Brain model
    capabilities: List[str]         # ["voice", "vision", "wake_word", ...]
    api_version: str = "1.0"        # API version
    discovered_at: float = field(default_factory=time.time)

    @property
    def ws_url(self) -> str:
        """WebSocket URL for connecting to this brain."""
        return f"ws://{self.host}:{self.port}/ws/mobile"

    @property
    def http_url(self) -> str:
        """HTTP base URL for the API."""
        return f"http://{self.host}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ws_url"] = self.ws_url
        d["http_url"] = self.http_url
        return d


# Discovery TXT record keys
TXT_VERSION = "version"
TXT_MODEL = "model"
TXT_NAME = "name"
TXT_CAPABILITIES = "caps"
TXT_API = "api"
TXT_VERSION_VALUE = "3.2.0"
TXT_MODEL_DEFAULT = "qwen2.5-1.5b"
TXT_API_VALUE = "1.0"


@dataclass
class PairingCode:
    """A one-time pairing code for secure device linking."""
    code: str                       # 6-digit numeric
    host: str
    port: int
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    paired_devices: List[str] = field(default_factory=list)  # device_ids

    def is_valid(self) -> bool:
        """Check if this pairing code is still valid (not expired)."""
        return time.time() < self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "host": self.host,
            "port": self.port,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "valid": self.is_valid(),
        }

    def to_uri(self) -> str:
        """Convert to a omni:// URI for QR code."""
        return f"omni://pair?host={self.host}&port={self.port}&code={self.code}"


def generate_pairing_code(host: str, port: int = SERVICE_PORT, ttl_sec: int = 300) -> PairingCode:
    """
    Generate a one-time pairing code. Valid for `ttl_sec` seconds (default 5 min).
    The code is a 6-digit numeric that's hard to brute-force (1M combinations).
    """
    code = "".join(secrets.choice(string.digits) for _ in range(6))
    now = time.time()
    return PairingCode(
        code=code,
        host=host,
        port=port,
        created_at=now,
        expires_at=now + ttl_sec,
    )


def parse_pairing_code(uri: str) -> Optional[PairingCode]:
    """
    Parse an omni://pair?code=...&host=...&port=... URI.
    Returns None if the URI is invalid.
    """
    if not uri.startswith("omni://"):
        return None
    try:
        # Strip omni://
        rest = uri[len("omni://"):]
        # Split path from query
        if "?" not in rest:
            return None
        path, query = rest.split("?", 1)
        if path != "pair":
            return None
        # Parse query params
        params = {}
        for part in query.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = v
        if "code" not in params or "host" not in params:
            return None
        port = int(params.get("port", SERVICE_PORT))
        return PairingCode(
            code=params["code"],
            host=params["host"],
            port=port,
        )
    except Exception:
        return None


def device_id_from_public_key(public_key_bytes: bytes) -> str:
    """Derive a stable device ID from a public key (for trust)."""
    return hashlib.sha256(public_key_bytes).hexdigest()[:16]


def make_qr_payload(info: NetworkInfo) -> str:
    """Generate a QR code payload string for the mobile app to scan."""
    # Simple: JSON-serialized info. Phone scans and parses.
    import json
    return json.dumps({
        "type": "omni-discover",
        "name": info.name,
        "host": info.host,
        "port": info.port,
        "version": info.version,
        "model": info.model,
        "caps": info.capabilities,
    })


def parse_qr_payload(payload: str) -> Optional[NetworkInfo]:
    """Parse a QR code payload into a NetworkInfo."""
    import json
    try:
        data = json.loads(payload)
        if data.get("type") != "omni-discover":
            return None
        return NetworkInfo(
            name=data.get("name", "OMNI"),
            host=data["host"],
            port=int(data.get("port", SERVICE_PORT)),
            version=data.get("version", "unknown"),
            model=data.get("model", "unknown"),
            capabilities=data.get("caps", []),
        )
    except Exception:
        return None


def make_discovery_info(name: str = "OMNI", port: int = SERVICE_PORT) -> NetworkInfo:
    """Helper: build a NetworkInfo for the current laptop."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    return NetworkInfo(
        name=name,
        host=ip,
        port=port,
        version=TXT_VERSION_VALUE,
        model=TXT_MODEL_DEFAULT,
        capabilities=["voice", "vision", "wake_word", "memory", "personality", "marketplace"],
        api_version=TXT_API_VALUE,
    )
