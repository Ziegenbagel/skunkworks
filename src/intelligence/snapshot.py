from datetime import datetime
from pathlib import Path


class SnapshotAnalyzer:
    """Analyze runtime snapshot metadata."""

    def __init__(self, snapshot_path):
        self.snapshot_path = Path(snapshot_path)

    def get_snapshot_info(self, probe_name):
        """Return information about the current runtime snapshot."""

        modified = datetime.fromtimestamp(
            self.snapshot_path.stat().st_mtime
        )

        age = datetime.now() - modified

        age_seconds = int(age.total_seconds())

        if age_seconds < 60:
            age_text = f"{age_seconds} sec"

        elif age_seconds < 3600:
            age_text = f"{age_seconds // 60} min"

        else:
            age_text = (
                f"{age_seconds // 3600} hr "
                f"{(age_seconds % 3600) // 60} min"
            )

        return {
            "probe": probe_name,
            "last_refresh": modified.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "age": age_text,
            "fresh": age_seconds < 300,
        }