"""
OMNI CREDENTIAL VAULT (Phase 14, #4) — local, encrypted secrets with a gate.

Stores API keys / secrets / tokens LOCALLY and ENCRYPTED at rest so tools,
automations, and MCP servers can authenticate without plaintext secrets lying
around in config or logs.

Design:
  - FERNET ENCRYPTION AT REST: each secret is encrypted with a Fernet key. The
    key is derived from a local keyfile (data/brain/vault_key) or a passphrase
    env var (OMNI_VAULT_KEY). If neither exists, a keyfile is generated.
  - PERMISSION GATE: a caller must be ALLOWED to read a given secret. The gate
    is pluggable: a default allow-list of caller names, or an approve callback
    (HITL). This mirrors "permission checks before tools use secrets".
  - LIST masks values (shows only names + which callers are allowed).
  - Fully local + headless-testable (Fernet works offline; we can inject a key
    for tests so they don't depend on the keyfile).

Usage:
    omni vault set GITHUB_TOKEN secret123 --callers mcp,automation
    omni vault get GITHUB_TOKEN --caller automation   # works
    omni vault get GITHUB_TOKEN --caller unknown      # DENIED
    omni vault list
    omni vault delete GITHUB_TOKEN
"""
from __future__ import annotations
import os
import json
import time
import base64
import getpass
import hashlib
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("Vault")

from omni_v2.core.paths import DATA_DIR

VAULT_DIR = DATA_DIR / "brain" / "vault"
VAULT_FILE = VAULT_DIR / "vault.json"
KEY_FILE = VAULT_DIR / "vault_key"
ENV_KEY = "OMNI_VAULT_KEY"

# default allow-list: callers allowed to read any secret by default
DEFAULT_ALLOWED = {"omni", "self"}


class VaultError(Exception):
    pass


class PermissionDenied(VaultError):
    pass


class CredentialVault:
    """Encrypted, permission-gated local secret store."""

    def __init__(self, vault_dir: Optional[Path] = None,
                 key: Optional[bytes] = None, approve: Optional[Callable[[str, str], bool]] = None):
        self.vault_dir = Path(vault_dir) if vault_dir else VAULT_DIR
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.vault_file = self.vault_dir / "vault.json"
        self.approve = approve            # optional HITL gate: approve(secret_name, caller)->bool
        self._lock = threading.RLock()
        self._fernet = None
        self._data: Dict[str, Dict[str, Any]] = {}
        self._init_crypto(key)
        self._load()

    # -- crypto -------------------------------------------------------------
    def _init_crypto(self, key: Optional[bytes]) -> None:
        from cryptography.fernet import Fernet
        if key is not None:
            self._fernet = Fernet(key)
            return
        # try env passphrase
        env = os.environ.get(ENV_KEY)
        if env:
            self._fernet = Fernet(self._derive(env))
            return
        # keyfile
        if KEY_FILE.exists():
            self._fernet = Fernet(KEY_FILE.read_bytes())
            return
        # generate a keyfile
        key = Fernet.generate_key()
        KEY_FILE.write_bytes(key)
        self._fernet = Fernet(key)
        logger.info(f"🔐 Vault key generated at {KEY_FILE} (protect this file)")

    @staticmethod
    def _derive(passphrase: str) -> bytes:
        return base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest())

    # -- persistence ---------------------------------------------------------
    def _load(self) -> None:
        try:
            if self.vault_file.exists():
                self._data = json.loads(self.vault_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"vault load failed: {e}")

    def _save(self) -> None:
        with self._lock:
            try:
                self.vault_file.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"vault save failed: {e}")

    def _encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()

    # -- CRUD ----------------------------------------------------------------
    def set_secret(self, name: str, value: str, callers: Optional[List[str]] = None,
                   metadata: str = "") -> Dict[str, Any]:
        if not name or value is None:
            raise VaultError("name and value required")
        allowed = callers or list(DEFAULT_ALLOWED)
        with self._lock:
            self._data[name] = {
                "ciphertext": self._encrypt(value),
                "allowed": allowed,
                "metadata": metadata,
                "updated_at": time.time(),
            }
            self._save()
        return {"ok": True, "name": name, "callers": allowed}

    def get_secret(self, name: str, caller: str = "omni") -> str:
        """Read a secret, gated by permission. Raises PermissionDenied if not allowed."""
        entry = self._data.get(name)
        if entry is None:
            raise VaultError(f"no secret '{name}'")
        if caller not in entry.get("allowed", []) and caller not in DEFAULT_ALLOWED:
            # HITL approve hook
            if self.approve is not None and self.approve(name, caller):
                pass
            else:
                raise PermissionDenied(f"caller '{caller}' not allowed to read '{name}'")
        return self._decrypt(entry["ciphertext"])

    def list_secrets(self) -> List[Dict[str, Any]]:
        """List secret metadata only (never the values)."""
        out = []
        for name, e in self._data.items():
            out.append({"name": name, "allowed": e.get("allowed", []),
                        "metadata": e.get("metadata", ""),
                        "updated_at": e.get("updated_at", 0)})
        return sorted(out, key=lambda x: x["name"])

    def delete_secret(self, name: str) -> bool:
        with self._lock:
            if name in self._data:
                del self._data[name]
                self._save()
                return True
            return False

    def grant(self, name: str, caller: str) -> bool:
        with self._lock:
            if name not in self._data:
                return False
            allowed = self._data[name].setdefault("allowed", [])
            if caller not in allowed:
                allowed.append(caller)
                self._save()
            return True

    def revoke(self, name: str, caller: str) -> bool:
        with self._lock:
            if name not in self._data:
                return False
            allowed = self._data[name].get("allowed", [])
            if caller in allowed:
                allowed.remove(caller)
                self._save()
            return True

    # -- introspection ---------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        return {"secrets": len(self._data),
                "names": [e["name"] for e in self.list_secrets()],
                "vault_file": str(self.vault_file),
                "key_source": "keyfile" if KEY_FILE.exists() else
                              ("env" if os.environ.get(ENV_KEY) else "generated")}


def get_vault(**kwargs) -> CredentialVault:
    return CredentialVault(**kwargs)
