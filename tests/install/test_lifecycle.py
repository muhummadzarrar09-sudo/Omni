from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import psutil
import pytest

from omni_v2.core.config import load_config
from omni_v2.core.lifecycle import (
    LifecycleError,
    RuntimeState,
    ServiceState,
    _operation_lock,
    _terminate_service,
    _utc_now,
    _wait_for_http,
    status,
    stop,
)


def _service_for(process: psutil.Process, working_directory: Path) -> ServiceState:
    return ServiceState(
        name="test-service",
        pid=process.pid,
        create_time=process.create_time(),
        executable=process.exe(),
        command=tuple(process.cmdline()),
        working_directory=str(working_directory),
        log_path=str(working_directory / "test.log"),
        url="http://127.0.0.1:1",
    )


def _write_state(path: Path, repository: Path, service: ServiceState) -> None:
    state = RuntimeState(
        schema_version=1,
        run_id="test-generation",
        created_at=_utc_now(),
        repository_root=str(repository),
        services=(service,),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict()), encoding="utf-8")


def test_stop_terminates_only_a_matching_owned_process_tree(tmp_path: Path) -> None:
    parent = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import subprocess,sys,time; "
                "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
                "time.sleep(60)"
            ),
        ],
        cwd=tmp_path,
    )
    process = psutil.Process(parent.pid)
    try:
        deadline = time.monotonic() + 5
        descendants: list[psutil.Process] = []
        while time.monotonic() < deadline and not descendants:
            descendants = process.children(recursive=True)
            time.sleep(0.05)
        assert descendants, "test child process did not start"

        result = _terminate_service(_service_for(process, tmp_path), timeout=2)

        assert result.status == "stopped"
        assert not process.is_running()
        assert all(not child.is_running() for child in descendants)
    finally:
        try:
            remaining = process.children(recursive=True)
        except psutil.NoSuchProcess:
            remaining = []
        for candidate in [*remaining, process]:
            try:
                candidate.kill()
            except psutil.Error:
                pass
        parent.wait(timeout=5)


def test_stop_refuses_to_signal_a_process_when_identity_does_not_match(tmp_path: Path) -> None:
    parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], cwd=tmp_path)
    process = psutil.Process(parent.pid)
    try:
        service = _service_for(process, tmp_path)
        mismatched = ServiceState(
            **{**service.__dict__, "create_time": service.create_time - 10.0}
        )
        config = load_config(environment={"OMNI_DATA_DIR": str(tmp_path / "data")})
        _write_state(config.runtime_state_path, tmp_path, mismatched)

        result = stop(config=config, timeout=0.1)

        assert result.ok is True
        assert result.services[0].status == "stale"
        assert process.is_running()
        assert not config.runtime_state_path.exists()
    finally:
        parent.terminate()
        parent.wait(timeout=5)


def test_status_rejects_invalid_state_instead_of_guessing_ownership(tmp_path: Path) -> None:
    config = load_config(environment={"OMNI_DATA_DIR": str(tmp_path)})
    config.runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    config.runtime_state_path.write_text('{"schema_version": 999}', encoding="utf-8")

    with pytest.raises(LifecycleError, match="invalid"):
        status(config)


def test_operation_lock_serializes_lifecycle_mutations(tmp_path: Path) -> None:
    lock = tmp_path / "operation.lock"
    with (
        _operation_lock(lock),
        pytest.raises(LifecycleError, match="Another OMNI lifecycle operation"),
        _operation_lock(lock),
    ):
        pass
    assert not lock.exists()


def test_operation_lock_never_auto_breaks_an_orphaned_identity(tmp_path: Path) -> None:
    lock = tmp_path / "operation.lock"
    lock.write_text(f"{psutil.Process().pid} 1.0\n", encoding="utf-8")

    with (
        pytest.raises(LifecycleError, match="will not break it automatically"),
        _operation_lock(lock),
    ):
        pass

    assert lock.exists()


def test_status_marks_an_owned_but_unready_process_unhealthy(tmp_path: Path) -> None:
    parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], cwd=tmp_path)
    process = psutil.Process(parent.pid)
    config = load_config(environment={"OMNI_DATA_DIR": str(tmp_path / "data")})
    try:
        service = _service_for(process, tmp_path)
        backend = ServiceState(**{**service.__dict__, "name": "backend"})
        _write_state(config.runtime_state_path, tmp_path, backend)

        result = status(config)

        assert result.ok is False
        assert result.services[0].status == "unhealthy"
        assert "readiness probe failed" in result.services[0].detail
    finally:
        parent.terminate()
        parent.wait(timeout=5)


def test_readiness_rejects_an_unrelated_http_service(tmp_path: Path) -> None:
    script = (
        "from http.server import BaseHTTPRequestHandler,HTTPServer\n"
        "class Handler(BaseHTTPRequestHandler):\n"
        " def do_GET(self):\n"
        "  body=b'{\"status\":\"ok\"}'\n"
        "  self.send_response(200); self.end_headers(); self.wfile.write(body)\n"
        " def log_message(self,*args): pass\n"
        "server=HTTPServer(('127.0.0.1',0),Handler)\n"
        "print(server.server_port,flush=True)\n"
        "server.serve_forever()\n"
    )
    parent = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        text=True,
    )
    process = psutil.Process(parent.pid)
    try:
        assert parent.stdout is not None
        port = int(parent.stdout.readline().strip())
        with pytest.raises(LifecycleError, match="unexpected readiness payload"):
            _wait_for_http(
                f"http://127.0.0.1:{port}/api/health",
                process,
                0.25,
                {
                    "status": "ok",
                    "qualification": "experimental_not_release_qualified",
                },
            )
    finally:
        parent.terminate()
        parent.wait(timeout=5)
