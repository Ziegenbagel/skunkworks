from pathlib import Path
import sys

project_root = (
    Path(__file__)
    .resolve()
    .parents[2]
)

sys.path.insert(
    0,
    str(project_root),
)

from src.operations.operations import (
    Operations,
)

from src.intelligence.world_builder import (
    WorldBuilder,
)

from src.api.client import (
    GameClient,
)

from src.snapshot.manager import (
    SnapshotManager,
)

print(
    operations.fleet.total_probes()
)

print(
    operations.fleet.idle_count()
)

print(
    operations.fleet.active_count()
)

print(
    operations.fleet.probe_names()
)