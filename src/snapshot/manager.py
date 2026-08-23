import json
from datetime import datetime, timedelta
from pathlib import Path

from src.application.paths import application_paths

from src import snapshot


class SnapshotManager:
    """
    Responsible for retrieving and storing live game snapshots.

    Responsibilities

    - Refresh snapshots from the API
    - Save timestamped runtime snapshots
    - Maintain latest.json
    """

    def __init__(
        self, client, snapshot_directory=None, *, archive_interval_minutes=60,
        retention_days=7, maximum_archives_per_probe=168,
    ):

        self.client = client

        self.snapshot_directory = Path(
            snapshot_directory or application_paths().snapshots
        )
        self.archive_interval = timedelta(
            minutes=max(1, int(archive_interval_minutes))
        )
        self.retention_days = max(1, int(retention_days))
        self.maximum_archives_per_probe = max(
            1, int(maximum_archives_per_probe)
        )

        self.latest_snapshot = (
            self.snapshot_directory / "latest.json"
        )

        self.snapshot_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def refresh_sector(self, probe_id):
        """
        Download a fresh sector snapshot.
        """

        snapshot = self.client.get_sector(probe_id)

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        probe_latest = self.snapshot_directory / f"latest_probe_{probe_id}.json"
        self._save_json(probe_latest, snapshot)
        self._save_json(self.latest_snapshot, snapshot)

        # The latest files are sufficient for ordinary world construction.
        # Keep timestamped payloads only as a bounded diagnostic trail instead
        # of writing another large, permanent file on every refresh.
        newest_archive = self._newest_archive(probe_id)
        now = datetime.now()
        if (
            newest_archive is None
            or now - datetime.fromtimestamp(newest_archive.stat().st_mtime)
            >= self.archive_interval
        ):
            snapshot_path = self.snapshot_directory / (
                f"{timestamp}_probe_{probe_id}.json"
            )
            self._save_json(snapshot_path, snapshot)
            self.prune_archives(probe_id)

        return snapshot, probe_latest

    def _save_json(self, path, data):
        """
        Save JSON to disk.
        """

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(data, file, separators=(",", ":"))

    def _archives(self, probe_id):
        return sorted(
            (
                path for path in self.snapshot_directory.glob(
                    f"*_probe_{int(probe_id)}.json"
                )
                if not path.name.startswith("latest_probe_")
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    def _newest_archive(self, probe_id):
        return next(iter(self._archives(probe_id)), None)

    def prune_archives(self, probe_id=None, *, now=None):
        """Remove expired diagnostic snapshots while preserving latest files."""

        now = now or datetime.now()
        cutoff = now - timedelta(days=self.retention_days)
        if probe_id is None:
            probe_ids = {
                int(path.stem.rsplit("_probe_", 1)[1])
                for path in self.snapshot_directory.glob("*_probe_*.json")
                if not path.name.startswith("latest_probe_")
            }
        else:
            probe_ids = {int(probe_id)}
        removed = 0
        for current_probe_id in probe_ids:
            for position, path in enumerate(self._archives(current_probe_id)):
                expired = datetime.fromtimestamp(path.stat().st_mtime) < cutoff
                over_limit = position >= self.maximum_archives_per_probe
                if expired or over_limit:
                    path.unlink(missing_ok=True)
                    removed += 1
        return removed
