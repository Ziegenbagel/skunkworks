import json
from datetime import datetime, timedelta
from pathlib import Path

from src.snapshot.manager import SnapshotManager


class Client:
    def get_sector(self, probe_id):
        return {"sector": {"probeId": probe_id, "objects": ["x"]}}


def test_refresh_keeps_latest_but_rate_limits_timestamped_archives(tmp_path):
    manager = SnapshotManager(Client(), tmp_path, archive_interval_minutes=60)

    _, first = manager.refresh_sector(7)
    _, second = manager.refresh_sector(7)

    archives = [
        path for path in tmp_path.glob("*_probe_7.json")
        if not path.name.startswith("latest_probe_")
    ]
    assert first == second == tmp_path / "latest_probe_7.json"
    assert len(archives) == 1
    assert json.loads(first.read_text())["sector"]["probeId"] == 7
    assert "\n" not in first.read_text()


def test_prune_archives_enforces_age_and_per_probe_limit(tmp_path):
    manager = SnapshotManager(
        Client(), tmp_path, retention_days=7, maximum_archives_per_probe=2,
    )
    now = datetime.now()
    paths = []
    for index in range(4):
        path = tmp_path / f"2026-08-{index + 1:02d}_00-00-00_probe_7.json"
        path.write_text("{}")
        timestamp = (now - timedelta(days=index)).timestamp()
        path.touch()
        import os
        os.utime(path, (timestamp, timestamp))
        paths.append(path)

    removed = manager.prune_archives(7, now=now)

    assert removed == 2
    assert len(manager._archives(7)) == 2
