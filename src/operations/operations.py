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
from src.operations.mannies import MannyService
from src.operations.containers import ContainerService
from src.operations.depots import DepotService
from src.operations.exploration import ExplorationService
from src.operations.health import OperationalHealthService
from src.operations.messaging import EventService, MessagingService, MissionService
from src.operations.predictions import PredictionService
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
        capabilities=None,
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
        self.mannies = MannyService(world)
        self.containers = ContainerService(world)
        self.depots = DepotService(
            world,
            self.mannies,
            self.containers,
        )
        self.galaxy = GalaxyService(world)
        self.messaging = MessagingService(data_engine, capabilities) if data_engine else None
        self.missions = MissionService(data_engine, capabilities) if data_engine else None
        self.events = EventService(data_engine) if data_engine else None
        self.exploration = ExplorationService(self)
        self.predictions = PredictionService(self)
        self.health = OperationalHealthService(self)
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
