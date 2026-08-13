"""Owned, restartable process lifecycle for the OMNI source-checkout runtime."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import psutil

from omni_v2.core.config import RuntimeConfig, load_config
from omni_v2.core.preflight import PreflightReport, run_preflight, write_json_report

_STATE_SCHEMA_VERSION = 1
_CREATE_TIME_TOLERANCE = 0.05


class LifecycleError(RuntimeError):
    """Raised when a lifecycle operation cannot complete safely."""


@dataclass(frozen=True)
class ServiceState:
    """Persisted ownership identity for one service process."""

    name: str
    pid: int
    create_time: float
    executable: str
    command: tuple[str, ...]
    working_directory: str
    log_path: str
    url: str


@dataclass(frozen=True)
class RuntimeState:
    """Atomic state describing one managed runtime generation."""

    schema_version: int
    run_id: str
    created_at: str
    repository_root: str
    services: tuple[ServiceState, ...]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["services"] = [asdict(item) for item in self.services]
        return result


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    status: str
    pid: int | None
    url: str
    detail: str


@dataclass(frozen=True)
class LifecycleResult:
    operation: str
    ok: bool
    run_id: str | None
    services: tuple[ServiceStatus, ...]
    diagnostics_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "ok": self.ok,
            "run_id": self.run_id,
            "diagnostics_path": self.diagnostics_path,
            "services": [asdict(item) for item in self.services],
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, content: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _lock_owner_is_active(path: Path) -> bool:
    """Conservatively verify the PID/create-time identity stored in a lock."""

    try:
        pid_text, created_text = path.read_text(encoding="utf-8").split()
        process = psutil.Process(int(pid_text))
        return abs(process.create_time() - float(created_text)) <= _CREATE_TIME_TOLERANCE
    except (FileNotFoundError, psutil.NoSuchProcess):
        return False
    except (OSError, ValueError, psutil.AccessDenied):
        # An unreadable or unverifiable lock must never be broken automatically.
        return True


@contextmanager
def _operation_lock(path: Path) -> Iterator[None]:
    """Serialize lifecycle mutations using a PID/create-time-owned lock."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        owner = "active" if _lock_owner_is_active(path) else "not active or unverifiable"
        raise LifecycleError(
            f"Another OMNI lifecycle operation owns {path} (owner is {owner}). "
            "Wait for it to finish. If its process crashed, inspect the lock and runtime status "
            "before manually removing the lock; OMNI will not break it automatically."
        ) from None
    try:
        created_at = psutil.Process(os.getpid()).create_time()
        os.write(descriptor, f"{os.getpid()} {created_at:.6f}\n".encode())
    finally:
        os.close(descriptor)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _load_state(path: Path) -> RuntimeState | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("schema_version") != _STATE_SCHEMA_VERSION:
            raise ValueError("unsupported schema version")
        services = tuple(
            ServiceState(
                name=str(item["name"]),
                pid=int(item["pid"]),
                create_time=float(item["create_time"]),
                executable=str(item["executable"]),
                command=tuple(str(part) for part in item["command"]),
                working_directory=str(item["working_directory"]),
                log_path=str(item["log_path"]),
                url=str(item["url"]),
            )
            for item in raw["services"]
        )
        return RuntimeState(
            schema_version=int(raw["schema_version"]),
            run_id=str(raw["run_id"]),
            created_at=str(raw["created_at"]),
            repository_root=str(raw["repository_root"]),
            services=services,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise LifecycleError(
            f"Runtime state {path} is invalid: {exc}. "
            "Inspect it before deleting it; OMNI will not guess process ownership."
        ) from exc


def _same_executable(actual: str, expected: str) -> bool:
    try:
        return Path(actual).resolve() == Path(expected).resolve()
    except OSError:
        return os.path.normcase(actual) == os.path.normcase(expected)


def _owned_process(service: ServiceState) -> tuple[psutil.Process | None, str]:
    """Return a process only after PID, creation time, and executable agree."""

    try:
        process = psutil.Process(service.pid)
        actual_time = process.create_time()
        actual_executable = process.exe()
    except psutil.NoSuchProcess:
        return None, "process is not running"
    except (psutil.AccessDenied, OSError) as exc:
        return None, f"process ownership could not be verified: {exc}"
    if abs(actual_time - service.create_time) > _CREATE_TIME_TOLERANCE:
        return None, "PID was reused by another process (creation time mismatch)"
    if not _same_executable(actual_executable, service.executable):
        return None, "PID belongs to another executable"
    return process, "PID, creation time, and executable match managed state"


def _service_readiness(service: ServiceState, timeout: float = 1.0) -> tuple[bool, str]:
    expected: dict[str, object] = {
        "status": "ok",
        "qualification": "experimental_not_release_qualified",
    }
    if service.name == "frontend":
        expected["nextjs"] = True
    elif service.name != "backend":
        return False, f"unknown managed service identity {service.name!r}"
    url = f"{service.url.rstrip('/')}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read())
    except (json.JSONDecodeError, urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"readiness probe failed at {url}: {exc}"
    if response.status != 200 or not isinstance(payload, dict):
        return False, f"readiness probe at {url} returned HTTP {response.status} or a non-object payload"
    mismatched = [key for key, value in expected.items() if payload.get(key) != value]
    if mismatched:
        return False, f"readiness probe at {url} had unexpected field(s): {', '.join(mismatched)}"
    return True, f"readiness identity verified at {url}"


def _state_status(state: RuntimeState | None, config: RuntimeConfig) -> tuple[ServiceStatus, ...]:
    if state is None:
        return (
            ServiceStatus("backend", "stopped", None, config.backend_url, "No managed runtime state."),
            ServiceStatus("frontend", "stopped", None, config.frontend_url, "No managed runtime state."),
        )
    results = []
    for service in state.services:
        process, detail = _owned_process(service)
        unverified = detail.startswith("process ownership could not be verified")
        service_status = "unverified" if unverified else "stale"
        if process is not None:
            ready, readiness_detail = _service_readiness(service)
            service_status = "running" if ready else "unhealthy"
            detail = f"{detail}; {readiness_detail}"
        results.append(
            ServiceStatus(
                service.name,
                service_status,
                service.pid,
                service.url,
                detail,
            )
        )
    return tuple(results)


def status(config: RuntimeConfig | None = None) -> LifecycleResult:
    """Inspect managed state without mutating or signaling any process."""

    config = config or load_config()
    state = _load_state(config.runtime_state_path)
    services = _state_status(state, config)
    return LifecycleResult(
        operation="status",
        ok=bool(state) and all(item.status == "running" for item in services),
        run_id=state.run_id if state else None,
        services=services,
    )


def _wait_for_http(
    url: str,
    process: psutil.Process,
    timeout: float,
    expected: Mapping[str, object],
) -> None:
    """Wait for an owned process to return the expected OMNI identity payload."""

    deadline = time.monotonic() + timeout
    error = "no response"
    while time.monotonic() < deadline:
        if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
            raise LifecycleError(f"Process {process.pid} exited before {url} became ready")
        try:
            with urllib.request.urlopen(url, timeout=min(2.0, timeout)) as response:
                payload = json.loads(response.read())
                if response.status == 200 and isinstance(payload, dict) and all(
                    payload.get(key) == value for key, value in expected.items()
                ):
                    return
                error = f"HTTP {response.status} returned an unexpected readiness payload"
        except (json.JSONDecodeError, urllib.error.URLError, TimeoutError, OSError) as exc:
            error = str(exc)
        time.sleep(0.2)
    raise LifecycleError(f"Timed out after {timeout:.1f}s waiting for {url}: {error}")


def _spawn(
    *,
    name: str,
    command: Sequence[str],
    cwd: Path,
    environment: dict[str, str],
    log_path: Path,
    url: str,
) -> tuple[ServiceState, psutil.Process]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creation_flags = 0
    popen_options: dict[str, object] = {}
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        popen_options["start_new_session"] = True
    with log_path.open("ab", buffering=0) as log_file:
        log_file.write(f"\n--- {name} start {_utc_now()} ---\n".encode())
        child = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            **popen_options,
        )
    process = psutil.Process(child.pid)
    try:
        create_time = process.create_time()
        executable = process.exe()
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as exc:
        raise LifecycleError(f"{name} process exited during launch: {exc}") from exc
    service = ServiceState(
        name=name,
        pid=child.pid,
        create_time=create_time,
        executable=executable,
        command=tuple(str(part) for part in command),
        working_directory=str(cwd.resolve()),
        log_path=str(log_path.resolve()),
        url=url,
    )
    return service, process


def _save_generation(
    config: RuntimeConfig,
    run_id: str,
    repository_root: Path,
    services: Sequence[ServiceState],
) -> RuntimeState:
    state = RuntimeState(
        schema_version=_STATE_SCHEMA_VERSION,
        run_id=run_id,
        created_at=_utc_now(),
        repository_root=str(repository_root.resolve()),
        services=tuple(services),
    )
    _atomic_json(config.runtime_state_path, state.to_dict())
    return state


def _tail(path: Path, lines: int = 30) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError as exc:
        return f"Could not read log: {exc}"


def _terminate_service(service: ServiceState, timeout: float) -> ServiceStatus:
    process, detail = _owned_process(service)
    if process is None:
        status = "failed" if detail.startswith("process ownership could not be verified") else "stale"
        return ServiceStatus(service.name, status, service.pid, service.url, detail)

    try:
        descendants = process.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        descendants = []
    targets = descendants + [process]
    for target in targets:
        try:
            target.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(targets, timeout=timeout)
    for target in alive:
        try:
            target.kill()
        except psutil.NoSuchProcess:
            pass
    _, still_alive = psutil.wait_procs(alive, timeout=min(timeout, 3.0))
    if still_alive:
        pids = ", ".join(str(item.pid) for item in still_alive)
        return ServiceStatus(
            service.name,
            "failed",
            service.pid,
            service.url,
            f"Owned process tree still contains PID(s): {pids}",
        )
    return ServiceStatus(service.name, "stopped", service.pid, service.url, detail)


def _stop_unlocked(config: RuntimeConfig, timeout: float) -> LifecycleResult:
    state = _load_state(config.runtime_state_path)
    if state is None:
        return LifecycleResult("stop", True, None, _state_status(None, config))
    results = tuple(_terminate_service(item, timeout) for item in reversed(state.services))
    unsafe = any(item.status == "failed" for item in results)
    if not unsafe:
        config.runtime_state_path.unlink(missing_ok=True)
    return LifecycleResult("stop", not unsafe, state.run_id, results)


def stop(config: RuntimeConfig | None = None, timeout: float = 10.0) -> LifecycleResult:
    """Stop only processes whose persisted ownership identity still matches."""

    config = config or load_config()
    with _operation_lock(config.lifecycle_lock_path):
        return _stop_unlocked(config, timeout)


def _repository_root(path: Path | None) -> Path:
    root = (path or Path(__file__).resolve().parents[2]).resolve()
    if not (root / "backend_fastapi" / "main.py").is_file():
        raise LifecycleError(f"Backend source checkout was not found at {root}")
    return root


def _assert_clean_start(config: RuntimeConfig) -> None:
    state = _load_state(config.runtime_state_path)
    if state is None:
        return
    statuses = _state_status(state, config)
    if any(item.status in {"running", "unhealthy", "unverified"} for item in statuses):
        details = ", ".join(
            f"{item.name} PID {item.pid} ({item.status})" for item in statuses
        )
        raise LifecycleError(
            f"Existing runtime ownership blocks startup ({details}). Use status and stop first."
        )
    config.runtime_state_path.unlink(missing_ok=True)


def _preflight_or_raise(
    config: RuntimeConfig,
    root: Path,
    require_frontend: bool,
) -> PreflightReport:
    report = run_preflight(
        require_primary=False,
        require_frontend=require_frontend,
        repository_root=root,
        config=config,
    )
    write_json_report(report, config.diagnostics_path)
    if not report.ok:
        failures = "; ".join(
            f"{item.code}: {item.summary}" for item in report.checks if item.status == "fail"
        )
        raise LifecycleError(f"Preflight blocked startup: {failures}")
    return report


def _start_unlocked(
    *,
    config: RuntimeConfig,
    repository_root: Path,
    include_frontend: bool,
    timeout: float,
    preflight: bool,
) -> LifecycleResult:
    _assert_clean_start(config)
    if preflight:
        _preflight_or_raise(config, repository_root, include_frontend)

    environment = config.child_environment()
    environment["PYTHONUNBUFFERED"] = "1"
    environment["PYTHONPATH"] = str(repository_root) + os.pathsep + environment.get("PYTHONPATH", "")
    run_id = str(uuid.uuid4())
    services: list[ServiceState] = []
    backend_log = config.logs_dir / "backend.log"
    frontend_log = config.logs_dir / "frontend.log"

    try:
        backend_command = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend_fastapi.main:app",
            "--host",
            config.backend_host,
            "--port",
            str(config.backend_port),
            "--no-access-log",
        ]
        backend, backend_process = _spawn(
            name="backend",
            command=backend_command,
            cwd=repository_root,
            environment=environment,
            log_path=backend_log,
            url=config.backend_url,
        )
        services.append(backend)
        _save_generation(config, run_id, repository_root, services)
        _wait_for_http(
            config.backend_health_url,
            backend_process,
            timeout,
            {
                "status": "ok",
                "qualification": "experimental_not_release_qualified",
            },
        )

        if include_frontend:
            node = shutil.which("node")
            frontend_server = repository_root / "frontend_next" / "server.js"
            if node is None or not frontend_server.is_file():
                raise LifecycleError("Frontend runtime is missing; run the documented installer first")
            frontend_command = [node, str(frontend_server)]
            frontend, frontend_process = _spawn(
                name="frontend",
                command=frontend_command,
                cwd=repository_root / "frontend_next",
                environment=environment,
                log_path=frontend_log,
                url=config.frontend_url,
            )
            services.append(frontend)
            _save_generation(config, run_id, repository_root, services)
            _wait_for_http(
                f"{config.frontend_url}/api/health",
                frontend_process,
                timeout,
                {
                    "status": "ok",
                    "qualification": "experimental_not_release_qualified",
                    "nextjs": True,
                },
            )
    except Exception as exc:
        cleanup = [
            _terminate_service(service, min(timeout, 5.0))
            for service in reversed(services)
        ]
        cleanup_failed = any(item.status == "failed" for item in cleanup)
        if not cleanup_failed:
            config.runtime_state_path.unlink(missing_ok=True)
        logs = []
        for name, path in (("backend", backend_log), ("frontend", frontend_log)):
            if path.exists():
                logs.append(f"--- {name} log ---\n{_tail(path)}")
        if cleanup_failed:
            logs.append(
                "Cleanup failed; persisted state was retained to prevent unsafe PID reuse handling: "
                + "; ".join(item.detail for item in cleanup if item.status == "failed")
            )
        context = "\n".join(logs)
        raise LifecycleError(f"Startup failed: {exc}\n{context}".rstrip()) from exc

    state = _save_generation(config, run_id, repository_root, services)
    statuses = _state_status(state, config)
    return LifecycleResult(
        "start",
        all(item.status == "running" for item in statuses),
        run_id,
        statuses,
        str(config.diagnostics_path),
    )


