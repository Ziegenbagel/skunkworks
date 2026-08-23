from pathlib import Path

from src.application.paths import ApplicationPaths
from src.data import DataEngine


def test_platform_paths_follow_macos_conventions(tmp_path):
    paths = ApplicationPaths.discover({}, home=tmp_path, platform="darwin")

    assert paths.database == tmp_path / "Library/Application Support/Skunkworks/skunkworks.sqlite3"
    assert paths.config == tmp_path / "Library/Application Support/Skunkworks/config"
    assert paths.snapshots == tmp_path / "Library/Caches/Skunkworks/snapshots/runtime"
    assert paths.state == tmp_path / "Library/Logs/Skunkworks"


def test_home_override_keeps_private_development_data_together(tmp_path):
    paths = ApplicationPaths.discover(
        {"SKUNKWORKS_HOME": str(tmp_path / "private-runtime")},
        home=tmp_path,
        platform="linux",
    )

    assert paths.database == tmp_path / "private-runtime/data/skunkworks.sqlite3"
    assert paths.config_file("execution_policy.json") == (
        tmp_path / "private-runtime/config/execution_policy.json"
    )


def test_platform_paths_follow_windows_conventions(tmp_path):
    local = tmp_path / "LocalAppData"
    paths = ApplicationPaths.discover(
        {"LOCALAPPDATA": str(local)}, home=tmp_path, platform="win32",
    )

    assert paths.database == local / "Skunkworks/Data/skunkworks.sqlite3"
    assert paths.config == local / "Skunkworks/Config"
    assert paths.state == local / "Skunkworks/Logs"


def test_platform_paths_follow_linux_xdg_conventions(tmp_path):
    paths = ApplicationPaths.discover({}, home=tmp_path, platform="linux")

    assert paths.database == tmp_path / ".local/share/skunkworks/skunkworks.sqlite3"
    assert paths.config == tmp_path / ".config/skunkworks"
    assert paths.snapshots == tmp_path / ".cache/skunkworks/snapshots/runtime"


def test_legacy_migration_copies_verified_database_and_user_configuration(tmp_path):
    project = tmp_path / "checkout"
    legacy = DataEngine(project / "data/skunkworks.sqlite3")
    legacy.set_preference("private_test_marker", "preserved")
    (project / "config").mkdir()
    (project / "config/execution_policy.json").write_text('{"mode":"observe"}')
    paths = ApplicationPaths(
        tmp_path / "user/data", tmp_path / "user/config",
        tmp_path / "user/cache", tmp_path / "user/state",
    )

    report = paths.migrate_legacy(project)

    assert report["database"]
    assert report["configuration"] == ["execution_policy.json"]
    assert DataEngine(paths.database).get_preference("private_test_marker") == "preserved"
    assert legacy.get_preference("private_test_marker") == "preserved"


def test_legacy_migration_never_overwrites_existing_user_data(tmp_path):
    project = tmp_path / "checkout"
    legacy = DataEngine(project / "data/skunkworks.sqlite3")
    legacy.set_preference("marker", "legacy")
    paths = ApplicationPaths(
        tmp_path / "user/data", tmp_path / "user/config",
        tmp_path / "user/cache", tmp_path / "user/state",
    )
    current = DataEngine(paths.database)
    current.set_preference("marker", "current")

    report = paths.migrate_legacy(project)

    assert not report["database"]
    assert DataEngine(paths.database).get_preference("marker") == "current"
