#!/usr/bin/env python3
"""Check that local file targets in Markdown links exist.

This intentionally checks path existence rather than heading fragments. API paths,
external schemes, and fragment-only links are outside this local-file drift check.
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
HTML_LINK = re.compile(r"\b(?:href|src)=[\"']([^\"']+)[\"']", re.IGNORECASE)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def markdown_files(inputs: list[str]) -> list[Path]:
    files: set[Path] = set()
    for item in inputs:
        path = (ROOT / item).resolve() if not Path(item).is_absolute() else Path(item).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError:
            raise ValueError(f"input is outside repository: {item}")
        if not path.exists():
            raise ValueError(f"input does not exist: {item}")
        if path.is_dir():
            files.update(candidate for candidate in path.rglob("*.md") if candidate.is_file())
        elif path.suffix.lower() == ".md":
            files.add(path)
    return sorted(files)


def normalize_inline_target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    # Markdown permits an optional quoted title after the destination. shlex handles
    # common cases without treating escaped spaces as separate targets.
    try:
        parts = shlex.split(raw)
    except ValueError:
        parts = raw.split()
    return parts[0] if parts else ""


def without_code(text: str) -> str:
    # Link-like PowerShell/Python/transcript syntax inside examples is not Markdown.
    text = re.sub(r"^\s*(```|~~~).*?^\s*\1[^\n]*$", "", text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def targets(text: str) -> list[str]:
    text = without_code(text)
    found = [normalize_inline_target(match.group(1)) for match in INLINE_LINK.finditer(text)]
    found.extend(match.group(1).strip("<>") for match in REFERENCE_LINK.finditer(text))
    found.extend(match.group(1) for match in HTML_LINK.finditer(text))
    return found


def target_path(source: Path, raw: str) -> Path | None:
    raw = raw.strip()
    if not raw or raw.startswith("#") or raw.startswith("/") or SCHEME.match(raw):
        return None
    if any(marker in raw for marker in ("{{", "}}", "${")):
        return None
    split = urlsplit(raw)
    decoded = unquote(split.path)
    if not decoded:
        return None
    return (source.parent / decoded).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true", help="document that only local targets are checked")
    parser.add_argument("paths", nargs="+", help="Markdown files or directories, relative to repository root")
    args = parser.parse_args()

    try:
        files = markdown_files(args.paths)
    except ValueError as exc:
        print(f"link check failed: {exc}", file=sys.stderr)
        return 2

    failures: list[str] = []
    checked = 0
    for source in files:
        text = source.read_text(encoding="utf-8", errors="replace")
        for raw in targets(text):
            candidate = target_path(source, raw)
            if candidate is None:
                continue
            checked += 1
            try:
                candidate.relative_to(ROOT)
            except ValueError:
                failures.append(f"{source.relative_to(ROOT)}: target escapes repository: {raw}")
                continue
            if not candidate.exists():
                failures.append(f"{source.relative_to(ROOT)}: missing target: {raw}")

    if failures:
        print("local Markdown link check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"local Markdown link check passed: {len(files)} files, {checked} local targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
