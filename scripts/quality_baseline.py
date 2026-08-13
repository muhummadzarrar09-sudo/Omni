#!/usr/bin/env python3
"""Generate and validate OMNI's B00 quality inventory, or capture a local baseline.

The generated inventory and Markdown are deterministic for a given source tree. The
`capture` command additionally runs environment-dependent probes and writes their
full output under quality/.local/ (ignored by Git). Use --publish to write a small,
explicit evidence summary that can be reviewed and committed.
"""

from __future__ import annotations

import argparse
import ast
import collections
import datetime as dt
import fnmatch
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "quality"
CAPABILITIES_PATH = QUALITY / "capabilities.json"
SCORECARD_PATH = QUALITY / "scorecard.json"
POLICY_PATH = QUALITY / "policy.json"
BATCHES_PATH = QUALITY / "batches.json"
INVENTORY_PATH = QUALITY / "inventory.json"
CAPABILITY_DOC_PATH = ROOT / "docs" / "CAPABILITY_MATRIX.md"
SCORECARD_DOC_PATH = ROOT / "docs" / "QUALITY_SCORECARD.md"
BATCHES_DOC_PATH = ROOT / "docs" / "EXECUTION_BATCHES.md"
LOCAL_BASELINE_PATH = QUALITY / ".local" / "baseline-results.json"

LIFECYCLES = {"stable", "beta", "experimental", "demo", "unavailable", "removed"}
IMPLEMENTATIONS = {"real", "partial", "demo", "placeholder", "stub", "infrastructure"}
SCORE_STATUSES = {
    "pass",
    "in_progress",
    "blocked",
    "not_measured",
    "not_applicable_personal_scope",
}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html"}
WEB_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".css", ".html"}
IGNORED_PARTS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


