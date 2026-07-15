import json
from datetime import datetime
from pathlib import Path


class SnapshotManager:
    """
    Responsible for retrieving and storing live game snapshots.

    Responsibilities

    - Refresh snapshots from the API
    - Save timestamped runtime snapshots
    - Maintain latest.json
    """

    def __init__(self, client):

        self.client = client

        self.snapshot_directory = Path("data/snapshots/runtime")

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

        snapshot_name = (
            f"{timestamp}_probe_{probe_id}.json"
        )

        snapshot_path = (
            self.snapshot_directory / snapshot_name
        )

        self._save_json(snapshot_path, snapshot)

        self._save_json(
            self.latest_snapshot,
            snapshot,
        )

        return snapshot, self.latest_snapshot

    def _save_json(self, path, data):
        """
        Save JSON to disk.
        """

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
            )