def start(
    *,
    config: RuntimeConfig | None = None,
    repository_root: Path | None = None,
    include_frontend: bool = True,
    timeout: float = 45.0,
    preflight: bool = True,
) -> LifecycleResult:
    """Start a new owned runtime and wait for bounded HTTP readiness."""

    config = config or load_config()
    root = _repository_root(repository_root)
    with _operation_lock(config.lifecycle_lock_path):
        return _start_unlocked(
            config=config,
            repository_root=root,
            include_frontend=include_frontend,
            timeout=timeout,
            preflight=preflight,
        )


def restart(
    *,
    config: RuntimeConfig | None = None,
    repository_root: Path | None = None,
    include_frontend: bool = True,
    timeout: float = 45.0,
    preflight: bool = True,
) -> LifecycleResult:
    """Stop the owned generation, then start and qualify a fresh generation."""

    config = config or load_config()
    root = _repository_root(repository_root)
    with _operation_lock(config.lifecycle_lock_path):
        stopped = _stop_unlocked(config, min(timeout, 10.0))
        if not stopped.ok:
            raise LifecycleError("Restart refused because the previous process tree did not stop cleanly")
        result = _start_unlocked(
            config=config,
            repository_root=root,
            include_frontend=include_frontend,
            timeout=timeout,
            preflight=preflight,
        )
        return LifecycleResult(
            "restart",
            result.ok,
            result.run_id,
            result.services,
            result.diagnostics_path,
        )
