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
        mannies=None,
        galaxy=None,
    ):

        self.player = player
        self.fleet = fleet
        self.snapshot = snapshot

        self.probe = probe
        self.sector = sector
        self.mannies = mannies or {
            "mannies": [],
            "nextUsefulRefreshDelayMs": 30000,
        }
        self.galaxy = galaxy
