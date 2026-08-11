"""
OMNI CREDENTIAL VAULT (Phase 14, #4) — local encrypted secrets with a gate.

Fernet-encrypted at rest, permission-gated reads. Fully local, headless-testable.
"""
from omni_v2.vault.vault import CredentialVault, VaultError, PermissionDenied, get_vault

__all__ = ["CredentialVault", "VaultError", "PermissionDenied", "get_vault"]
