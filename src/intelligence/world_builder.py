from src.intelligence.fleet import (
    FleetAnalyzer,
)
from src.intelligence.inventory import (
    InventoryAnalyzer,
)
from src.intelligence.resources import (
    ResourceAnalyzer,
)
from src.intelligence.snapshot import (
    SnapshotAnalyzer,
)
from src.intelligence.world import (
    WorldModel,
)


class WorldBuilder:
    """
    Construct a normalized WorldModel
    from the latest game snapshot.
    """

    def build(
        self,
        player,
        probe_data,
        snapshot,
        snapshot_path,
        probe_name,
    ):

        resource_analyzer = ResourceAnalyzer()

        inventory_analyzer = InventoryAnalyzer()

        snapshot_analyzer = SnapshotAnalyzer(
            snapshot_path
        )
        fleet_analyzer = FleetAnalyzer()

        world = WorldModel()

        world.player = player

        world.fleet = (
            fleet_analyzer.get_fleet(
                probe_data
            )
        )

        world.resources = (
            resource_analyzer
            .get_sector_resources(snapshot)
        )

        world.inventory = (
            inventory_analyzer
            .get_inventory(snapshot)
        )

        world.snapshot = (
            snapshot_analyzer
            .get_snapshot_info(probe_name)
        )

        return world