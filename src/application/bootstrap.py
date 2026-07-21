from src.api.client import (
    GameClient,
)
from src.snapshot.manager import (
    SnapshotManager,
)
from src.intelligence.world_builder import (
    WorldBuilder,
)


class Application:
    """
    Coordinates construction of the
    application's runtime components.
    """

    def __init__(
        self,
    ):

        self.client = GameClient()

        self.snapshot_manager = (
            SnapshotManager(
                self.client
            )
        )

        self.builder = WorldBuilder()

    def build_world(
        self,
    ):
        """
        Build and return the current
        WorldModel.
        """

        pass