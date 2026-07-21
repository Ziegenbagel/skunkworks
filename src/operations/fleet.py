class FleetService:
    """
    Provides operational fleet queries.
    """

    def __init__(
        self,
        world,
    ):

        self.world = world

    def total_probes(
        self,
    ):
        """
        Return the total number of probes.
        """

        return self.world.fleet[
            "total"
        ]
    
    def available_probes(
        self,
    ):
        """
        Return all available probes.
        """

        return [
            probe
            for probe in self.world.fleet[
                "probes"
            ]
            if probe["status"] == "idle"
        ]
    
    def busy_probes(
        self,
    ):
        """
        Return all busy probes.
        """

        return [
            probe
            for probe in self.world.fleet[
                "probes"
            ]
            if probe["status"] != "idle"
        ]
    
    def idle_count(
        self,
    ):
        """
        Return the number of idle probes.
        """

        return self.world.fleet[
            "idle"
        ]
    
    def active_count(
        self,
    ):
        """
        Return the number of active probes.
        """

        return self.world.fleet[
            "active"
        ]
    
    def default_probe_id(
        self,
    ):
        """
        Return the player's default probe ID.
        """

        return self.world.fleet[
            "default_probe"
        ]
    
    def status_counts(
        self,
    ):
        """
        Return probe counts by status.
        """

        return self.world.fleet[
            "status_counts"
        ]
    
    def default_probe(
        self,
    ):
        """
        Return the player's default probe.
        """

        for probe in self.world.fleet[
            "probes"
        ]:

            if probe["isDefault"]:

                return probe

        return None
    
    def probe_by_id(
        self,
        probe_id,
    ):
        """
        Return one probe by ID.
        """

        for probe in self.world.fleet[
            "probes"
        ]:

            if probe["id"] == probe_id:

                return probe

        return None
    
    def probe_names(
        self,
    ):
        """
        Return all probe names.
        """

        return [
            probe["name"]
            for probe in self.world.fleet[
                "probes"
            ]
        ]