"""Command-line interface for configuration, diagnostics, and managed runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omni_v2.core.config import ConfigError, load_config, write_default_config
from omni_v2.core.lifecycle import LifecycleError, restart, start, status, stop
from omni_v2.core.preflight import render_report, run_preflight, write_json_report


def _root(value: str | None) -> Path:
    return Path(value).expanduser().resolve() if value else Path(__file__).resolve().parents[2]


def _emit_json(value: object) -> None:
    if hasattr(value, "to_dict"):
        value = value.to_dict()  # type: ignore[union-attr]
    print(json.dumps(value, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omni-runtime",
        description="Configure, diagnose, and manage the OMNI source-checkout runtime.",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    commands = parser.add_subparsers(dest="command", required=True)

    config = commands.add_parser("config", help="show or initialize non-secret configuration")
    config.add_argument("action", choices=("show", "init"), nargs="?", default="show")

    preflight = commands.add_parser("preflight", help="run side-effect-light readiness checks")
    preflight.add_argument("--primary", action="store_true", help="require Windows 11 x64")
    preflight.add_argument("--frontend", action="store_true", help="require a built frontend")
    preflight.add_argument("--root", help="source checkout root")
    preflight.add_argument("--output", type=Path, help="write the JSON report to this path")

    for name in ("start", "restart"):
        command = commands.add_parser(name, help=f"{name} the owned runtime")
        command.add_argument("--backend-only", action="store_true")
        command.add_argument("--root", help="source checkout root")
        command.add_argument("--timeout", type=float, default=45.0)
        command.add_argument("--skip-preflight", action="store_true")

    stop_command = commands.add_parser("stop", help="stop only the owned process tree")
    stop_command.add_argument("--timeout", type=float, default=10.0)
    commands.add_parser("status", help="inspect persisted runtime ownership")
    return parser


def _run(args: argparse.Namespace) -> int:
    if args.command == "config":
        config = load_config()
        if args.action == "init":
            path, created = write_default_config(data_dir=config.data_dir)
            result = {"created": created, "path": str(path), "configuration": config.public_dict()}
        else:
            result = config.public_dict()
        _emit_json(result)
        return 0

    if args.command == "preflight":
        report = run_preflight(
            require_primary=args.primary,
            require_frontend=args.frontend,
            repository_root=_root(args.root),
        )
        output = args.output or load_config().diagnostics_path
        write_json_report(report, output)
        if args.json:
            _emit_json(report)
        else:
            render_report(report)
            print(f"Diagnostics: {output}")
        return 0 if report.ok else 1

    if args.command == "status":
        result = status()
    elif args.command == "stop":
        result = stop(timeout=args.timeout)
    else:
        function = start if args.command == "start" else restart
        result = function(
            repository_root=_root(args.root),
            include_frontend=not args.backend_only,
            timeout=args.timeout,
            preflight=not args.skip_preflight,
        )
    if args.json:
        _emit_json(result)
    else:
        print(f"OMNI {result.operation}: {'OK' if result.ok else 'NOT RUNNING'}")
        for service in result.services:
            pid = f" PID {service.pid}" if service.pid is not None else ""
            print(f"  {service.name}: {service.status}{pid} — {service.url}")
            print(f"    {service.detail}")
        if result.diagnostics_path:
            print(f"Diagnostics: {result.diagnostics_path}")
    if args.command == "status":
        return 0
    return 0 if result.ok else 1


def main(argv: list[str] | None = None) -> int:
    """Run the runtime CLI with stable nonzero failure behavior."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except (ConfigError, LifecycleError, OSError, ValueError) as exc:
        if args.json:
            _emit_json({"ok": False, "error": str(exc)})
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
