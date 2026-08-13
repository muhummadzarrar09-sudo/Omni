#!/usr/bin/env python3
"""B02 managed startup/stop/restart smoke test on the current host.

This is useful non-Windows evidence only. It does not qualify either required
native Windows 11 Arm64/x64 B02 lane or the physical DGX target.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import psutil
from websockets.sync.client import connect as websocket_connect

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omni_v2.core.config import load_config
from omni_v2.core.lifecycle import restart, start, status, stop


def free_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def get_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise TypeError(f"{url} did not return a JSON object")
    return value


def request_json_status(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    origin: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers: dict[str, str] = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if origin is not None:
        headers["Origin"] = origin
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        value = json.loads(response.read())
        status_code = response.status
    if not isinstance(value, dict):
        raise TypeError(f"{url} did not return a JSON object")
    return status_code, value


def post_json(url: str, payload: dict[str, object], *, origin: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise TypeError(f"{url} did not return a JSON object")
    return value


def verify_websocket(frontend_url: str, ticket: str) -> None:
    websocket_url = frontend_url.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
    with websocket_connect(
        f"{websocket_url}/ws?token={ticket}",
        origin=frontend_url,
        open_timeout=10,
    ) as websocket:
        websocket.send(json.dumps({"smoke": "B02"}))
        response = json.loads(websocket.recv(timeout=10))
    require(
        response.get("type") == "echo" and response.get("data", {}).get("smoke") == "B02",
        "authenticated same-origin WebSocket proxy did not echo the smoke payload",
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def wait_gone(pids: set[int]) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not any(psutil.pid_exists(pid) for pid in pids):
            return
        time.sleep(0.1)
    remaining = sorted(pid for pid in pids if psutil.pid_exists(pid))
    raise RuntimeError(f"managed process IDs survived stop: {remaining}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart", action="store_true", help="also replace the running generation")
    parser.add_argument("--backend-only", action="store_true", help="skip the Next.js process/proxy check")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    ports: set[int] = set()
    while len(ports) < 4:
        ports.add(free_port())
    backend_port, frontend_port, discovery_port, browser_debug_port = ports

    with tempfile.TemporaryDirectory(prefix="omni-startup-smoke-") as temporary:
        environment = {
            "OMNI_DATA_DIR": temporary,
            "OMNI_BACKEND_PORT": str(backend_port),
            "OMNI_FRONTEND_PORT": str(frontend_port),
            "OMNI_DISCOVERY_PORT": str(discovery_port),
            "OMNI_BROWSER_DEBUG_PORT": str(browser_debug_port),
            "OMNI_API_TOKEN": "b02-smoke-token",
        }
        previous = os.environ.copy()
        os.environ.update(environment)
        config = load_config()
        all_pids: set[int] = set()
        try:
            first = start(
                config=config,
                repository_root=ROOT,
                include_frontend=not args.backend_only,
                timeout=args.timeout,
            )
            require(first.ok, "first managed start was not ready")
            active = first
            first_pids = {item.pid for item in first.services if item.pid is not None}
            all_pids.update(first_pids)
            require(status(config).ok, "status did not verify the started generation")
            health = get_json(config.backend_health_url)
            require(health.get("status") in {"healthy", "ok"}, "backend health was not healthy")
            if not args.backend_only:
                proxy_health = get_json(f"{config.frontend_url}/api/health")
                require(
                    proxy_health.get("status") in {"healthy", "ok"},
                    "same-origin frontend proxy did not reach the configured backend",
                )
                mutation = post_json(
                    f"{config.frontend_url}/api/goals",
                    {"intent": "B02 authenticated proxy smoke", "title": "B02 smoke"},
                    origin=config.frontend_url,
                )
                require(
                    isinstance(mutation.get("goal"), dict),
                    "server-side frontend proxy did not apply the canonical API token",
                )
                rejected_status, rejected = request_json_status(
                    f"{config.frontend_url}/api/execute",
                    method="POST",
                    payload={"command": "must not execute"},
                    origin="https://cross-origin.invalid",
                )
                require(
                    rejected_status == 403
                    and rejected.get("error") == "cross_origin_mutation_rejected",
                    "frontend proxy did not reject a cross-origin browser mutation",
                )
                validation_status, _ = request_json_status(
                    f"{config.frontend_url}/api/execute",
                    method="POST",
                    payload={},
                    origin=config.frontend_url,
                )
                require(
                    validation_status == 422,
                    "frontend proxy did not preserve the backend validation status",
                )
                ticket_payload = post_json(
                    f"{config.frontend_url}/api/python/auth/websocket-ticket",
                    {},
                    origin=config.frontend_url,
                )
                ticket = ticket_payload.get("ticket")
                require(isinstance(ticket, str) and bool(ticket), "WebSocket ticket was not issued")
                verify_websocket(config.frontend_url, ticket)

            if args.restart:
                replaced = restart(
                    config=config,
                    repository_root=ROOT,
                    include_frontend=not args.backend_only,
                    timeout=args.timeout,
                )
                require(replaced.ok, "managed restart was not ready")
                active = replaced
                require(replaced.run_id != first.run_id, "restart reused the old generation identifier")
                second_pids = {item.pid for item in replaced.services if item.pid is not None}
                all_pids.update(second_pids)
                require(first_pids.isdisjoint(second_pids), "restart reused an old process identity")
                require(status(config).ok, "status did not verify the restarted generation")

            if not args.backend_only:
                backend_service = next(item for item in active.services if item.name == "backend")
                require(backend_service.pid is not None, "managed backend has no process identity")
                backend_process = psutil.Process(backend_service.pid)
                backend_process.terminate()
                backend_process.wait(timeout=10)
                unavailable_status, unavailable = request_json_status(
                    f"{config.frontend_url}/api/health"
                )
                require(
                    unavailable_status == 503
                    and unavailable.get("error") == "backend_unavailable",
                    "frontend proxy did not report backend unavailability as HTTP 503",
                )

            stopped = stop(config=config, timeout=10)
            require(stopped.ok, "managed stop failed")
            require(not config.runtime_state_path.exists(), "runtime ownership state survived clean stop")
            wait_gone(all_pids)
            require(not status(config).ok, "status still reports a running generation after stop")
        finally:
            # Safe idempotent cleanup for exceptions. Ownership checks prevent
            # this from signaling unrelated processes.
            stop(config=config, timeout=10)
            os.environ.clear()
            os.environ.update(previous)

    print("B02 managed startup smoke: PASS")
    print("Qualification boundary: current-host evidence only; not Windows 11 x64 evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
