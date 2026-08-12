"""Canonical local-model cache and network policy helpers.

Model libraries frequently download implicitly when passed a repository/model
name. Every such call site must project :class:`RuntimeConfig` into the
library's explicit cache and local-only switches so ``offline=true`` is a real
no-download policy rather than a UI label.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omni_v2.core.config import RuntimeConfig


class OfflineModeError(RuntimeError):
    """Raised before an operation that requires public-network access."""


def require_online(runtime_config: RuntimeConfig, operation: str) -> None:
    if runtime_config.offline:
        raise OfflineModeError(f"{operation} is disabled by canonical offline configuration")


def require_cloud_tts(runtime_config: RuntimeConfig, operation: str) -> None:
    require_online(runtime_config, operation)
    if not runtime_config.tts_allow_cloud:
        raise OfflineModeError(f"{operation} requires explicit tts_allow_cloud=true")


def faster_whisper_kwargs(runtime_config: RuntimeConfig) -> dict[str, Any]:
    """Return the explicit cache/no-download policy for Faster-Whisper."""

    cache_dir = runtime_config.models_dir / "stt" / "faster-whisper"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {
        "download_root": str(cache_dir),
        "local_files_only": runtime_config.offline,
    }


def huggingface_pretrained_kwargs(runtime_config: RuntimeConfig) -> dict[str, Any]:
    """Return the canonical Transformers cache and local-only policy."""

    cache_dir = runtime_config.models_dir / "huggingface"
    cache_dir.mkdir(parents=True, exist_ok=True)
    kwargs: dict[str, Any] = {
        "cache_dir": str(cache_dir),
        "local_files_only": runtime_config.offline,
    }
    if runtime_config.hf_token:
        kwargs["token"] = runtime_config.hf_token
    return kwargs


def huggingface_download_kwargs(runtime_config: RuntimeConfig, local_dir: Path) -> dict[str, Any]:
    """Return explicit Hugging Face Hub request policy.

    ``local_files_only`` makes the Hub client resolve an already-cached artifact
    without issuing HTTP requests. ``local_dir`` remains canonical and caller
    controlled beneath the configured models directory.
    """

    return {
        "local_dir": str(local_dir),
        "token": runtime_config.hf_token,
        "local_files_only": runtime_config.offline,
    }
