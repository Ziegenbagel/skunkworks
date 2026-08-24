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
