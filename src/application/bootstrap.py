from src.api.client import (
    GameClient,
)
from src.snapshot.manager import (
    SnapshotManager,
)
from src.intelligence.world_builder import (
    WorldBuilder,
)
from src.api.capabilities import GameCapabilities
from src.application.probe_selector import ProbeSelector
from src.recipes.manager import RecipeManager


class Application:
    """
    Coordinates construction of the
    application's runtime components.
    """

    def __init__(
        self,
    ):

        self.client = GameClient()
        self.capabilities = GameCapabilities(
            self.client
        )

        self.snapshot_manager = (
            SnapshotManager(
                self.client
            )
        )

        self.builder = WorldBuilder()
        self.recipes = RecipeManager()
        self.probe_selector = ProbeSelector()

    def select_probe(
        self,
        probe_data,
        arguments=None,
        preferred_probe_id=None,
    ):
        """Resolve the focused probe for this application session."""

        return self.probe_selector.select(
            probe_data,
            arguments,
            preferred_probe_id,
        )

    def build_world(
        self,
    ):
        """
        Build and return the current
        WorldModel.
        """

        raise NotImplementedError(
            "Use WorldBuilder with an explicitly selected probe."
        )
