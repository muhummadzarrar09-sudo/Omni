"""
Tests for the Credential Vault (Phase 14, #4) - encrypted local secrets with a gate.
Run: python -m pytest omni_v2/tests/test_vault.py -q
"""
import sys
import os
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("OMNI_DATA_DIR", str(tempfile.mkdtemp(prefix="omni_vault_")))

from cryptography.fernet import Fernet
from omni_v2.vault.vault import CredentialVault, PermissionDenied, VaultError


def _vault(tmp, approve=None):
    key = Fernet.generate_key()
    return CredentialVault(vault_dir=Path(tmp) / "vault", key=key, approve=approve)


def test_set_and_get_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp)
        v.set_secret("GITHUB_TOKEN", "ghp_secret123", callers=["mcp", "automation"])
        assert v.get_secret("GITHUB_TOKEN", caller="mcp") == "ghp_secret123"
        assert v.get_secret("GITHUB_TOKEN", caller="automation") == "ghp_secret123"


def test_permission_gate_denies_unknown():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp)
        v.set_secret("API_KEY", "k", callers=["mcp"])
        try:
            v.get_secret("API_KEY", caller="hacker")
            assert False, "should have denied"
        except PermissionDenied:
            pass


def test_default_omni_caller_allowed():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp)
        v.set_secret("KEY", "val", callers=["mcp"])
        assert v.get_secret("KEY", caller="omni") == "val"


def test_approve_hook_overrides_gate():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp, approve=lambda name, caller: True)
        v.set_secret("S", "v", callers=["mcp"])
        assert v.get_secret("S", caller="nobody") == "v"


def test_approve_hook_false_denies():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp, approve=lambda name, caller: False)
        v.set_secret("S", "v", callers=["mcp"])
        try:
            v.get_secret("S", caller="nobody")
            assert False
        except PermissionDenied:
            pass


def test_list_masks_values():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp)
        v.set_secret("A", "secretvalue", callers=["mcp"])
        listing = v.list_secrets()
        assert listing[0]["name"] == "A"
        assert "secretvalue" not in str(listing)  # never leaks the value


def test_persists_across_reload():
    with tempfile.TemporaryDirectory() as tmp:
        key = Fernet.generate_key()
        d = Path(tmp) / "vault"
        v1 = CredentialVault(vault_dir=d, key=key)
        v1.set_secret("X", "hello", callers=["mcp"])
        v2 = CredentialVault(vault_dir=d, key=key)
        assert v2.get_secret("X", caller="mcp") == "hello"


def test_delete_and_grant_revoke():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp)
        v.set_secret("S", "v", callers=["mcp"])
        v.grant("S", "extra")
        assert v.get_secret("S", caller="extra") == "v"
        v.revoke("S", "extra")
        try:
            v.get_secret("S", caller="extra")
            assert False
        except PermissionDenied:
            pass
        assert v.delete_secret("S") is True
        try:
            v.get_secret("S", caller="mcp")
            assert False
        except VaultError:
            pass


def test_missing_secret_raises():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp)
        try:
            v.get_secret("NOPE", caller="omni")
            assert False
        except VaultError:
            pass


def test_stats():
    with tempfile.TemporaryDirectory() as tmp:
        v = _vault(tmp)
        v.set_secret("A", "v")
        st = v.stats()
        assert st["secrets"] == 1
        assert st["names"] == ["A"]


if __name__ == "__main__":
    for fn in [f for f in list(globals()) if f.startswith("test_") and callable(globals()[f])]:
        try:
            globals()[fn]()
            print(f"PASSED {fn}")
        except AssertionError as e:
            print(f"FAILED {fn}: {e}")
            raise
    print("ALL PASSED")
