from src.operations.fleet import (
    FleetService,
)

from src.operations.manufacturing import (
    ManufacturingService,
)

from src.operations.travel import (
    TravelService,
)

from src.operations.probes import (
    ProbeService,
)

from src.operations.snapshots import (
    SnapshotService,
)
from src.operations.inventory import InventoryService
from src.operations.mining import MiningService
from src.operations.galaxy import GalaxyService


class Operations:
    """
    Coordinates access to all operational
    services.
    """

    def __init__(
        self,
        world,
        recipes,
    ):

        self.world = world

        self.fleet = FleetService(
            world
        )
    
        self.manufacturing = (
            ManufacturingService(
                world,
                recipes,
            )
        )

        self.travel = (
            TravelService(
                world
            )
        )

        self.probes = (
            ProbeService(
                world
            )
        )

        self.snapshots = (
            SnapshotService(
                world
            )
        )

        self.inventory = InventoryService(world)
        self.mining = MiningService(world)
        self.galaxy = GalaxyService(world)
