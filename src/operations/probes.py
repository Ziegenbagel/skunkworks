class ProbeService:
    """
    Operational information about the
    currently selected probe.
    """

    def __init__(
        self,
        world,
    ):
        self.world = world

    def current(self):

        current_name = (
            self.world.snapshot["probe"]
        )

        for probe in self.world.fleet["probes"]:

            if (
                probe["name"]
                == current_name
            ):
                return probe

        return None

    def inventory(self):

        return self.world.inventory

    def fuel(self):

        return self.world.fuel

    def is_idle(self):

        probe = self.current()

        if probe is None:
            return False

        return (
            probe["status"]
            == "idle"
        )