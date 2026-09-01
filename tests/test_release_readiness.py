from pathlib import Path
import re
import tomllib

from tools.release_readiness import audit


def test_release_readiness_has_expected_non_packaging_gates():
    checks = {check["name"]: check for check in audit()}

    assert checks["metadata:description"]["ok"]
    assert checks["metadata:version"]["ok"]
    assert checks["metadata:lock-version"]["ok"]
    assert checks["privacy:local-files"]["ok"]
    assert checks["privacy:policy-template"]["ok"]
    assert checks["privacy:manual-screenshots"]["ok"]
    assert checks["legal:license"]["ok"]
    assert checks["file:NOTICE"]["ok"]
    assert all(
        check["ok"] for name, check in checks.items()
        if name.startswith("file:")
    )


def test_published_release_notes_are_operator_facing_bullet_lists():
    notes = Path("RELEASE_NOTES.md").read_text(encoding="utf-8")
    sections = notes.split("\n## Skunkworks ")[1:]
    versions = set(re.findall(r"^## Skunkworks (\d+\.\d+\.\d+)$", notes, re.MULTILINE))

    assert sections
    assert versions == {f"1.0.{patch}" for patch in range(12)}
    assert ".dev" not in notes.casefold()
    assert "development branch" not in notes.casefold()
    assert "tests pass" not in notes.casefold()
    assert "reviews and integrates" not in notes.casefold()
    assert "analyzed api" not in notes.casefold()
    for section in sections:
        lines = section.splitlines()
        body = [line for line in lines[1:] if line.strip()]
        assert body
        assert body[0].startswith("- ")
        assert all(
            line.startswith("- ") or line.startswith("  ") for line in body
        )


def test_pep_639_license_expression_is_not_combined_with_legacy_classifier():
    metadata = Path("pyproject.toml").read_text()

    assert 'license = "GPL-3.0-only"' in metadata
    assert '"License ::' not in metadata


def test_source_distribution_explicitly_packages_launcher_and_ui_assets():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["scripts"]["skunkworks"] == "src.ui.app:run"
    assert metadata["build-system"]["build-backend"] == "setuptools.build_meta"
    assert metadata["tool"]["setuptools"]["packages"]["find"]["include"] == [
        "src", "src.*",
    ]
    assert metadata["tool"]["setuptools"]["package-data"]["src.ui"] == [
        "qml/**/*", "assets/**/*",
    ]


def test_upgrade_guide_preserves_accumulated_user_data():
    guide = Path("docs/installing-and-updating.md").read_text(encoding="utf-8")

    assert "Safe update procedure — keep your accumulated data" in guide
    assert "delete the Skunkworks user-data folder" in guide
    assert "do not set a new" in guide and "`SKUNKWORKS_HOME`" in guide


def test_release_candidate_build_excludes_private_and_development_directories():
    workflow = Path(".github/workflows/release-candidate.yml").read_text()
    assert "python -m tools.build_release_candidate --clean" in workflow
    builder = Path("tools/build_release_candidate.py").read_text()
    for forbidden in ("/.venv", "'data'=data", "'env'=env", "'output'=output", "'private'=private"):
        assert forbidden not in builder
    assert "Skunkworks_Operator_Manual.docx" in builder
    assert "docs/user-guide/CHANGELOG.md" in builder
    assert "ROOT / 'LICENSE'" in builder
    assert "ROOT / 'NOTICE'" in builder
    assert "PySide6.QtMultimedia" in builder
    workflow = Path(".github/workflows/release-candidate.yml").read_text()
    assert "tools.collect_release_licenses" in workflow
