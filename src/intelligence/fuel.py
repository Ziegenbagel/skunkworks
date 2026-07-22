class FuelAnalyzer:
    """
    Extract fuel intelligence from a sector snapshot.
    """

    def get_fuel(self, snapshot):

        inventory = snapshot["inventory"]

        tanks = []

        for tank in inventory.get(
            "externalTanks",
            [],
        ):

            tanks.append(
                {
                    "id": tank["id"],
                    "type": tank["type"],
                    "name": tank["name"],
                    "fill_percent": tank[
                        "fillPercent"
                    ],
                    "external": tank[
                        "external"
                    ],
                    "uses_cargo_capacity": tank[
                        "usesCargoCapacity"
                    ],
                }
            )

        return {
            "external_tanks": tanks,
        }