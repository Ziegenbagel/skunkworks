class ResourceAnalyzer:
    """
    Extract resource intelligence from a sector snapshot.
    """

    def get_sector_resources(self, snapshot):

        sector = snapshot["sector"]

        solar_system = None

        for obj in sector["objects"]:

            if obj["type"] == "solar_system":
                solar_system = obj
                break

        if solar_system is None:
            return []

        resources = []

        for asteroid in solar_system.get(
            "minableTargets",
            [],
        ):

            resources.append(
                {
                    "id": asteroid["id"],
                    "resources": asteroid.get(
                        "resourceAmounts",
                        {},
                    ),
                    "composition": asteroid.get(
                        "resourceComposition",
                        {},
                    ),
                }
            )

        return resources