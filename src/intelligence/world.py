class WorldModel:
    """
    Unified view of the current game world.
    """

    def __init__(
        self,
        player=None,
        fleet=None,
        snapshot=None,
        inventory=None,
        resources=None,
    ):
        self.player = player
        self.fleet = fleet
        self.snapshot = snapshot
        self.inventory = inventory
        self.resources = resources