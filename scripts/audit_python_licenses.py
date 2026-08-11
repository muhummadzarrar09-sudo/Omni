#!/usr/bin/env python3
"""Inventory licenses for every distribution in an exact hashed lock.

This is an inventory/completeness gate, not legal advice. Ambiguous or
copyleft-related metadata is preserved under ``review_required`` rather than
silently converted into a permissive-license claim.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIREMENT = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;]+)")
REVIEW_MARKERS = ("general public license", "gpl", "proprietary", "unknown")


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def load_lock(path: Path) -> dict[str, tuple[str, str]]:
    packages: dict[str, tuple[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = REQUIREMENT.match(line)
        if match:
            display_name, version = match.groups()
            packages[canonical_name(display_name)] = (display_name, version)
    if not packages:
        raise ValueError(f"no exact requirements found in {path}")
    return packages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lock", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    lock = args.lock.resolve()
    expected = load_lock(lock)

    with tempfile.TemporaryDirectory(prefix="omni-license-audit-") as temporary:
        inventory_path = Path(temporary) / "inventory.json"
        command = [
            sys.executable,
            "-m",
            "piplicenses",
            "--with-system",
            "--format=json",
            "--packages",
            *[item[0] for item in expected.values()],
            "--output-file",
            str(inventory_path),
        ]
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(
                f"pip-licenses failed ({completed.returncode})\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        raw = json.loads(inventory_path.read_text(encoding="utf-8"))

    found: dict[str, dict[str, str]] = {}
    mismatches: list[dict[str, str]] = []
    for item in raw:
        name = canonical_name(item["Name"])
        if name not in expected:
            continue
        expected_version = expected[name][1]
        if item["Version"] != expected_version:
            mismatches.append(
                {
                    "name": item["Name"],
                    "expected": expected_version,
                    "installed": item["Version"],
                }
            )
            continue
        found[name] = {
            "name": item["Name"],
            "version": item["Version"],
            "license": item["License"],
        }

    # ``--with-system`` can expose both base-interpreter and virtualenv copies
    # of pip/setuptools/wheel. An exact lock match wins; only unresolved version
    # mismatches are failures.
    mismatches = [item for item in mismatches if canonical_name(item["name"]) not in found]
    missing = [expected[name][0] for name in sorted(set(expected) - set(found))]
    unknown = [
        item for item in found.values() if item["license"].strip().lower() in {"", "unknown"}
    ]
    reviews = [
        item
        for item in found.values()
        if any(marker in item["license"].lower() for marker in REVIEW_MARKERS)
    ]
    passed = not (missing or mismatches or unknown)
    report = {
        "schema_version": 1,
        "status": "pass" if passed else "fail",
        "scope": "exact installed distributions from the supplied hashed lock",
        "lock": str(lock),
        "expected_distribution_count": len(expected),
        "inventoried_distribution_count": len(found),
        "missing": missing,
        "version_mismatches": mismatches,
        "unknown_licenses": unknown,
        "review_required": reviews,
        "legal_claim": "Inventory completeness only; this report is not legal advice or a license-compatibility certification.",
        "distributions": sorted(found.values(), key=lambda item: canonical_name(item["name"])),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
