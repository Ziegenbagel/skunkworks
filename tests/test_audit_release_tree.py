from pathlib import Path

from tools.audit_release_tree import findings


def test_audit_ignores_python_credential_expressions(tmp_path: Path):
    source = tmp_path / "controller.py"
    source.write_text("api_key = self.credential_store.get()\n", encoding="utf-8")

    assert findings(tmp_path) == []


def test_audit_rejects_literal_api_key(tmp_path: Path):
    source = tmp_path / "settings.py"
    source.write_text('api_key = "example-secret-123456"\n', encoding="utf-8")

    assert findings(tmp_path) == ["credential-like content: settings.py"]


def test_audit_does_not_scan_compiled_windows_binaries_as_text(tmp_path: Path):
    binary = tmp_path / "_ssl.pyd"
    binary.write_bytes(b"\x00api_key='binary-coincidence-123456'\xff")

    assert findings(tmp_path) == []
