"""Collect the exact installed runtime dependency inventory and license files."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import re
import shutil
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


RUNTIME_ROOTS = ("pyside6", "requests", "python-dotenv", "keyring")
LICENSE_NAMES = re.compile(r"(?i)(?:^|/)(?:license|copying|notice|authors?)(?:[._-].*)?$")


def runtime_distributions():
    available = {
        canonicalize_name(distribution.metadata["Name"]): distribution
        for distribution in metadata.distributions()
        if distribution.metadata.get("Name")
    }
    pending = [canonicalize_name(name) for name in RUNTIME_ROOTS]
    selected = {}
    while pending:
        name = pending.pop()
        if name in selected or name not in available:
            continue
        distribution = available[name]
        selected[name] = distribution
        for raw_requirement in distribution.requires or ():
            requirement = Requirement(raw_requirement)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            pending.append(canonicalize_name(requirement.name))
    return [selected[name] for name in sorted(selected)]


def collect(output_directory: Path) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    license_root = output_directory / "licenses"
    license_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for distribution in runtime_distributions():
        name = distribution.metadata["Name"]
        license_expression = (
            distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or "Not declared in package metadata"
        ).strip()
        copied = []
        destination = license_root / f"{canonicalize_name(name)}-{distribution.version}"
        for item in distribution.files or ():
            relative = Path(str(item))
            if not LICENSE_NAMES.search(relative.as_posix()):
                continue
            source = Path(distribution.locate_file(item))
            if not source.is_file():
                continue
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / relative.name
            shutil.copy2(source, target)
            copied.append(target.relative_to(output_directory).as_posix())
        rows.append((name, distribution.version, license_expression, copied))

    inventory = output_directory / "DEPENDENCY_INVENTORY.md"
    lines = [
        "# Packaged Runtime Dependency Inventory",
        "",
        "Generated from the exact Python environment used to build this artifact.",
        "",
        "| Component | Version | Declared license | Collected files |",
        "|---|---:|---|---|",
    ]
    for name, version, expression, copied in rows:
        safe_expression = expression.replace("|", "OR").replace("\n", " ")
        files = "<br>".join(f"`{path}`" for path in copied) or "Package metadata only"
        lines.append(f"| {name} | {version} | {safe_expression} | {files} |")
    inventory.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inventory


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args(argv)
    inventory = collect(arguments.output)
    print(inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
