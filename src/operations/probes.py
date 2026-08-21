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
        """
        Return the currently focused probe.
        """

        return self.world.probe

    def inventory(self):
        """
        Return the current probe's inventory.
        """

        return self.current()["inventory"]

    def fuel(self):
        """
        Return the current probe's fuel system.
        """

        return self.current()["fuel"]

    def is_idle(self):
        """
        Return True if the current probe is idle.
        """

        # The game reports a stationary probe as either ``idle`` or
        # ``arrived`` depending on which endpoint produced the snapshot.
        # Both states can safely accept onboard Manny and movement orders.
        return self.status() in {"idle", "arrived"}

    def status(self):
        """
        Return the current probe's status.
        """

        return self.current()["status"]


    def is_traveling(self):
        """
        Return True if the probe is traveling between sectors.
        """

        return self.status() in {
            "preparing",
            "accelerating",
            "cruising",
            "decelerating",
        }


    def sensor_mode(self):
        """
        Return the current probe's sensor mode.
        """

        return self.current()["sensor_mode"]

    def movement(self):
        """
        Return the probe's movement information.
        """

        return self.current()["movement"]


    def navigation(self):
        """
        Return the probe's navigation information.
        """

        return self.current()["navigation"]


    def systems(self):
        """
        Return the probe's systems information.
        """

        return self.current()["systems"]

    def inventory_used_percent(self):
        """
        Return cargo utilization as a percentage.
        """

        inventory = self.inventory()

        capacity = inventory.get("capacity", 0)

        if capacity == 0:
            return 0

        return (
            inventory.get("usedCapacity", 0) / capacity
        ) * 100

    def fuel_percent(self):
        """
        Return internal fuel percentage.
        """

        fuel = self.fuel()

        maximum = fuel["maxDeuterium"]

        if maximum == 0:
            return 0

        return (
            fuel["deuterium"] / maximum
        ) * 100