class ValidationError(Exception):
    """Raised when a machine-readable quality authority is invalid."""


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing required file: {relative(path)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {relative(path)}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{relative(path)} must contain a JSON object")
    return data


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def iter_files(root: Path, suffixes: set[str] | None = None) -> Iterable[Path]:
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        if suffixes is None or path.suffix.lower() in suffixes:
            yield path


def production_files() -> list[Path]:
    files: set[Path] = set()
    for base in (ROOT / "omni_v2", ROOT / "omni", ROOT / "backend_fastapi"):
        for path in iter_files(base, SOURCE_SUFFIXES):
            if "tests" in path.relative_to(ROOT).parts:
                continue
            if path.name.startswith("test_"):
                continue
            files.add(path)
    for name in ("omni.py", "omni_daemon.py", "omni_desktop.py"):
        path = ROOT / name
        if path.exists():
            files.add(path)
    for base in (ROOT / "frontend_next" / "app", ROOT / "frontend_next" / "components", ROOT / "mobile"):
        files.update(iter_files(base, SOURCE_SUFFIXES))
    return sorted(files, key=relative)


def test_files() -> list[Path]:
    files: set[Path] = set()
    for path in iter_files(ROOT / "omni_v2", {".py"}):
        parts = path.relative_to(ROOT).parts
        if "tests" in parts or path.name.startswith("test_"):
            files.add(path)
    return sorted(files, key=relative)


def file_record(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    text = payload.decode("utf-8", errors="replace")
    return {
        "path": relative(path),
        "bytes": len(payload),
        "lines": len(text.splitlines()),
        "nonblank_lines": sum(bool(line.strip()) for line in text.splitlines()),
        "sha256": sha256_bytes(payload),
    }


def parse_python(path: Path) -> ast.AST:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=relative(path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValidationError(f"cannot parse {relative(path)}: {exc}") from exc


def python_ast_metrics(paths: Iterable[Path]) -> dict[str, int]:
    metrics = collections.Counter()
    for path in paths:
        if path.suffix != ".py":
            continue
        for node in ast.walk(parse_python(path)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions"] += 1
            elif isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
    return dict(sorted(metrics.items()))


def body_signal(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    body = list(node.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body or all(
        isinstance(item, ast.Pass)
        or (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant) and item.value.value is Ellipsis)
        for item in body
    ):
        return "placeholder_body"
    if len(body) == 1 and isinstance(body[0], ast.Raise):
        call = body[0].exc
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "NotImplementedError":
            return "explicitly_unimplemented"
    return "code_present_effect_unverified"


def fastapi_routes() -> list[dict[str, str]]:
    methods = {"get", "post", "put", "patch", "delete", "options", "head", "websocket"}
    routes: list[dict[str, str]] = []
    for path in iter_files(ROOT / "backend_fastapi", {".py"}):
        for node in ast.walk(parse_python(path)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                method = decorator.func.attr.lower()
                if method not in methods:
                    continue
                route_path = "<dynamic>"
                if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                    route_path = decorator.args[0].value
                owner = decorator.func.value.id if isinstance(decorator.func.value, ast.Name) else "<expression>"
                routes.append(
                    {
                        "method": method.upper(),
                        "path": route_path,
                        "handler": node.name,
                        "owner": owner,
                        "source": f"{relative(path)}:{getattr(node, 'lineno', 0)}",
                        "implementation_signal": body_signal(node),
                    }
                )
    return sorted(routes, key=lambda row: (row["source"], row["method"], row["path"]))


def literal_string_list(node: ast.AST) -> list[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return None
    values: list[str] = []
    for item in node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            return None
        values.append(item.value)
    return values


def tool_declarations() -> list[dict[str, Any]]:
    """Inventory statically declared tool/plugin classes without importing application code."""
    declarations: list[dict[str, Any]] = []
    for path in iter_files(ROOT / "omni_v2" / "tools", {".py"}):
        if path.name == "__init__.py":
            continue
        for node in parse_python(path).body:
            if not isinstance(node, ast.ClassDef):
                continue
            supported_actions: list[str] | None = None
            has_execute = False
            base_names: list[str] = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    base_names.append(base.id)
                elif isinstance(base, ast.Attribute):
                    base_names.append(base.attr)
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == "execute":
                    has_execute = True
                if isinstance(member, ast.Assign):
                    for target in member.targets:
                        if isinstance(target, ast.Name) and target.id == "SUPPORTED_ACTIONS":
                            supported_actions = literal_string_list(member.value)
            if not has_execute and not any(name.endswith(("Tool", "Plugin")) or name == "CommandPlugin" for name in base_names):
                continue
            declarations.append(
                {
                    "class": node.name,
                    "source": f"{relative(path)}:{node.lineno}",
                    "bases": base_names,
                    "execute_declared": has_execute,
                    "implementation_signal": body_signal(next(
                        member
                        for member in node.body
                        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == "execute"
                    )) if has_execute else "inherited_or_missing_execute",
                    "supported_actions": supported_actions,
                    "supported_action_count": None if supported_actions is None else len(supported_actions),
                }
            )
    return sorted(declarations, key=lambda row: (row["source"], row["class"]))


def path_matches(source_path: str, actual: str) -> bool:
    if any(char in source_path for char in "*?["):
        return fnmatch.fnmatchcase(actual, source_path)
    candidate = ROOT / source_path
    if candidate.is_dir():
        prefix = source_path.rstrip("/") + "/"
        return actual.startswith(prefix)
    return actual == source_path


def validate_authorities(
    capabilities: dict[str, Any],
    scorecard: dict[str, Any],
    policy: dict[str, Any],
    batches: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    capability_rows = capabilities.get("capabilities")
    if not isinstance(capability_rows, list) or not capability_rows:
        errors.append("capabilities.json: capabilities must be a non-empty list")
        capability_rows = []
    capability_ids: list[str] = []
    source_owners: dict[str, list[str]] = collections.defaultdict(list)
    for index, row in enumerate(capability_rows):
        prefix = f"capabilities.json: capabilities[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        capability_id = row.get("id")
        if not isinstance(capability_id, str) or not capability_id:
            errors.append(f"{prefix}.id must be a non-empty string")
            continue
        capability_ids.append(capability_id)
        if row.get("lifecycle") not in LIFECYCLES:
            errors.append(f"{prefix}.lifecycle is invalid: {row.get('lifecycle')!r}")
        if row.get("implementation") not in IMPLEMENTATIONS:
            errors.append(f"{prefix}.implementation is invalid: {row.get('implementation')!r}")
        for field in ("name", "area", "target_scope", "summary"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if not isinstance(row.get("known_gaps"), list):
            errors.append(f"{prefix}.known_gaps must be a list")
        if not isinstance(row.get("owner"), str) or not row["owner"].strip():
            errors.append(f"{prefix}.owner must be a non-empty string")
        entry_points = row.get("entry_points")
        if not isinstance(entry_points, list) or not entry_points:
            errors.append(f"{prefix}.entry_points must be a non-empty list")
        else:
            for entry_point in entry_points:
                if not isinstance(entry_point, str) or not entry_point:
                    errors.append(f"{prefix}.entry_points contains an invalid path")
                elif not any(char in entry_point for char in "*?[") and not (ROOT / entry_point).exists():
                    errors.append(f"{prefix}.entry_points does not exist: {entry_point}")
                elif any(char in entry_point for char in "*?[") and not list(ROOT.glob(entry_point)):
                    errors.append(f"{prefix}.entry_points glob has no matches: {entry_point}")

        requirements = row.get("requirements")
        if not isinstance(requirements, dict):
            errors.append(f"{prefix}.requirements must be an object")
            requirements = {}
        if not isinstance(requirements.get("audit_status"), str) or not requirements.get("audit_status", "").strip():
            errors.append(f"{prefix}.requirements.audit_status must be a non-empty string")
        for field in ("packages", "models", "accounts_or_keys", "hardware"):
            if not isinstance(requirements.get(field), list):
                errors.append(f"{prefix}.requirements.{field} must be a list")

        tests = row.get("tests")
        if not isinstance(tests, dict):
            errors.append(f"{prefix}.tests must be an object")
            tests = {}
        for field in ("unit_or_contract", "integration", "end_to_end", "hardware"):
            test_paths = tests.get(field)
            if not isinstance(test_paths, list):
                errors.append(f"{prefix}.tests.{field} must be a list")
                continue
            for test_path in test_paths:
                if not isinstance(test_path, str) or not test_path or not (ROOT / test_path).is_file():
                    errors.append(f"{prefix}.tests.{field} contains a missing or invalid path: {test_path!r}")
        required_test_types = tests.get("required_types_for_stable")
        known_test_types = {"unit_or_contract", "integration", "end_to_end", "hardware"}
        if (
            not isinstance(required_test_types, list)
            or not required_test_types
            or any(item not in known_test_types for item in required_test_types)
        ):
            errors.append(f"{prefix}.tests.required_types_for_stable must name one or more known test types")
            required_test_types = []
        if not isinstance(tests.get("qualification"), str) or not tests.get("qualification", "").strip():
            errors.append(f"{prefix}.tests.qualification must be a non-empty string")
        if not isinstance(tests.get("note"), str) or not tests.get("note", "").strip():
            errors.append(f"{prefix}.tests.note must be a non-empty string")

        if not isinstance(row.get("verified_platforms"), list):
            errors.append(f"{prefix}.verified_platforms must be a list")
        if not isinstance(row.get("platform_note"), str) or not row["platform_note"].strip():
            errors.append(f"{prefix}.platform_note must be a non-empty string")
        data_access = row.get("data_access")
        if not isinstance(data_access, list) or not data_access or not all(isinstance(item, str) and item.strip() for item in data_access):
            errors.append(f"{prefix}.data_access must be a non-empty list of strings")
        network = row.get("network")
        if not isinstance(network, dict):
            errors.append(f"{prefix}.network must be an object")
            network = {}
        if not isinstance(network.get("mode"), str) or not network.get("mode", "").strip():
            errors.append(f"{prefix}.network.mode must be a non-empty string")
        if not isinstance(network.get("destinations"), list):
            errors.append(f"{prefix}.network.destinations must be a list")
        if not isinstance(network.get("disclosure"), str) or not network.get("disclosure", "").strip():
            errors.append(f"{prefix}.network.disclosure must be a non-empty string")
        if network.get("privacy_qualification") not in {"not_qualified", "release_qualified"}:
            errors.append(f"{prefix}.network.privacy_qualification must be not_qualified or release_qualified")

        interface_audit = row.get("interface_audit")
        if not isinstance(interface_audit, dict):
            errors.append(f"{prefix}.interface_audit must be an object")
            interface_audit = {}
        if not isinstance(interface_audit.get("scope"), str) or not interface_audit.get("scope", "").strip():
            errors.append(f"{prefix}.interface_audit.scope must be a non-empty string")
        if interface_audit.get("qualification") not in {"not_applicable", "not_qualified", "release_qualified"}:
            errors.append(f"{prefix}.interface_audit.qualification is invalid")
        if not isinstance(interface_audit.get("evidence"), list):
            errors.append(f"{prefix}.interface_audit.evidence must be a list")

        paths = row.get("paths")
        if not isinstance(paths, list) or not paths:
            errors.append(f"{prefix}.paths must be a non-empty list")
        else:
            for source_path in paths:
                if not isinstance(source_path, str) or not source_path:
                    errors.append(f"{prefix}.paths contains an invalid path")
                    continue
                source_owners[source_path].append(capability_id)
                if not any(char in source_path for char in "*?[") and not (ROOT / source_path).exists():
                    errors.append(f"{prefix}.paths does not exist: {source_path}")
                if any(char in source_path for char in "*?[") and not list(ROOT.glob(source_path)):
                    errors.append(f"{prefix}.paths glob has no matches: {source_path}")
        if row.get("lifecycle") == "stable" and row.get("implementation") != "real":
            errors.append(f"{prefix}: stable capability must have implementation=real")
        if row.get("lifecycle") == "stable" and row.get("known_gaps"):
            errors.append(f"{prefix}: stable capability cannot retain known gaps")
        if row.get("lifecycle") == "stable" and tests.get("qualification") != "release_qualified":
            errors.append(f"{prefix}: stable capability requires tests.qualification=release_qualified")
        if row.get("lifecycle") == "stable":
            for test_type in required_test_types:
                if not tests.get(test_type):
                    errors.append(f"{prefix}: stable capability requires mapped {test_type} test evidence")
        if row.get("lifecycle") == "stable" and not row.get("verified_platforms"):
            errors.append(f"{prefix}: stable capability requires at least one verified platform")
        if row.get("lifecycle") == "stable" and requirements.get("audit_status") != "complete":
            errors.append(f"{prefix}: stable capability requires requirements.audit_status=complete")
        if (
            row.get("lifecycle") == "stable"
            and network.get("mode") != "none_expected"
            and network.get("privacy_qualification") != "release_qualified"
        ):
            errors.append(f"{prefix}: stable network-capable capability requires release-qualified privacy disclosure")
        if (
            row.get("lifecycle") == "stable"
            and interface_audit.get("scope") != "not_applicable"
            and (
                interface_audit.get("qualification") != "release_qualified"
                or not interface_audit.get("evidence")
            )
        ):
            errors.append(f"{prefix}: stable tool/API capability requires release-qualified per-interface evidence")

    duplicates = sorted(item for item, count in collections.Counter(capability_ids).items() if count > 1)
    if duplicates:
        errors.append(f"capabilities.json: duplicate capability ids: {', '.join(duplicates)}")

    workflow_rows = capabilities.get("core_workflows")
    workflow_ids: list[str] = []
    if not isinstance(workflow_rows, list) or len(workflow_rows) != 10:
        errors.append("capabilities.json: exactly ten core_workflows are required")
        workflow_rows = []
    for index, row in enumerate(workflow_rows):
        prefix = f"capabilities.json: core_workflows[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        workflow_ids.append(str(row.get("id", "")))
        for field in ("id", "name", "outcome", "current_status", "qualification_batch"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")
    if workflow_ids != [f"W{i:02d}" for i in range(1, 11)]:
        errors.append("capabilities.json: workflow ids must be W01 through W10 in order")

    active_files = [
        path
        for path in production_files()
        if path.name != "__init__.py" and path.suffix.lower() in SOURCE_SUFFIXES
    ]
    patterns = [(row.get("id", "?"), item) for row in capability_rows for item in row.get("paths", [])]
    uncovered = []
    for path in active_files:
        actual = relative(path)
        if not any(path_matches(pattern, actual) for _, pattern in patterns):
            uncovered.append(actual)
    if uncovered:
        errors.append("capabilities.json: active source files without capability coverage: " + ", ".join(uncovered))

    categories = scorecard.get("categories")
    if not isinstance(categories, list) or not categories:
        errors.append("scorecard.json: categories must be a non-empty list")
        categories = []
    category_ids = []
    for index, row in enumerate(categories):
        prefix = f"scorecard.json: categories[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        category_ids.append(row.get("id"))
        if row.get("status") not in SCORE_STATUSES:
            errors.append(f"{prefix}.status is invalid: {row.get('status')!r}")
        score = row.get("current_score")
        target = row.get("target_score")
        for field, value in (("current_score", score), ("target_score", target)):
            if value is not None and (not isinstance(value, (int, float)) or not 0 <= value <= 10):
                errors.append(f"{prefix}.{field} must be null or between 0 and 10")
        if row.get("status") == "pass" and score != 10:
            errors.append(f"{prefix}: pass requires current_score=10")
        if not row.get("evidence") or not isinstance(row.get("evidence"), list):
            errors.append(f"{prefix}.evidence must be a non-empty list")
        if not row.get("exit_criteria") or not isinstance(row.get("exit_criteria"), list):
            errors.append(f"{prefix}.exit_criteria must be a non-empty list")
    duplicate_categories = sorted(item for item, count in collections.Counter(category_ids).items() if count > 1)
    if duplicate_categories:
        errors.append(f"scorecard.json: duplicate category ids: {', '.join(duplicate_categories)}")

    execution = policy.get("execution", {})
    order = execution.get("batch_order")
    expected_order = [f"B{i:02d}" for i in range(17)]
    if order != expected_order:
        errors.append("policy.json: execution.batch_order must be B00 through B16")
    current_batch = execution.get("current_batch")
    next_batch = execution.get("next_batch")
    closed_batches = execution.get("closed_batches", [])
    if current_batch is not None and current_batch not in expected_order:
        errors.append("policy.json: execution.current_batch must be null or a known batch")
    if not isinstance(closed_batches, list) or closed_batches != expected_order[: len(closed_batches)]:
        errors.append("policy.json: closed_batches must be a contiguous prefix of batch_order")
        closed_batches = []
    expected_next = expected_order[len(closed_batches)] if len(closed_batches) < len(expected_order) else None
    if next_batch != expected_next:
        errors.append(f"policy.json: execution.next_batch must be {expected_next!r}")
    if current_batch is not None and current_batch != expected_next:
        errors.append("policy.json: current_batch must equal the first unclosed batch")
    if policy.get("feature_freeze", {}).get("enabled") is not True:
        errors.append("policy.json: feature freeze must remain enabled before B16 closes")
    if scorecard.get("batch_state", {}).get("current_batch") != current_batch:
        errors.append("scorecard.json and policy.json disagree on current_batch")
    if scorecard.get("batch_state", {}).get("next_batch") != next_batch:
        errors.append("scorecard.json and policy.json disagree on next_batch")
    if scorecard.get("batch_state", {}).get("feature_freeze") != policy.get("feature_freeze", {}).get("enabled"):
        errors.append("scorecard.json and policy.json disagree on feature_freeze")

    batch_rows = batches.get("batches")
    if not isinstance(batch_rows, list) or len(batch_rows) != len(expected_order):
        errors.append("batches.json: batches must contain exactly B00 through B16")
        batch_rows = []
    batch_ids = [row.get("id") for row in batch_rows if isinstance(row, dict)]
    if batch_ids != expected_order:
        errors.append("batches.json: batch ids must be B00 through B16 in order")
    active_batches = []
    ready_batches = []
    for index, row in enumerate(batch_rows):
        prefix = f"batches.json: batches[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        expected_dependencies = [] if index == 0 else [expected_order[index - 1]]
        if row.get("depends_on") != expected_dependencies:
            errors.append(f"{prefix}.depends_on must be {expected_dependencies}")
        if row.get("status") not in batches.get("batch_status_definitions", {}):
            errors.append(f"{prefix}.status has no definition: {row.get('status')!r}")
        if row.get("status") == "in_progress":
            active_batches.append(row.get("id"))
        if row.get("status") == "ready":
            ready_batches.append(row.get("id"))
        for field in ("title", "objective", "evidence_path", "solo_estimate"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")
        for field in ("in_scope", "target_paths", "verification_commands", "risks", "exit_gate"):
            if not isinstance(row.get(field), list) or not row[field]:
                errors.append(f"{prefix}.{field} must be a non-empty list")
        if row.get("status") == "closed":
            if not isinstance(row.get("closed_on"), str) or not row.get("closed_on", "").strip():
                errors.append(f"{prefix}.closed_on must be recorded for a closed batch")
            closure_evidence = row.get("closure_evidence")
            if not isinstance(closure_evidence, str) or not closure_evidence:
                errors.append(f"{prefix}.closure_evidence must be recorded for a closed batch")
            elif not (ROOT / closure_evidence).is_file():
                errors.append(f"{prefix}.closure_evidence does not exist: {closure_evidence}")
            else:
                try:
                    closure = read_json(ROOT / closure_evidence)
                except ValidationError as exc:
                    errors.append(str(exc))
                else:
                    if closure.get("batch") != row.get("id") or closure.get("decision") != "closed":
                        errors.append(f"{prefix}.closure_evidence does not approve this batch")
    # A formal dependency exception may permit exactly one bounded preparation
    # track without laundering closure of the blocked dependency or unlocking a
    # further batch. It is deliberately narrow so ordinary batch execution
    # remains strictly sequential.
    dependency_exception = execution.get("dependency_exception")
    permitted_parallel_batch = None
    if dependency_exception is not None:
        if not isinstance(dependency_exception, dict):
            errors.append("policy.json: execution.dependency_exception must be an object")
        else:
            required_exception = {
                "id": "B02-B03-preparation-exception-2026-08-13",
                "blocked_dependency": "B02",
                "permitted_batch": "B03",
                "mode": "preparation_and_implementation_only",
            }
            for field, expected in required_exception.items():
                if dependency_exception.get(field) != expected:
                    errors.append(f"policy.json: dependency exception {field} must be {expected!r}")
            evidence = dependency_exception.get("evidence")
            if not isinstance(evidence, str) or not (ROOT / evidence).is_file():
                errors.append("policy.json: dependency exception evidence must exist")
            elif len(batch_rows) <= 2 or batch_rows[2].get("status") == "closed":
                errors.append("policy.json: B02 must remain unclosed while its dependency exception is active")
            else:
                permitted_parallel_batch = "B03"

    expected_active = [current_batch] if current_batch is not None else []
    if permitted_parallel_batch:
        expected_active.append(permitted_parallel_batch)
    expected_ready = [] if current_batch is not None or next_batch is None else [next_batch]
    if active_batches != expected_active:
        errors.append(f"batches.json: in_progress batches must be {expected_active}; found {active_batches}")
    if ready_batches != expected_ready:
        errors.append(f"batches.json: ready batches must be {expected_ready}; found {ready_batches}")
    if [row.get("status") for row in batch_rows[: len(closed_batches)]] != ["closed"] * len(closed_batches):
        errors.append("batches.json: policy closed_batches must have status=closed")
    for row in batch_rows[len(closed_batches) + (1 if next_batch is not None else 0) :]:
        if row.get("id") == permitted_parallel_batch:
            exception = row.get("dependency_exception")
            if not isinstance(exception, dict) or exception.get("id") != dependency_exception.get("id"):
                errors.append("batches.json: permitted parallel batch must record the matching dependency exception")
        elif row.get("status") != "locked":
            errors.append(f"batches.json: downstream batch {row.get('id')} must be locked")

    expansion_rows = batches.get("post_10_expansions")
    expected_expansions = [f"E{i:02d}" for i in range(1, 11)]
    if not isinstance(expansion_rows, list) or [row.get("id") for row in expansion_rows if isinstance(row, dict)] != expected_expansions:
        errors.append("batches.json: post_10_expansions must be E01 through E10 in order")
        expansion_rows = []
    if policy.get("post_10", {}).get("expansion_queue") != expected_expansions:
        errors.append("policy.json and batches.json disagree on the E01-E10 expansion queue")
    for index, row in enumerate(expansion_rows):
        for field in ("title", "gate"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f"batches.json: post_10_expansions[{index}].{field} must be a non-empty string")

    if errors:
        raise ValidationError("\n- " + "\n- ".join(errors))

    return {
        "capability_count": len(capability_rows),
        "workflow_count": len(workflow_rows),
        "scorecard_category_count": len(categories),
        "batch_count": len(batch_rows),
        "expansion_count": len(expansion_rows),
        "covered_active_source_count": len(active_files),
        "source_pattern_count": len(patterns),
    }


def aggregate_digest(records: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_inventory(capabilities: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    production = [file_record(path) for path in production_files()]
    tests = [file_record(path) for path in test_files()]
    all_records = sorted(production + tests, key=lambda row: row["path"])
    capability_rows = capabilities["capabilities"]
    routes = fastapi_routes()
    tools = tool_declarations()
    ast_metrics = python_ast_metrics([ROOT / row["path"] for row in all_records])
    return {
        "schema_version": 1,
        "generated_by": "python scripts/quality_baseline.py generate",
        "inventory_policy": {
            "production": "Active Python, JavaScript/TypeScript, CSS, and HTML under omni_v2 (excluding tests), omni, backend_fastapi, frontend_next/app, frontend_next/components, and mobile, plus root Python launchers.",
            "tests": "Python files under omni_v2/tests plus test-prefixed Python modules under omni_v2.",
            "excluded": sorted(IGNORED_PARTS | {"_archive"}),
            "line_metric": "Physical split lines; nonblank lines contain at least one non-whitespace character.",
        },
        "authority_sha256": {
            relative(CAPABILITIES_PATH): sha256_bytes(CAPABILITIES_PATH.read_bytes()),
            relative(SCORECARD_PATH): sha256_bytes(SCORECARD_PATH.read_bytes()),
            relative(POLICY_PATH): sha256_bytes(POLICY_PATH.read_bytes()),
            relative(BATCHES_PATH): sha256_bytes(BATCHES_PATH.read_bytes()),
        },
        "source_digest": aggregate_digest(all_records),
        "counts": {
            "production_files": len(production),
            "production_bytes": sum(row["bytes"] for row in production),
            "production_lines": sum(row["lines"] for row in production),
            "production_nonblank_lines": sum(row["nonblank_lines"] for row in production),
            "test_files": len(tests),
            "test_bytes": sum(row["bytes"] for row in tests),
            "test_lines": sum(row["lines"] for row in tests),
            "test_nonblank_lines": sum(row["nonblank_lines"] for row in tests),
            "capabilities": len(capability_rows),
            "core_workflows": len(capabilities["core_workflows"]),
            "areas": len({row["area"] for row in capability_rows}),
            "fastapi_route_decorators": len(routes),
            "declared_tool_classes": len(tools),
            "declared_tool_actions": sum(row["supported_action_count"] or 0 for row in tools),
            **ast_metrics,
        },
        "capabilities_by_lifecycle": dict(sorted(collections.Counter(row["lifecycle"] for row in capability_rows).items())),
        "capabilities_by_implementation": dict(sorted(collections.Counter(row["implementation"] for row in capability_rows).items())),
        "capabilities_by_area": dict(sorted(collections.Counter(row["area"] for row in capability_rows).items())),
        "coverage": validation,
        "fastapi_routes": routes,
        "declared_tool_classes": tools,
        "files": {
            "production": production,
            "tests": tests,
        },
    }


def md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_capability_doc(capabilities: dict[str, Any], inventory: dict[str, Any]) -> str:
    product = capabilities["target_product"]
    rows = capabilities["capabilities"]
    lifecycle_counts = collections.Counter(row["lifecycle"] for row in rows)
    implementation_counts = collections.Counter(row["implementation"] for row in rows)
    result = [
        "# OMNI Capability Matrix",
        "",
        "> **Generated file.** Edit `quality/capabilities.json`, then run `python scripts/quality_baseline.py generate`.",
        "",
        f"**Authority verified:** {md(capabilities['verified_on'])}<br>",
        f"**Release state:** {md(product['release_state'])}<br>",
        f"**Source inventory digest:** `{inventory['source_digest']}`",
        "",
        "## Locked Product Promise",
        "",
        product["promise"],
        "",
        "## Platform Scope",
        "",
        "| Platform | Status | Reason |",
        "|---|---|---|",
        f"| {md(product['primary_platform']['name'])} (primary) | `{md(product['primary_platform']['status'])}` | {md(product['primary_platform']['reason'])} |",
    ]
    for platform_row in product["secondary_platforms"]:
        result.append(
            f"| {md(platform_row['name'])} | `{md(platform_row['status'])}` | {md(platform_row['reason'])} |"
        )
    result += ["", "## Pre-10 Non-goals", ""]
    result.extend(f"- {item}" for item in product["pre_10_non_goals"])
    result += [
        "",
        "## Locked Core Workflows",
        "",
        "| ID | Workflow | Current status | Qualification batch | Verifiable outcome |",
        "|---|---|---|---|---|",
    ]
    for workflow in capabilities["core_workflows"]:
        result.append(
            f"| {workflow['id']} | {md(workflow['name'])} | `{workflow['current_status']}` | {workflow['qualification_batch']} | {md(workflow['outcome'])} |"
        )
    result += [
        "",
        "## Inventory Summary",
        "",
        f"- **Capability groups:** {len(rows)}",
        f"- **Mapped active source files:** {inventory['coverage']['covered_active_source_count']}",
        f"- **Stable capabilities:** {lifecycle_counts.get('stable', 0)}",
        "- **Stable claim policy:** no capability is stable until exact-artifact qualification passes.",
        "",
        "| Lifecycle | Count | Definition |",
        "|---|---:|---|",
    ]
    for lifecycle in capabilities["lifecycle_definitions"]:
        result.append(
            f"| `{lifecycle}` | {lifecycle_counts.get(lifecycle, 0)} | {md(capabilities['lifecycle_definitions'][lifecycle])} |"
        )
    result += [
        "",
        "| Implementation reality | Count | Definition |",
        "|---|---:|---|",
    ]
    for implementation in capabilities["implementation_definitions"]:
        result.append(
            f"| `{implementation}` | {implementation_counts.get(implementation, 0)} | {md(capabilities['implementation_definitions'][implementation])} |"
        )
    result += [
        "",
        "## Capability Status",
        "",
        "Lifecycle and implementation reality are separate. `beta/real` means concrete behavior exists but release qualification is still open; `demo/demo`, `unavailable/placeholder`, and `unavailable/stub` are not working product claims.",
        "",
        "| ID | Capability | Area | Lifecycle | Reality | Target | Summary |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        result.append(
            f"| `{row['id']}` | {md(row['name'])} | {md(row['area'])} | `{row['lifecycle']}` | `{row['implementation']}` | `{row['target_scope']}` | {md(row['summary'])} |"
        )
    result += ["", "## Per-Capability Evidence, Requirements, and Ownership", ""]
    result += [
        "Test paths below record only the presence of relevant test code. They do not imply passing release qualification. Empty lists mean no mapped coverage of that type. Platform lists remain empty until a release-qualified platform run exists.",
        "",
    ]
    for row in rows:
        requirements = row["requirements"]
        tests = row["tests"]
        network = row["network"]
        interface_audit = row["interface_audit"]

        def values(items: list[str]) -> str:
            return ", ".join(f"`{item}`" for item in items) if items else "none recorded"

        result += [
            f"### `{row['id']}` — {row['name']}",
            "",
            f"- **Owner:** `{row['owner']}`",
            "- **Entry points:** " + ", ".join(f"`{path}`" for path in row["entry_points"]),
            "- **Source paths:** " + ", ".join(f"`{path}`" for path in row["paths"]),
            f"- **Requirements audit:** `{requirements['audit_status']}`",
            f"- **Known packages:** {values(requirements['packages'])}",
            f"- **Models:** {values(requirements['models'])}",
            f"- **Accounts or keys:** {values(requirements['accounts_or_keys'])}",
            f"- **Hardware:** {values(requirements['hardware'])}",
            f"- **Unit/contract test paths:** {values(tests['unit_or_contract'])}",
            f"- **Integration test paths:** {values(tests['integration'])}",
            f"- **End-to-end test paths:** {values(tests['end_to_end'])}",
            f"- **Hardware test paths:** {values(tests['hardware'])}",
            f"- **Required test types before stable:** {values(tests['required_types_for_stable'])}",
            f"- **Test qualification:** `{tests['qualification']}` — {tests['note']}",
            f"- **Verified platforms:** {values(row['verified_platforms'])}",
            f"- **Platform note:** {row['platform_note']}",
            f"- **Data accessed:** {', '.join(row['data_access'])}",
            f"- **Network mode:** `{network['mode']}`",
            f"- **Network destinations:** {values(network['destinations'])}",
            f"- **Privacy qualification:** `{network['privacy_qualification']}`",
            f"- **Network disclosure:** {network['disclosure']}",
            f"- **Tool/API interface audit:** `{interface_audit['qualification']}` over {interface_audit['scope']}; evidence: {values(interface_audit['evidence'])}",
            "- **Known gaps:**",
        ]
        if row["known_gaps"]:
            result.extend(f"  - {gap}" for gap in row["known_gaps"])
        else:
            result.append("  - No open gaps recorded.")
        result.append("")
    return "\n".join(result).rstrip() + "\n"


def display_score(value: Any) -> str:
    return "N/A" if value is None else f"{float(value):.1f}/10"


def render_scorecard_doc(scorecard: dict[str, Any]) -> str:
    result = [
        "# OMNI Quality Scorecard",
        "",
        "> **Generated file.** Edit `quality/scorecard.json`, then run `python scripts/quality_baseline.py generate`.",
        "",
        f"**Scope:** {scorecard['scope']}<br>",
        f"**Evidence verified:** {scorecard['verified_on']}<br>",
        f"**Current batch:** `{scorecard['batch_state']['current_batch'] or 'none'}`<br>",
        f"**Next batch:** `{scorecard['batch_state']['next_batch'] or 'none'}`<br>",
        f"**Feature freeze:** `{'enabled' if scorecard['batch_state']['feature_freeze'] else 'disabled'}`",
        "",
        scorecard["scoring_policy"],
        "",
        "## Current Scores",
        "",
        "| Category | Current | Target | Status | Closure gate |",
        "|---|---:|---:|---|---|",
    ]
    for row in scorecard["categories"]:
        result.append(
            f"| {md(row['name'])} | {display_score(row['current_score'])} | {display_score(row['target_score'])} | `{row['status']}` | `{row['closure_batch']}` |"
        )
    result += [
        "",
        "Commercial defensibility is intentionally outside the personal-core score. It remains unscored unless the owner explicitly starts the optional commercial validation track.",
        "",
        "## Evidence and Exit Criteria",
        "",
    ]
    for row in scorecard["categories"]:
        result += [
            f"### {row['name']} — {display_score(row['current_score'])}",
            "",
            f"**Status:** `{row['status']}`<br>",
            f"**Closure gate:** `{row['closure_batch']}`",
            "",
            "**Current evidence**",
            "",
        ]
        result.extend(f"- {item}" for item in row["evidence"])
        result += ["", "**10/10 exit criteria**", ""]
        marker = "x" if row["status"] == "pass" else " "
        result.extend(f"- [{marker}] {item}" for item in row["exit_criteria"])
        result.append("")
    return "\n".join(result).rstrip() + "\n"


def render_batches_doc(batches: dict[str, Any], policy: dict[str, Any]) -> str:
    result = [
        "# OMNI Locked Execution Batches",
        "",
        "> **Generated file.** Edit `quality/batches.json` or `quality/policy.json`, then run `python scripts/quality_baseline.py generate`.",
        "",
        f"**Current batch:** `{policy['execution']['current_batch'] or 'none'}`<br>",
        f"**Next batch:** `{policy['execution']['next_batch'] or 'none'}`<br>",
        f"**Feature freeze:** `{'enabled' if policy['feature_freeze']['enabled'] else 'disabled'}`<br>",
        "**Execution rule:** one batch at a time unless a recorded dependency exception permits a bounded preparation track; an exception cannot close a blocked dependency or unlock a later batch.",
        "",
    ]
    dependency_exception = policy["execution"].get("dependency_exception")
    if dependency_exception:
        result += [
            "## Active Dependency Exception",
            "",
            f"`{dependency_exception['id']}` permits `{dependency_exception['permitted_batch']}` as a `{dependency_exception['mode']}` track while `{dependency_exception['blocked_dependency']}` remains open. Evidence: `{dependency_exception['evidence']}`.",
            "",
        ]
    result += [
        "## Sequence",
        "",
        "| Batch | Title | Status | Dependency | Solo estimate |",
        "|---|---|---|---|---|",
    ]
    for row in batches["batches"]:
        result.append(
            f"| `{row['id']}` | {md(row['title'])} | `{row['status']}` | {md(', '.join(row['depends_on']) or 'None')} | {md(row['solo_estimate'])} |"
        )
    result += ["", "## Batch Contracts", ""]
    for row in batches["batches"]:
        result += [
            f"### {row['id']} — {row['title']}",
            "",
            f"**Status:** `{row['status']}`<br>",
            f"**Depends on:** `{', '.join(row['depends_on']) or 'none'}`<br>",
            f"**Solo estimate:** {row['solo_estimate']}<br>",
            f"**Evidence:** `{row['evidence_path']}`",
            "",
            f"**Objective:** {row['objective']}",
            "",
            "**In scope**",
            "",
        ]
        result.extend(f"- {item}" for item in row["in_scope"])
        result += ["", "**Target paths**", ""]
        result.extend(f"- `{item}`" for item in row["target_paths"])
        result += ["", "**Verification commands**", ""]
        result.extend(f"- `{item}`" for item in row["verification_commands"])
        result += ["", "**Principal risks**", ""]
        result.extend(f"- {item}" for item in row["risks"])
        result += ["", "**Exit gate**", ""]
        marker = "x" if row["status"] == "closed" else " "
        result.extend(f"- [{marker}] {item}" for item in row["exit_gate"])
        result.append("")
    result += [
        "## Post-10 Expansion Queue",
        "",
        "These items remain locked until B16 closes the exact-artifact 10/10 freeze. A listed idea is not a promise or working-capability claim.",
        "",
        "| Expansion | Title | Independent promotion gate |",
        "|---|---|---|",
    ]
    for row in batches["post_10_expansions"]:
        result.append(f"| `{row['id']}` | {md(row['title'])} | {md(row['gate'])} |")
    result += ["", "## Freeze and Claim Rules", ""]
    result.extend(f"- {item}" for item in policy["execution"]["rules"])
    result.append("")
    result.extend(f"- {item}" for item in policy["post_10"]["rules"])
    return "\n".join(result).rstrip() + "\n"


def generated_outputs() -> tuple[dict[str, Any], dict[Path, str]]:
    capabilities = read_json(CAPABILITIES_PATH)
    scorecard = read_json(SCORECARD_PATH)
    policy = read_json(POLICY_PATH)
    batches = read_json(BATCHES_PATH)
    validation = validate_authorities(capabilities, scorecard, policy, batches)
    inventory = build_inventory(capabilities, validation)
    outputs = {
        INVENTORY_PATH: json.dumps(inventory, indent=2, sort_keys=False) + "\n",
        CAPABILITY_DOC_PATH: render_capability_doc(capabilities, inventory),
        SCORECARD_DOC_PATH: render_scorecard_doc(scorecard),
        BATCHES_DOC_PATH: render_batches_doc(batches, policy),
    }
    return inventory, outputs


def generate(check: bool) -> dict[str, Any]:
    inventory, outputs = generated_outputs()
    drift = []
    for path, expected in outputs.items():
        if check:
            actual = path.read_text(encoding="utf-8") if path.exists() else None
            if actual != expected:
                drift.append(relative(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if drift:
        raise ValidationError(
            "generated quality artifacts are stale or missing: "
            + ", ".join(drift)
            + "; run `python scripts/quality_baseline.py generate`"
        )
    return inventory


def compact_output(value: str, limit: int = 30_000) -> str:
    if len(value) <= limit:
        return value
    removed = len(value) - limit
    return value[:limit] + f"\n... [{removed} characters truncated by baseline capture]\n"


def run_probe(
    name: str,
    command: list[str],
    *,
    cwd: Path = ROOT,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            env=merged_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        status = "pass" if process.returncode == 0 else "fail"
        returncode: int | None = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        returncode = None
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    finished = dt.datetime.now(dt.timezone.utc)
    return {
        "name": name,
        "command": command,
        "cwd": relative(cwd),
        "status": status,
        "returncode": returncode,
        "started_at": started.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "stdout": compact_output(stdout),
        "stderr": compact_output(stderr),
    }


def pytest_counts(output: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for count, label in re.findall(r"(\d+)\s+(passed|failed|skipped|xfailed|xpassed|errors?)", output):
        key = "error" if label.startswith("error") else label.rstrip("s")
        counts[key] = int(count)
    return counts


def wheel_probe(python: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="omni-wheel-baseline-") as temp_dir:
        probe = run_probe(
            "wheel_build_and_contents",
            [python, "-m", "pip", "wheel", "--disable-pip-version-check", "--no-deps", "--wheel-dir", temp_dir, "."],
            timeout=300,
        )
        wheels = sorted(Path(temp_dir).glob("*.whl"))
        probe["wheel"] = None
        if wheels:
            wheel = wheels[-1]
            with zipfile.ZipFile(wheel) as archive:
                names = sorted(archive.namelist())
            package_files = [name for name in names if name.endswith(".py")]
            probe["wheel"] = {
                "filename": wheel.name,
                "bytes": wheel.stat().st_size,
                "member_count": len(names),
                "python_file_count": len(package_files),
                "top_level_packages": sorted({name.split("/", 1)[0] for name in package_files if "/" in name}),
                "members": names,
            }
        return probe


def tool_probe(python: str) -> dict[str, Any]:
    code = textwrap.dedent(
        """
        import json
        from collections import Counter
        from omni_v2.tools import get_all_tools
        tools = get_all_tools()
        names = [type(tool).__name__ for tool in tools]
        details = []
        for tool in tools:
            actions = getattr(tool, "SUPPORTED_ACTIONS", getattr(tool, "supported_actions", []))
            if callable(actions):
                actions = actions()
            details.append({"class": type(tool).__name__, "actions": list(actions or [])})
        all_actions = [action for detail in details for action in detail["actions"]]
        print(json.dumps({
            "instance_count": len(tools),
            "class_counts": dict(sorted(Counter(names).items())),
            "duplicate_classes": sorted(name for name, count in Counter(names).items() if count > 1),
            "declared_action_count": len(all_actions),
            "unique_declared_action_count": len(set(all_actions)),
            "duplicate_actions": sorted(action for action, count in Counter(all_actions).items() if count > 1),
            "tools": details,
        }, sort_keys=True))
        """
    )
    probe = run_probe("runtime_tool_inventory", [python, "-c", code], timeout=60)
    try:
        probe["inventory"] = json.loads(probe["stdout"].strip())
    except (json.JSONDecodeError, TypeError):
        probe["inventory"] = None
    return probe


def audit_summary(probe: dict[str, Any]) -> dict[str, Any] | None:
    try:
        data = json.loads(probe["stdout"])
    except (json.JSONDecodeError, TypeError):
        return None
    metadata = data.get("metadata", {})
    return {
        "vulnerabilities": metadata.get("vulnerabilities"),
        "dependencies": metadata.get("dependencies"),
    }


def capture(publish: Path | None = None) -> dict[str, Any]:
    inventory = generate(check=False)
    python = sys.executable
    frontend = ROOT / "frontend_next"
    probes: list[dict[str, Any]] = []

    probes.append(run_probe("python_version", [python, "--version"], timeout=30))
    if shutil.which("node"):
        probes.append(run_probe("node_version", ["node", "--version"], timeout=30))
    else:
        probes.append({"name": "node_version", "status": "unavailable", "reason": "node executable not found"})
    if shutil.which("npm"):
        probes.append(run_probe("npm_version", ["npm", "--version"], timeout=30))
    else:
        probes.append({"name": "npm_version", "status": "unavailable", "reason": "npm executable not found"})

    probes.append(
        run_probe(
            "dependency_resolution",
            [python, "-m", "pip", "install", "--disable-pip-version-check", "--dry-run", "--ignore-installed", "."],
            timeout=300,
        )
    )
    probes.append(wheel_probe(python))
    probes.append(run_probe("python_compile", [python, "-m", "compileall", "-q", "omni_v2", "omni", "backend_fastapi"], timeout=120))
    tests = run_probe("python_tests", [python, "-m", "pytest", "-q"], timeout=900)
    tests["summary"] = pytest_counts(tests.get("stdout", "") + "\n" + tests.get("stderr", ""))
    probes.append(tests)
    live = run_probe(
        "backend_live_tests",
        [python, "-m", "pytest", "-q", "omni_v2/tests/test_mobile.py"],
        timeout=180,
    )
    live["summary"] = pytest_counts(live.get("stdout", "") + "\n" + live.get("stderr", ""))
    if live["status"] == "pass" and live["summary"].get("skipped", 0):
        live["status"] = "partial"
        live["reason"] = "backend live checks skipped because the baseline command did not start the backend"
    probes.append(live)
    probes.append(tool_probe(python))

    if shutil.which("npm") and frontend.exists():
        probes.append(run_probe("frontend_lint", ["npm", "run", "lint"], cwd=frontend, timeout=60, env={"CI": "1"}))
        package = read_json(frontend / "package.json")
        if "test" in package.get("scripts", {}):
            probes.append(run_probe("frontend_tests", ["npm", "test", "--", "--runInBand"], cwd=frontend, timeout=300, env={"CI": "1"}))
        else:
            probes.append({"name": "frontend_tests", "status": "not_configured", "reason": "frontend_next/package.json has no test script"})
        probes.append(run_probe("frontend_build", ["npm", "run", "build"], cwd=frontend, timeout=600, env={"CI": "1"}))
        audit = run_probe("frontend_dependency_audit", ["npm", "audit", "--json"], cwd=frontend, timeout=180, env={"CI": "1"})
        audit["summary"] = audit_summary(audit)
        probes.append(audit)
    else:
        for name in ("frontend_lint", "frontend_tests", "frontend_build", "frontend_dependency_audit"):
            probes.append({"name": name, "status": "unavailable", "reason": "npm or frontend_next is unavailable"})

    captured_at = dt.datetime.now(dt.timezone.utc).isoformat()
    result = {
        "schema_version": 1,
        "captured_at": captured_at,
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python_executable": relative(Path(python)) if Path(python).is_relative_to(ROOT) else python,
        },
        "source_digest": inventory["source_digest"],
        "authority_sha256": inventory["authority_sha256"],
        "inventory_counts": inventory["counts"],
        "probes": probes,
    }
    LOCAL_BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_BASELINE_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if publish:
        by_name = {probe["name"]: probe for probe in probes}
        wheel = by_name.get("wheel_build_and_contents", {}).get("wheel")
        tool_inventory = by_name.get("runtime_tool_inventory", {}).get("inventory")
        summary = {
            "schema_version": 1,
            "captured_at": captured_at,
            "host": result["host"],
            "source_digest": result["source_digest"],
            "authority_sha256": result["authority_sha256"],
            "inventory_counts": result["inventory_counts"],
            "probe_status": {probe["name"]: probe["status"] for probe in probes},
            "python_test_summary": by_name.get("python_tests", {}).get("summary"),
            "backend_live_test_summary": by_name.get("backend_live_tests", {}).get("summary"),
            "frontend_audit_summary": by_name.get("frontend_dependency_audit", {}).get("summary"),
            "wheel_summary": None
            if not wheel
            else {
                **{key: wheel[key] for key in ("filename", "bytes", "member_count", "python_file_count", "top_level_packages")},
                "python_members": [name for name in wheel["members"] if name.endswith(".py")],
            },
            "tool_inventory": tool_inventory,
            "full_local_result": relative(LOCAL_BASELINE_PATH),
        }
        publish.parent.mkdir(parents=True, exist_ok=True)
        publish.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return result


def print_summary(inventory: dict[str, Any], mode: str) -> None:
    counts = inventory["counts"]
    print(
        f"quality {mode}: {counts['capabilities']} capabilities, "
        f"{counts['core_workflows']} workflows, {counts['production_files']} production files, "
        f"{counts['test_files']} test files, {counts.get('fastapi_route_decorators', 0)} route decorators"
    )
    print(f"source digest: {inventory['source_digest']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("generate", help="validate authorities and regenerate deterministic artifacts")
    subparsers.add_parser("check", help="validate authorities and fail if generated artifacts drift")
    capture_parser = subparsers.add_parser("capture", help="generate artifacts and run environment baseline probes")
    capture_parser.add_argument(
        "--publish",
        type=Path,
        help="write a concise evidence JSON summary to this path; full output remains under quality/.local",
    )
    args = parser.parse_args()

    try:
        if args.command == "generate":
            inventory = generate(check=False)
            print_summary(inventory, "generated")
        elif args.command == "check":
            inventory = generate(check=True)
            print_summary(inventory, "check passed")
        else:
            publish = args.publish
            if publish and not publish.is_absolute():
                publish = ROOT / publish
            result = capture(publish=publish)
            inventory = read_json(INVENTORY_PATH)
            print_summary(inventory, "captured")
            print(f"full local baseline: {relative(LOCAL_BASELINE_PATH)}")
            if publish:
                print(f"published summary: {relative(publish)}")
            failures = [probe["name"] for probe in result["probes"] if probe["status"] not in {"pass"}]
            print("non-passing probes: " + (", ".join(failures) if failures else "none"))
        return 0
    except ValidationError as exc:
        print(f"quality validation failed:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
