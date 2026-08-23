"""Run deterministic, non-packaging Skunkworks release-readiness checks."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md", "PRIVACY.md", "SECURITY.md", "SUPPORT.md", "ASSET_MANIFEST.md",
    "THIRD_PARTY_NOTICES.md", "RELEASE_NOTES.md",
    "docs/release-checklist.md", "docs/capability-matrix.md",
    "docs/installing-and-updating.md", "docs/licensing-decision.md",
    "docs/private-test-data.md",
    "docs/repository-publication.md",
    "docs/user-guide/assets/PRIVACY_REVIEW.md",
    "docs/user-guide/Skunkworks_Operator_Manual.docx",
)


def audit(root=ROOT):
    root = Path(root)
    checks = []

    def record(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    for relative in REQUIRED_FILES:
        record(f"file:{relative}", (root / relative).is_file(), relative)

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    record(
        "metadata:description",
        "Add your description here" not in pyproject,
        "pyproject description must be product-specific",
    )
    config = (root / "src/config.py").read_text(encoding="utf-8")
    project_version = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    app_version = re.search(r'^APP_VERSION = "([^"]+)"', config, re.MULTILINE)
    versions_match = bool(
        project_version and app_version
        and project_version.group(1) == app_version.group(1)
    )
    record("metadata:version", versions_match, "pyproject and UI versions must match")

    license_files = tuple(
        name for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")
        if (root / name).is_file()
    )
    record(
        "legal:license",
        bool(license_files),
        "A distribution license must be selected before public release.",
    )
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    tracked_secrets = tuple(sorted(
        relative for relative in tracked
        if relative in {".env", "sector_snapshot.json"}
        or relative.endswith((".sqlite", ".sqlite3", ".db", ".log"))
        or relative.startswith("data/snapshots/")
        or relative.startswith("data/backups/")
    ))
    record(
        "privacy:local-files",
        not tracked_secrets,
        "Remove local credential/snapshot files from release staging: "
        + (", ".join(tracked_secrets) or "none found"),
    )
    screenshot_review = root / "docs/user-guide/assets/PRIVACY_REVIEW.md"
    screenshot_text = (
        screenshot_review.read_text(encoding="utf-8")
        if screenshot_review.is_file() else ""
    )
    record(
        "privacy:manual-screenshots",
        bool(re.search(
            r"^Status:\s*APPROVED SYNTHETIC DATA\s*$",
            screenshot_text,
            re.MULTILINE,
        )),
        "Operator Manual screenshots must be recaptured with synthetic data.",
    )

    execution_policy = json.loads(
        (root / "config/execution_policy.json").read_text(encoding="utf-8")
    )
    record(
        "privacy:policy-template",
        execution_policy.get("default", {}).get("mode") == "observe"
        and not execution_policy.get("default", {}).get("liveExecutionEnabled")
        and not execution_policy.get("probes"),
        "Tracked execution policy must be Observe Only with no probe IDs.",
    )
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--allow-documentation-work-in-progress",
        action="store_true",
        help="Keep manual screenshot/output failures visible but non-blocking for development CI.",
    )
    arguments = parser.parse_args(argv)
    checks = audit()
    if arguments.json:
        print(json.dumps(checks, indent=2))
    else:
        for check in checks:
            print(f"{'PASS' if check['ok'] else 'FAIL'}  {check['name']}: {check['detail']}")
    blocking = checks
    if arguments.allow_documentation_work_in_progress:
        allowed = {
            "file:docs/user-guide/Skunkworks_Operator_Manual.docx",
            "privacy:manual-screenshots",
        }
        blocking = [check for check in checks if check["name"] not in allowed]
    return 0 if all(check["ok"] for check in blocking) else 1


if __name__ == "__main__":
    raise SystemExit(main())
