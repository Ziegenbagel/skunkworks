"""Cross-platform writable locations and one-time legacy-data migration."""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApplicationPaths:
    data: Path
    config: Path
    cache: Path
    state: Path

    @classmethod
    def discover(cls, environment=None, home=None, platform=None):
        environment = os.environ if environment is None else environment
        home = Path.home() if home is None else Path(home)
        platform = sys.platform if platform is None else platform
        override = environment.get("SKUNKWORKS_HOME")
        if override:
            root = Path(override).expanduser()
            return cls(
                root / "data", root / "config", root / "cache", root / "state",
            )
        if platform == "darwin":
            support = home / "Library" / "Application Support" / "Skunkworks"
            return cls(
                support, support / "config",
                home / "Library" / "Caches" / "Skunkworks",
                home / "Library" / "Logs" / "Skunkworks",
            )
        if os.name == "nt" or platform.startswith("win"):
            local = Path(environment.get(
                "LOCALAPPDATA", home / "AppData" / "Local",
            )) / "Skunkworks"
            return cls(local / "Data", local / "Config", local / "Cache", local / "Logs")
        data = Path(environment.get("XDG_DATA_HOME", home / ".local" / "share")) / "skunkworks"
        config = Path(environment.get("XDG_CONFIG_HOME", home / ".config")) / "skunkworks"
        cache = Path(environment.get("XDG_CACHE_HOME", home / ".cache")) / "skunkworks"
        state = Path(environment.get("XDG_STATE_HOME", home / ".local" / "state")) / "skunkworks"
        return cls(data, config, cache, state)

    @property
    def database(self):
        return self.data / "skunkworks.sqlite3"

    @property
    def snapshots(self):
        return self.cache / "snapshots" / "runtime"

    @property
    def backups(self):
        return self.data / "backups"

    def config_file(self, name):
        return self.config / name

    def ensure(self):
        for directory in (self.data, self.config, self.cache, self.state, self.backups):
            directory.mkdir(parents=True, exist_ok=True)
        return self

    def migrate_legacy(self, project_root):
        """Copy user-owned legacy state out of a source/install directory once."""

        project_root = Path(project_root)
        self.ensure()
        report = {"database": False, "configuration": [], "snapshots": False}
        legacy_database = project_root / "data" / "skunkworks.sqlite3"
        if legacy_database.is_file() and not self.database.exists():
            partial = self.database.with_suffix(".sqlite3.partial")
            if partial.exists():
                partial.unlink()
            try:
                with sqlite3.connect(legacy_database) as source, sqlite3.connect(partial) as target:
                    source.backup(target)
                    if target.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                        raise sqlite3.DatabaseError(
                            "Legacy database backup failed verification."
                        )
                os.replace(partial, self.database)
            finally:
                if partial.exists():
                    partial.unlink()
            report["database"] = True

        # Configuration is migrated only alongside a legacy runtime database;
        # packaged config files are safe templates, not user state.
        if legacy_database.is_file():
            for name in (
                "execution_policy.json", "resource_safety.json", "travel_safety.json",
            ):
                source = project_root / "config" / name
                destination = self.config_file(name)
                if source.is_file() and not destination.exists():
                    shutil.copy2(source, destination)
                    report["configuration"].append(name)
        return report


def application_paths():
    return ApplicationPaths.discover()
