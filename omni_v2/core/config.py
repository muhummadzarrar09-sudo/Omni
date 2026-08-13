"""Canonical runtime configuration for OMNI.

The source of truth is deliberately small and explicit:

1. built-in safe defaults;
2. ``<data-dir>/config.json``;
3. documented environment-variable overrides.

Browser code never reads these values directly. The process launcher exports the
resolved server-side URL to Next.js, while browser requests remain same-origin.
Secret values are accepted only from the process environment and are never
written to ``config.json`` or included in diagnostics.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from omni_v2.core.paths import get_data_dir

CONFIG_SCHEMA_VERSION = 1
DEFAULT_BACKEND_HOST = "127.0.0.1"
DEFAULT_BACKEND_PORT = 8765
DEFAULT_FRONTEND_HOST = "127.0.0.1"
DEFAULT_FRONTEND_PORT = 3000
DEFAULT_DISCOVERY_PORT = 47624
DEFAULT_BROWSER_DEBUG_PORT = 9222
DEFAULT_FAST_MODEL = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
DEFAULT_DEEP_MODEL = "qwen2.5-3b-instruct-q4_k_m.gguf"
DEFAULT_STT_ENGINE = "auto"
DEFAULT_STT_MODEL = "base.en"
DEFAULT_STT_DEVICE = "auto"
DEFAULT_TTS_VOICE = "af_sarah"

_ENVIRONMENT_CONTRACT = {
    "OMNI_DATA_DIR": "Writable state root; resolved by omni_v2.core.paths.",
    "OMNI_BACKEND_HOST": "Backend bind host.",
    "OMNI_BACKEND_PORT": "Backend TCP port.",
    "OMNI_FRONTEND_HOST": "Frontend bind host.",
    "OMNI_FRONTEND_PORT": "Frontend TCP port.",
    "OMNI_DISCOVERY_PORT": "UDP local-network discovery port.",
    "OMNI_BACKEND_URL": "Derived server-side Next.js proxy target; launchers set this value.",
    "OMNI_CORS_ORIGINS": "Comma-separated exact browser origins.",
    "OMNI_MODELS_DIR": "Model directory; relative values are under the data root.",
    "OMNI_MODEL_PATH": "Fast GGUF path; relative values are under the model directory.",
    "OMNI_DEEP_MODEL_PATH": "Deep GGUF path; relative values are under the model directory.",
    "OMNI_STT_ENGINE": "Speech-to-text implementation preference.",
    "OMNI_STT_MODEL": "Speech-to-text model identifier.",
    "OMNI_STT_DEVICE": "Speech-to-text device preference.",
    "OMNI_TTS_VOICE": "Text-to-speech voice identifier.",
    "OMNI_TTS_ALLOW_CLOUD": "Whether text-to-speech may use cloud services.",
    "OMNI_MICROPHONE_DEVICE": "Microphone index or stable device name.",
    "OMNI_BROWSER_PATH": "Explicit browser executable.",
    "OMNI_BROWSER_PROFILE_DIR": "Isolated browser profile; relative values are under the data root.",
    "OMNI_BROWSER_DEBUG_PORT": "Isolated browser debugging port.",
    "OMNI_OFFLINE": "Requests offline behavior; full no-egress enforcement remains a B15 gate.",
    "OMNI_API_TOKEN": "API token (secret; environment only).",
    "HF_TOKEN": "Hugging Face token (secret; environment only).",
    "HUGGINGFACE_TOKEN": "Legacy alias for HF_TOKEN.",
    "PICOVOICE_ACCESS_KEY": "Picovoice key (secret; environment only).",
    "PICOVOICE_KEY": "Legacy Picovoice key alias.",
    "PORCUPINE_KEY": "Legacy Picovoice key alias.",
}

_HOST_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


class ConfigError(ValueError):
    """Raised when configuration is invalid or contradictory."""


def environment_contract() -> dict[str, str]:
    """Return the documented environment-variable contract."""

    return dict(_ENVIRONMENT_CONTRACT)


def _value(
    file_values: Mapping[str, Any],
    environment: Mapping[str, str],
    key: str,
    env_name: str,
    default: Any,
) -> Any:
    if env_name in environment and environment[env_name] != "":
        return environment[env_name]
    return file_values.get(key, default)


def _parse_port(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{name} must be an integer from 1 through 65535")
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer from 1 through 65535") from exc
    if not 1 <= port <= 65535:
        raise ConfigError(f"{name} must be an integer from 1 through 65535")
    return port


def _parse_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ConfigError(f"{name} must be one of: true, false, 1, 0, yes, no, on, off")


def _parse_host(value: Any, name: str) -> str:
    host = str(value).strip()
    valid = bool(host) and "/" not in host
    if valid and ":" in host:
        try:
            valid = ipaddress.ip_address(host).version == 6
        except ValueError:
            valid = False
    elif valid:
        valid = _HOST_PATTERN.fullmatch(host) is not None
    if not valid:
        raise ConfigError(f"{name} must be a host or IP address without a URL scheme, port, or path")
    return host


def _resolve_path(value: Any, base: Path, name: str) -> Path:
    raw = str(value).strip()
    if not raw:
        raise ConfigError(f"{name} cannot be empty")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _origin(value: Any) -> str:
    origin = str(value).strip().rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError(f"invalid CORS origin {origin!r}: expected http(s)://host[:port]")
    if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ConfigError(f"invalid CORS origin {origin!r}: paths, credentials, and queries are forbidden")
    try:
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ConfigError(f"invalid CORS origin {origin!r}: malformed host or port") from exc
    if not host or parsed.netloc.endswith(":"):
        raise ConfigError(f"invalid CORS origin {origin!r}: malformed host or port")
    _parse_host(host, "CORS origin host")
    if port is not None:
        _parse_port(port, "CORS origin port")
    return origin


def _origins(value: Any, frontend_port: int) -> tuple[str, ...]:
    default = (
        f"http://127.0.0.1:{frontend_port}",
        f"http://localhost:{frontend_port}",
    )
    if value is None or value == "":
        return default
    candidates = value.split(",") if isinstance(value, str) else value
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ConfigError("cors_origins must be a non-empty list or comma-separated string")
    resolved = tuple(dict.fromkeys(_origin(item) for item in candidates))
    if not resolved:
        raise ConfigError("cors_origins must contain at least one exact origin")
    return resolved


def _url_host(bind_host: str) -> str:
    """Return a connectable host for a service bound to ``bind_host``."""

    if bind_host == "0.0.0.0":
        return "127.0.0.1"
    if bind_host in {"::", "[::]"}:
        return "[::1]"
    if ":" in bind_host and not bind_host.startswith("["):
        return f"[{bind_host}]"
    return bind_host


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class RuntimeConfig:
    """Validated effective runtime configuration.

    Secret fields are excluded from ``repr`` and from :meth:`public_dict`.
    """

    data_dir: Path
    config_path: Path
    backend_host: str
    backend_port: int
    frontend_host: str
    frontend_port: int
    discovery_port: int
    cors_origins: tuple[str, ...]
    models_dir: Path
    fast_model_path: Path
    deep_model_path: Path
    stt_engine: str
    stt_model: str
    stt_device: str
    tts_voice: str
    tts_allow_cloud: bool
    microphone_device: str | None
    browser_path: str | None
    browser_profile_dir: Path
    browser_debug_port: int
    offline: bool
    api_token: str | None = field(default=None, repr=False)
    hf_token: str | None = field(default=None, repr=False)
    picovoice_key: str | None = field(default=None, repr=False)

    @property
    def backend_url(self) -> str:
        return f"http://{_url_host(self.backend_host)}:{self.backend_port}"

    @property
    def frontend_url(self) -> str:
        return f"http://{_url_host(self.frontend_host)}:{self.frontend_port}"

    @property
    def backend_health_url(self) -> str:
        return f"{self.backend_url}/api/health"

    @property
    def backend_docs_url(self) -> str:
        return f"{self.backend_url}/docs"

    @property
    def websocket_url(self) -> str:
        return f"ws://{_url_host(self.backend_host)}:{self.backend_port}/ws"

    @property
    def stt_device_attempts(self) -> tuple[tuple[str, str], ...]:
        """Return ordered faster-whisper device/compute attempts."""

        if self.stt_device == "auto":
            return (
                ("cuda", "int8"),
                ("cuda", "float16"),
                ("cpu", "int8"),
                ("cpu", "float32"),
            )
        if self.stt_device == "cpu":
            return (("cpu", "int8"), ("cpu", "float32"))
        if self.stt_device == "cuda":
            return (("cuda", "int8"), ("cuda", "float16"))
        return ((self.stt_device, "default"),)

    @property
    def run_dir(self) -> Path:
        return self.data_dir / "run"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def memory_db_path(self) -> Path:
        return self.data_dir / "memory.db"

    @property
    def vector_db_path(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def runtime_state_path(self) -> Path:
        return self.run_dir / "runtime.json"

    @property
    def lifecycle_lock_path(self) -> Path:
        return self.run_dir / "lifecycle.lock"

    @property
    def diagnostics_path(self) -> Path:
        return self.data_dir / "diagnostics" / "preflight.json"

    def child_environment(self) -> dict[str, str]:
        """Return inherited child environment with effective settings overlaid.

        Secrets remain environment-only: inherited secret variables are passed
        through but are never copied to configuration, state, or diagnostics.
        """

        environment = dict(os.environ)
        # Remove every supported override first so this validated snapshot is
        # the sole authority even if the parent environment changed after load.
        for name in _ENVIRONMENT_CONTRACT:
            environment.pop(name, None)
        environment.update({
            "OMNI_DATA_DIR": str(self.data_dir),
            "OMNI_BACKEND_HOST": self.backend_host,
            "OMNI_BACKEND_PORT": str(self.backend_port),
            "OMNI_FRONTEND_HOST": self.frontend_host,
            "OMNI_FRONTEND_PORT": str(self.frontend_port),
            "OMNI_DISCOVERY_PORT": str(self.discovery_port),
            "OMNI_BACKEND_URL": self.backend_url,
            "OMNI_CORS_ORIGINS": ",".join(self.cors_origins),
            "OMNI_MODELS_DIR": str(self.models_dir),
            "OMNI_MODEL_PATH": str(self.fast_model_path),
            "OMNI_DEEP_MODEL_PATH": str(self.deep_model_path),
            "OMNI_STT_ENGINE": self.stt_engine,
            "OMNI_STT_MODEL": self.stt_model,
            "OMNI_STT_DEVICE": self.stt_device,
            "OMNI_TTS_VOICE": self.tts_voice,
            "OMNI_TTS_ALLOW_CLOUD": "1" if self.tts_allow_cloud else "0",
            "OMNI_BROWSER_PROFILE_DIR": str(self.browser_profile_dir),
            "OMNI_BROWSER_DEBUG_PORT": str(self.browser_debug_port),
            "OMNI_OFFLINE": "1" if self.offline else "0",
            **(
                {"OMNI_MICROPHONE_DEVICE": self.microphone_device}
                if self.microphone_device is not None
                else {}
            ),
            **({"OMNI_BROWSER_PATH": self.browser_path} if self.browser_path else {}),
        })
        if self.api_token:
            environment["OMNI_API_TOKEN"] = self.api_token
        if self.hf_token:
            environment["HF_TOKEN"] = self.hf_token
        if self.picovoice_key:
            environment["PICOVOICE_ACCESS_KEY"] = self.picovoice_key
        return environment

    def secret_status(self) -> dict[str, bool]:
        """Report only whether each supported secret is configured."""

        return {
            "api_token_configured": bool(self.api_token),
            "hf_token_configured": bool(self.hf_token),
            "picovoice_key_configured": bool(self.picovoice_key),
        }

    def public_dict(self) -> dict[str, Any]:
        """Return diagnostics-safe settings with no secret values."""

        return {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "data_dir": str(self.data_dir),
            "config_path": str(self.config_path),
            "logs_dir": str(self.logs_dir),
            "runtime_state_path": str(self.runtime_state_path),
            "diagnostics_path": str(self.diagnostics_path),
            "backend_host": self.backend_host,
            "backend_port": self.backend_port,
            "backend_url": self.backend_url,
            "frontend_host": self.frontend_host,
            "frontend_port": self.frontend_port,
            "frontend_url": self.frontend_url,
            "discovery_port": self.discovery_port,
            "cors_origins": list(self.cors_origins),
            "models_dir": str(self.models_dir),
            "fast_model_path": str(self.fast_model_path),
            "deep_model_path": str(self.deep_model_path),
            "stt_engine": self.stt_engine,
            "stt_model": self.stt_model,
            "stt_device": self.stt_device,
            "tts_voice": self.tts_voice,
            "tts_allow_cloud": self.tts_allow_cloud,
            "microphone_device": self.microphone_device,
            "browser_path": self.browser_path,
            "browser_profile_dir": str(self.browser_profile_dir),
            "browser_debug_port": self.browser_debug_port,
            "offline_requested": self.offline,
            "offline_enforced": False,
            "secrets": self.secret_status(),
        }


def default_config_document() -> dict[str, Any]:
    """Return the persisted, non-secret default configuration document."""

    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "backend_host": DEFAULT_BACKEND_HOST,
        "backend_port": DEFAULT_BACKEND_PORT,
        "frontend_host": DEFAULT_FRONTEND_HOST,
        "frontend_port": DEFAULT_FRONTEND_PORT,
        "discovery_port": DEFAULT_DISCOVERY_PORT,
        # null keeps the exact local origins derived from frontend_port. Set an
        # explicit non-empty list only when additional trusted origins are needed.
        "cors_origins": None,
        "models_dir": "models",
        "fast_model_path": DEFAULT_FAST_MODEL,
        "deep_model_path": DEFAULT_DEEP_MODEL,
        "stt_engine": DEFAULT_STT_ENGINE,
        "stt_model": DEFAULT_STT_MODEL,
        "stt_device": DEFAULT_STT_DEVICE,
        "tts_voice": DEFAULT_TTS_VOICE,
        "microphone_device": None,
        "browser_path": None,
        "browser_profile_dir": "browser/chrome_profile",
        "browser_debug_port": DEFAULT_BROWSER_DEBUG_PORT,
        "offline": False,
        "tts_allow_cloud": False,
    }


def read_config_document(path: Path) -> dict[str, Any]:
    """Read a JSON object or return an empty mapping when absent."""

    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read valid JSON configuration at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"configuration at {path} must contain a JSON object")
    schema = payload.get("schema_version", CONFIG_SCHEMA_VERSION)
    if schema != CONFIG_SCHEMA_VERSION:
        raise ConfigError(
            f"configuration schema_version must be {CONFIG_SCHEMA_VERSION}; found {schema!r}"
        )
    unknown = sorted(set(payload) - set(default_config_document()))
    if unknown:
        raise ConfigError(
            "configuration contains unsupported key(s): " + ", ".join(unknown)
        )
    return payload


def load_config(
    *,
    environment: Mapping[str, str] | None = None,
    data_dir: Path | None = None,
) -> RuntimeConfig:
    """Load and validate effective configuration without exposing secrets."""

    env = os.environ if environment is None else environment
    resolved_data_dir = (
        Path(data_dir).expanduser().resolve()
        if data_dir is not None
        else get_data_dir(create=False, environment=env)
    )
    config_path = resolved_data_dir / "config.json"
    values = read_config_document(config_path)

    backend_host = _parse_host(
        _value(values, env, "backend_host", "OMNI_BACKEND_HOST", DEFAULT_BACKEND_HOST),
        "backend_host",
    )
    backend_port = _parse_port(
        _value(values, env, "backend_port", "OMNI_BACKEND_PORT", DEFAULT_BACKEND_PORT),
        "backend_port",
    )
    frontend_host = _parse_host(
        _value(values, env, "frontend_host", "OMNI_FRONTEND_HOST", DEFAULT_FRONTEND_HOST),
        "frontend_host",
    )
    frontend_port = _parse_port(
        _value(values, env, "frontend_port", "OMNI_FRONTEND_PORT", DEFAULT_FRONTEND_PORT),
        "frontend_port",
    )
    if backend_port == frontend_port:
        raise ConfigError("backend_port and frontend_port must differ")
    discovery_port = _parse_port(
        _value(values, env, "discovery_port", "OMNI_DISCOVERY_PORT", DEFAULT_DISCOVERY_PORT),
        "discovery_port",
    )

    cors_value: Any = env.get("OMNI_CORS_ORIGINS")
    if cors_value in {None, ""}:
        cors_value = values.get("cors_origins")
    cors_origins = _origins(cors_value, frontend_port)

    models_dir = _resolve_path(
        _value(values, env, "models_dir", "OMNI_MODELS_DIR", "models"),
        resolved_data_dir,
        "models_dir",
    )
    fast_model_path = _resolve_path(
        _value(values, env, "fast_model_path", "OMNI_MODEL_PATH", DEFAULT_FAST_MODEL),
        models_dir,
        "fast_model_path",
    )
    deep_model_path = _resolve_path(
        _value(values, env, "deep_model_path", "OMNI_DEEP_MODEL_PATH", DEFAULT_DEEP_MODEL),
        models_dir,
        "deep_model_path",
    )

    stt_engine = str(
        _value(values, env, "stt_engine", "OMNI_STT_ENGINE", DEFAULT_STT_ENGINE)
    ).strip()
    stt_model = str(
        _value(values, env, "stt_model", "OMNI_STT_MODEL", DEFAULT_STT_MODEL)
    ).strip()
    stt_device = str(
        _value(values, env, "stt_device", "OMNI_STT_DEVICE", DEFAULT_STT_DEVICE)
    ).strip()
    tts_voice = str(
        _value(values, env, "tts_voice", "OMNI_TTS_VOICE", DEFAULT_TTS_VOICE)
    ).strip()
    if not stt_engine:
        raise ConfigError("stt_engine cannot be empty")
    if not stt_model:
        raise ConfigError("stt_model cannot be empty")
    if stt_device not in {"auto", "cpu", "cuda"}:
        raise ConfigError("stt_device must be one of: auto, cpu, cuda")
    if not tts_voice:
        raise ConfigError("tts_voice cannot be empty")
    tts_allow_cloud = _parse_bool(
        _value(values, env, "tts_allow_cloud", "OMNI_TTS_ALLOW_CLOUD", False),
        "tts_allow_cloud",
    )

    microphone_device = _optional_text(
        _value(values, env, "microphone_device", "OMNI_MICROPHONE_DEVICE", None)
    )
    browser_path = _optional_text(
        _value(values, env, "browser_path", "OMNI_BROWSER_PATH", None)
    )
    browser_profile_dir = _resolve_path(
        _value(
            values,
            env,
            "browser_profile_dir",
            "OMNI_BROWSER_PROFILE_DIR",
            "browser/chrome_profile",
        ),
        resolved_data_dir,
        "browser_profile_dir",
    )
    browser_debug_port = _parse_port(
        _value(
            values,
            env,
            "browser_debug_port",
            "OMNI_BROWSER_DEBUG_PORT",
            DEFAULT_BROWSER_DEBUG_PORT,
        ),
        "browser_debug_port",
    )
    if browser_debug_port in {backend_port, frontend_port}:
        raise ConfigError("browser_debug_port must differ from backend_port and frontend_port")
    offline = _parse_bool(
        _value(values, env, "offline", "OMNI_OFFLINE", False),
        "offline",
    )
    if offline and tts_allow_cloud:
        raise ConfigError("offline mode cannot be combined with tts_allow_cloud")

    return RuntimeConfig(
        data_dir=resolved_data_dir,
        config_path=config_path,
        backend_host=backend_host,
        backend_port=backend_port,
        frontend_host=frontend_host,
        frontend_port=frontend_port,
        discovery_port=discovery_port,
        cors_origins=cors_origins,
        models_dir=models_dir,
        fast_model_path=fast_model_path,
        deep_model_path=deep_model_path,
        stt_engine=stt_engine,
        stt_model=stt_model,
        stt_device=stt_device,
        tts_voice=tts_voice,
        tts_allow_cloud=tts_allow_cloud,
        microphone_device=microphone_device,
        browser_path=browser_path,
        browser_profile_dir=browser_profile_dir,
        browser_debug_port=browser_debug_port,
        offline=offline,
        api_token=_optional_text(env.get("OMNI_API_TOKEN")),
        hf_token=_optional_text(env.get("HF_TOKEN") or env.get("HUGGINGFACE_TOKEN")),
        picovoice_key=_optional_text(
            env.get("PICOVOICE_ACCESS_KEY")
            or env.get("PICOVOICE_KEY")
            or env.get("PORCUPINE_KEY")
        ),
    )


def write_default_config(*, data_dir: Path | None = None) -> tuple[Path, bool]:
    """Create the default config atomically, preserving any existing file.

    Returns ``(path, created)``. Existing valid configuration is never changed.
    """

    root = Path(data_dir).expanduser().resolve() if data_dir else get_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "config.json"
    if path.exists():
        read_config_document(path)
        return path, False

    document = default_config_document()
    descriptor, temporary_name = tempfile.mkstemp(prefix="config.", suffix=".tmp", dir=root)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        try:
            os.link(temporary, path)
        except FileExistsError:
            read_config_document(path)
            return path, False
        except OSError as exc:
            raise ConfigError(f"cannot atomically create configuration at {path}: {exc}") from exc
        try:
            path.chmod(0o600)
        except OSError:
            pass
    finally:
        temporary.unlink(missing_ok=True)
    return path, True
