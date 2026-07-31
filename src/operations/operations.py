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
from src.safety.policy import TravelSafetyPolicy
from src.safety.travel import TravelSafetyService
from src.safety.resources import (
    ResourceSafetyPolicy,
    ResourceSustainabilityService,
)


class Operations:
    """
    Coordinates access to all operational
    services.
    """

    def __init__(
        self,
        world,
        recipes,
        travel_safety_policy=None,
        data_engine=None,
        resource_safety_policy=None,
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
        self.travel_safety = TravelSafetyService(
            world,
            self.travel,
            travel_safety_policy or TravelSafetyPolicy(),
        )
        self.resource_sustainability = (
            ResourceSustainabilityService(
                world,
                data_engine,
                resource_safety_policy
                or ResourceSafetyPolicy(),
            )
        )
