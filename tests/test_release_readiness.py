from pathlib import Path

from tools.release_readiness import audit


def test_release_readiness_has_expected_non_packaging_gates():
    checks = {check["name"]: check for check in audit()}

    assert checks["metadata:description"]["ok"]
    assert checks["metadata:version"]["ok"]
    assert checks["privacy:local-files"]["ok"]
    assert checks["privacy:policy-template"]["ok"]
    assert checks["privacy:manual-screenshots"]["ok"]
    assert checks["legal:license"]["ok"]
    assert checks["file:NOTICE"]["ok"]
    assert all(
        check["ok"] for name, check in checks.items()
        if name.startswith("file:")
    )


def test_pep_639_license_expression_is_not_combined_with_legacy_classifier():
    metadata = Path("pyproject.toml").read_text()

    assert 'license = "GPL-3.0-only"' in metadata
    assert '"License ::' not in metadata


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
