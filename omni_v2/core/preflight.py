"""Truthful, side-effect-light installation and startup diagnostics."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from omni_v2.core.config import ConfigError, RuntimeConfig, load_config


@dataclass(frozen=True)
class CheckResult:
    """One deterministic preflight result."""

    code: str
    status: str
    summary: str
    detail: str
    remediation: str | None = None


@dataclass(frozen=True)
class PreflightReport:
    """Serializable preflight report with explicit failure semantics."""

    schema_version: int
    platform: str
    architecture: str
    python: str
    configuration: dict[str, object] | None
    checks: tuple[CheckResult, ...]

    @property
    def ok(self) -> bool:
        return not any(item.status == "fail" for item in self.checks)

    @property
    def counts(self) -> dict[str, int]:
        return {
            status: sum(item.status == status for item in self.checks)
            for status in ("pass", "warn", "fail")
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "ok": self.ok,
            "platform": self.platform,
            "architecture": self.architecture,
            "python": self.python,
            "configuration": self.configuration,
            "counts": self.counts,
            "checks": [asdict(item) for item in self.checks],
        }


def _result(
    code: str,
    status: str,
    summary: str,
    detail: str,
    remediation: str | None = None,
) -> CheckResult:
    return CheckResult(code, status, summary, detail, remediation)


def _windows_version() -> tuple[int | None, int | None]:
    """Return (build, product_type) without treating Windows Server as Windows 11."""

    if platform.system() != "Windows":
        return None, None
    get_version = getattr(sys, "getwindowsversion", None)
    if get_version is not None:
        try:
            version = get_version()
            return int(version.build), int(version.product_type)
        except (AttributeError, TypeError, ValueError):
            pass
    try:
        return int(platform.version().split(".")[-1]), None
    except (ValueError, IndexError):
        return None, None


def _platform_check(require_primary: bool) -> CheckResult:
    system = platform.system()
    machine = platform.machine().lower()
    is_x64 = machine in {"amd64", "x86_64"}
    build, product_type = _windows_version()
    is_workstation = product_type == 1
    is_windows_11 = (
        system == "Windows"
        and build is not None
        and build >= 22000
        and is_workstation
    )
    if is_windows_11 and is_x64:
        return _result(
            "platform.primary",
            "pass",
            "Windows 11 x64 workstation detected",
            (
                f"Windows build {build}; product type {product_type} (workstation); "
                f"architecture {platform.machine()}."
            ),
        )
    status = "fail" if require_primary else "warn"
    if system == "Windows" and product_type in {2, 3}:
        summary = "Windows Server is not a supported product platform"
        detail = (
            f"Detected Windows build {build}, product type {product_type}, "
            f"architecture {platform.machine()}. Windows Server and domain-controller "
            "products are not Windows 11 workstation qualification hosts."
        )
    elif system == "Windows" and product_type is None:
        summary = "Windows workstation product type could not be verified"
        detail = (
            f"Detected Windows build {build}, architecture {platform.machine()}, but the "
            "operating-system product type was unavailable. A build number alone cannot "
            "distinguish Windows 11 from Windows Server."
        )
    else:
        summary = "Primary product platform not detected"
        detail = (
            f"Detected {system} {platform.release()} ({platform.machine()}). "
            "Linux is a development environment only; macOS is unsupported and unverified."
        )
    return _result(
        "platform.primary",
        status,
        summary,
        detail,
        "Run product qualification on Windows 11 x64 workstation; use this platform only for development checks.",
    )


def _python_check(require_x64: bool) -> CheckResult:
    implementation = platform.python_implementation()
    machine = platform.machine().lower()
    pointer_bits = 64 if sys.maxsize > 2**32 else 32
    exact_version = implementation == "CPython" and sys.version_info[:2] == (3, 11)
    native_x64 = pointer_bits == 64 and machine in {"amd64", "x86_64"}
    compatible = exact_version and (native_x64 or not require_x64)
    if compatible:
        summary = "CPython 3.11 x64 detected" if require_x64 else "CPython 3.11 detected"
    else:
        summary = "Unsupported Python interpreter"
    return _result(
        "python.version",
        "pass" if compatible else "fail",
        summary,
        (
            f"{implementation} {platform.python_version()} ({pointer_bits}-bit, "
            f"{platform.machine()}) at {sys.executable}."
        ),
        None if compatible else "Install native x64 CPython 3.11; OMNI requires >=3.11,<3.12.",
    )


def _config_check(config: RuntimeConfig | None, error: str | None) -> CheckResult:
    if config is None:
        return _result(
            "config.valid",
            "fail",
            "Configuration is invalid",
            error or "Unknown configuration error.",
            "Fix the named value in <data-dir>/config.json or its OMNI_* override.",
        )
    return _result(
        "config.valid",
        "pass",
        "Configuration contract is valid",
        f"Loaded {config.config_path}; environment overrides take precedence.",
    )


def _writable_check(config: RuntimeConfig | None) -> CheckResult:
    if config is None:
        return _result(
            "paths.writable",
            "fail",
            "Writable paths could not be checked",
            "Configuration must be valid before paths can be resolved.",
        )
    try:
        config.data_dir.mkdir(parents=True, exist_ok=True)
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix="preflight.", dir=config.data_dir)
        os.close(descriptor)
        Path(name).unlink()
    except OSError as exc:
        return _result(
            "paths.writable",
            "fail",
            "Data directory is not writable",
            f"{config.data_dir}: {exc}",
            "Choose a writable OMNI_DATA_DIR and retry.",
        )
    return _result(
        "paths.writable",
        "pass",
        "Runtime paths are writable",
        f"Data: {config.data_dir}; logs: {config.logs_dir}; models: {config.models_dir}.",
    )


def _dependency_check(module: str, code: str, required: bool, remediation: str) -> CheckResult:
    available = importlib.util.find_spec(module) is not None
    status = "pass" if available else ("fail" if required else "warn")
    return _result(
        code,
        status,
        f"{module} is available" if available else f"{module} is unavailable",
        "Import metadata was found." if available else "No import metadata was found in this environment.",
        None if available else remediation,
    )


def _port_check(config: RuntimeConfig | None, frontend: bool) -> CheckResult:
    role = "frontend" if frontend else "backend"
    if config is None:
        return _result(
            f"port.{role}",
            "fail",
            f"{role.title()} port could not be checked",
            "Configuration is invalid.",
        )
    host = config.frontend_host if frontend else config.backend_host
    port = config.frontend_port if frontend else config.backend_port
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    probe_host = "::" if host in {"::", "[::]"} else host
    try:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((probe_host, port))
    except OSError as exc:
        return _result(
            f"port.{role}",
            "warn",
            f"{role.title()} port {port} is already in use",
            f"Could not bind {host}:{port}: {exc}. This is expected only when OMNI is already running.",
            "Run the OMNI status command; stop the conflicting process or choose another configured port.",
        )
    return _result(
        f"port.{role}",
        "pass",
        f"{role.title()} port {port} is available",
        f"A temporary bind to {host}:{port} succeeded.",
    )


def _model_check(config: RuntimeConfig | None) -> CheckResult:
    if config is None:
        return _result("model.fast", "fail", "Model path is unknown", "Configuration is invalid.")
    path = config.fast_model_path
    if path.is_file() and path.stat().st_size > 0:
        return _result(
            "model.fast",
            "pass",
            "Configured local model is present",
            f"{path} ({path.stat().st_size} bytes).",
        )
    return _result(
        "model.fast",
        "warn",
        "Configured local model is missing",
        f"Expected a non-empty GGUF at {path}. The API can start, but LLM-dependent work is unavailable.",
        "Run `omni model download` when network access is permitted, or set OMNI_MODEL_PATH.",
    )


def _microphone_check(config: RuntimeConfig | None) -> CheckResult:
    if importlib.util.find_spec("sounddevice") is None:
        return _result(
            "microphone.input",
            "warn",
            "Microphone support is not installed",
            "The sounddevice module is absent; voice input is unavailable.",
            "Install the qualified voice profile before attempting microphone workflows.",
        )
    try:
        import sounddevice  # type: ignore[import-not-found]

        devices = sounddevice.query_devices()
        inputs = [item for item in devices if int(item.get("max_input_channels", 0)) > 0]
    except Exception as exc:  # noqa: BLE001 - hardware backends raise vendor-specific errors
        return _result(
            "microphone.input",
            "warn",
            "Microphone enumeration failed",
            f"sounddevice is installed but input devices could not be queried: {exc}",
            "Check Windows microphone privacy permission, the selected device, and the audio driver.",
        )
    configured = config.microphone_device if config else None
    if not inputs:
        return _result(
            "microphone.input",
            "warn",
            "No microphone input device was found",
            "sounddevice reported zero devices with input channels.",
            "Connect and enable a microphone, then grant Windows microphone permission.",
        )
    return _result(
        "microphone.input",
        "pass",
        "Microphone input is discoverable",
        f"Found {len(inputs)} input device(s); configured preference: {configured or 'automatic'}.",
    )


def _browser_candidates(config: RuntimeConfig | None) -> list[Path]:
    candidates: list[Path] = []
    if config and config.browser_path:
        candidates.append(Path(config.browser_path).expanduser())
    for command in ("msedge", "msedge.exe", "chrome", "chrome.exe", "chromium", "chromium-browser"):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))
    if os.name == "nt":
        for base_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(base_name)
            if not base:
                continue
            candidates.extend(
                [
                    Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe",
                ]
            )
    return candidates


def _browser_check(config: RuntimeConfig | None) -> CheckResult:
    found = next((path for path in _browser_candidates(config) if path.is_file()), None)
    if found:
        return _result(
            "browser.executable",
            "pass",
            "A supported browser executable was found",
            str(found.resolve()),
        )
    return _result(
        "browser.executable",
        "warn",
        "No Chrome or Edge executable was found",
        "OMNI may still open the operating-system default browser, but isolated-profile automation is unavailable.",
        "Install Microsoft Edge or Google Chrome, or set OMNI_BROWSER_PATH.",
    )


def _frontend_check(repository_root: Path | None, require_frontend: bool) -> list[CheckResult]:
    status_if_missing = "fail" if require_frontend else "warn"
    node = shutil.which("node")
    node_version = ""
    node_compatible = False
    if node:
        try:
            node_version = subprocess.run(
                [node, "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip().lstrip("v")
            parts = tuple(int(part) for part in node_version.split("."))
            node_compatible = len(parts) == 3 and parts[0] == 22 and parts >= (22, 22, 2)
        except (OSError, ValueError, subprocess.SubprocessError):
            node_compatible = False
    checks = [
        _result(
            "frontend.node",
            "pass" if node_compatible else status_if_missing,
            (
                "Compatible Node.js runtime found"
                if node_compatible
                else ("Node.js runtime is incompatible" if node else "Node.js executable not found")
            ),
            (
                f"Node.js {node_version or 'unknown'} at {node}."
                if node
                else "node is not on PATH."
            ),
            (
                None
                if node_compatible
                else "Install Node.js >=22.22.2,<23 for the Next.js interface."
            ),
        )
    ]
    if repository_root is None:
        checks.append(
            _result(
                "frontend.build",
                status_if_missing,
                "Frontend checkout could not be located",
                "Installed Python packages do not include the source-only Next.js application.",
                "Run the primary launcher from a complete OMNI source checkout.",
            )
        )
        return checks
    frontend = repository_root / "frontend_next"
    build_id = frontend / ".next" / "BUILD_ID"
    next_cli = frontend / "node_modules" / "next" / "dist" / "bin" / "next"
    frontend_server = frontend / "server.js"
    ready = build_id.is_file() and next_cli.is_file() and frontend_server.is_file()
    checks.append(
        _result(
            "frontend.build",
            "pass" if ready else status_if_missing,
            "Frontend production build is ready" if ready else "Frontend production build is missing",
            f"Expected {build_id}, {next_cli}, and {frontend_server}.",
            None if ready else "Run the documented installer to perform npm ci and npm run build.",
        )
    )
    return checks


def _offline_check(config: RuntimeConfig | None) -> CheckResult:
    if config is None or not config.offline:
        return _result(
            "offline.request",
            "pass",
            "Offline mode is not requested",
            "Network-capable optional features remain configuration-dependent.",
        )
    return _result(
        "offline.request",
        "warn",
        "Offline behavior is requested but not yet enforced",
        "OMNI_OFFLINE/config offline is centralized, but B15 no-egress enforcement has not passed.",
        "Do not treat this setting as a network sandbox until B15 closes.",
    )


def run_preflight(
    *,
    require_primary: bool = False,
    require_frontend: bool = False,
    repository_root: Path | None = None,
    config: RuntimeConfig | None = None,
) -> PreflightReport:
    """Run installation/startup checks without starting OMNI."""

    config_error = None
    if config is None:
        try:
            config = load_config()
        except ConfigError as exc:
            config_error = str(exc)

    checks: list[CheckResult] = [
        _platform_check(require_primary),
        _python_check(require_primary),
        _config_check(config, config_error),
        _writable_check(config),
        _dependency_check(
            "fastapi",
            "dependency.fastapi",
            True,
            "Run the documented core-profile installer.",
        ),
        _dependency_check(
            "uvicorn",
            "dependency.uvicorn",
            True,
            "Run the documented core-profile installer.",
        ),
        _port_check(config, False),
        _port_check(config, True),
        _model_check(config),
        _microphone_check(config),
        _browser_check(config),
        _offline_check(config),
    ]
    checks.extend(_frontend_check(repository_root, require_frontend))
    for module, code, remediation in (
        ("llama_cpp", "optional.llama_cpp", "Install the all profile before using a local GGUF model."),
        ("faster_whisper", "optional.faster_whisper", "Install the voice profile before local STT."),
        ("cv2", "optional.opencv", "Install the vision profile before camera/security workflows."),
    ):
        checks.append(_dependency_check(module, code, False, remediation))

    return PreflightReport(
        schema_version=1,
        platform=platform.platform(),
        architecture=platform.machine(),
        python=platform.python_version(),
        configuration=config.public_dict() if config else None,
        checks=tuple(checks),
    )


def render_report(report: PreflightReport, write: Callable[[str], None] = print) -> None:
    """Render a compact human-readable report."""

    icons = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
    write("OMNI preflight")
    write(f"Platform: {report.platform} ({report.architecture})")
    write(f"Python:   {report.python}")
    for item in report.checks:
        write(f"[{icons[item.status]}] {item.code}: {item.summary}")
        write(f"       {item.detail}")
        if item.remediation:
            write(f"       Fix: {item.remediation}")
    counts = report.counts
    write(
        f"Result: {'READY' if report.ok else 'BLOCKED'} "
        f"({counts['pass']} pass, {counts['warn']} warning, {counts['fail']} fail)"
    )


def write_json_report(report: PreflightReport, path: Path) -> None:
    """Write diagnostics atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
