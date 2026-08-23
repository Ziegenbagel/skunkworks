from tools.audit_release_tree import findings


def test_release_tree_audit_rejects_runtime_and_secret_material(tmp_path):
    (tmp_path / "skunkworks.sqlite3").write_bytes(b"database")
    (tmp_path / "notes.txt").write_text("API key=super-secret-value")

    problems = findings(tmp_path)

    assert any("skunkworks.sqlite3" in problem for problem in problems)
    assert any("notes.txt" in problem for problem in problems)


def test_release_tree_audit_accepts_normal_release_files(tmp_path):
    (tmp_path / "README.md").write_text("Skunkworks release")
    (tmp_path / "app.bin").write_bytes(b"compiled application")

    assert findings(tmp_path) == []
