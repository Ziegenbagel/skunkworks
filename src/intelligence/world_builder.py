from src.intelligence.fleet import (
    FleetAnalyzer,
)

from src.intelligence.probe import (
    ProbeAnalyzer,
)

from src.intelligence.sector import (
    SectorAnalyzer,
)

from src.intelligence.snapshot import (
    SnapshotAnalyzer,
)

from src.intelligence.world import (
    WorldModel,
)

from datetime import datetime


class WorldBuilder:
    """
    Construct a normalized WorldModel
    from live game data.
    """

    def __init__(self):

        self.fleet_analyzer = (
            FleetAnalyzer()
        )

        self.probe_analyzer = (
            ProbeAnalyzer()
        )

        self.sector_analyzer = (
            SectorAnalyzer()
        )

    def build(
        self,
        player,
        probe_data,
        probe,
        snapshot,
        snapshot_path,
        probe_name,
        mannies=None,
    ):

        snapshot_analyzer = (
            SnapshotAnalyzer(
                snapshot_path
            )
        )

        world = WorldModel()

        world.player = player

        world.fleet = (
            self.fleet_analyzer.get_fleet(
                probe_data
            )
        )

        # The detailed sector endpoint is the authoritative inventory source.
        # GET /probe may contain only its compact resource summary, which made
        # crafted equipment disappear from the Resources workspace even though
        # it was present in the just-fetched sector snapshot.
        probe_with_inventory = dict(probe)
        if isinstance(snapshot, dict) and isinstance(snapshot.get("inventory"), dict):
            probe_with_inventory["inventory"] = snapshot["inventory"]

        world.probe = (
            self.probe_analyzer.analyze(
                probe_with_inventory
            )
        )

        world.sector = (
            self.sector_analyzer.analyze(
                snapshot
            )
        )

        if mannies is not None:
            world.mannies = mannies

        world.snapshot = (
            snapshot_analyzer.get_snapshot_info(
                probe_name
            )
        )

        return world

    def build_limited(
        self,
        player,
        probe_data,
        probe,
        probe_name,
        mannies=None,
    ):
        """Build safe state for an owned probe outside telemetry range."""

        world = WorldModel()
        world.player = player
        world.fleet = self.fleet_analyzer.get_fleet(
            probe_data
        )
        world.probe = self.probe_analyzer.analyze(probe)
        world.sector = {
            "resources": [],
            "snapshot": None,
        }
        world.snapshot = {
            "probe": probe_name,
            # This is still a current focused-probe refresh. Only the detailed
            # sector view is unavailable while moving/out of coverage; calling
            # the entire probe snapshot stale hides live movement telemetry.
            "last_refresh": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "age": "0 sec",
            "age_seconds": 0,
            "fresh": True,
            "sector_available": False,
        }

        if mannies is not None:
            world.mannies = mannies

        return world
