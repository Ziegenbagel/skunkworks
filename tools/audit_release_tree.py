"""Reject private/runtime material from a source or packaged release tree."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


FORBIDDEN_SUFFIXES = (
    ".db", ".sqlite", ".sqlite3", ".sqlite3-shm", ".sqlite3-wal", ".log",
)
FORBIDDEN_NAMES = {".env", "sector_snapshot.json"}
SECRET_PATTERNS = (
    re.compile(rb"(?i)authorization\s*[:=]\s*bearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(rb"(?i)(?:api[-_ ]?key|token|secret)\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
)


def findings(root):
    root = Path(root)
    problems = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            try:
                path.resolve(strict=True).relative_to(root.resolve())
            except (FileNotFoundError, ValueError):
                problems.append(f"external or broken symbolic link: {path.relative_to(root)}")
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        lowered = path.name.lower()
        if lowered in FORBIDDEN_NAMES or lowered.endswith(FORBIDDEN_SUFFIXES):
            problems.append(f"private/runtime filename: {relative}")
            continue
        is_distribution_metadata = any(
            part.endswith(".dist-info") for part in relative.parts
        )
        if not is_distribution_metadata and path.stat().st_size <= 2 * 1024 * 1024:
            content = path.read_bytes()
            if any(pattern.search(content) for pattern in SECRET_PATTERNS):
                problems.append(f"credential-like content: {relative}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    arguments = parser.parse_args(argv)
    problems = findings(arguments.root)
    if problems:
        for problem in problems:
            print(f"FAIL  {problem}")
        return 1
    print(f"PASS  no private/runtime material found in {arguments.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
