from src.operations.fleet import (
    FleetService,
)

from src.operations.manufacturing import (
    ManufacturingService,
)


class Operations:
    """
    Coordinates access to all operational
    services.
    """

    def __init__(
        self,
        world,
    ):

        self.world = world

        self.fleet = FleetService(
            world
        )
    
        self.manufacturing = (
            ManufacturingService(
                world
            )
        )