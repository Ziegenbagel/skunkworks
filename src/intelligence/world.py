class WorldModel:
    """
    Unified view of the current game world.
    """

    def __init__(
        self,
        player=None,
        fleet=None,
        snapshot=None,
        probe=None,
        sector=None,
    ):

        self.player = player
        self.fleet = fleet
        self.snapshot = snapshot

        self.probe = probe
        self.sector = sector