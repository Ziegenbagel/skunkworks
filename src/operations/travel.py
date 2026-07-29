class TravelService:
    """
    Operational travel intelligence.
    """

    def __init__(
        self,
        world,
    ):
        self.world = world

    def has_external_tanks(self):

        return bool(
            self.world.probe["fuel"]["external_tanks"]
        )

    def fuel_percentage(self):

        tanks = self.world.probe["fuel"][
            "external_tanks"
        ]

        if not tanks:
            return 0

        return tanks[0]["fill_percent"]

    def travel_ready(self):

        return (
            self.has_external_tanks()
            and self.fuel_percentage() > 0
        )