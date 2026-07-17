class ResourceAnalyzer:
    """
    Extract resource intelligence from a sector snapshot.
    """

    def get_sector_resources(self, snapshot):
        """Return every mineable object in the current sector."""

        mineables = self._discover_mineables(snapshot)

        resources = []

        for obj in mineables:

            resource_amounts = obj.get(
                "resourceAmounts",
                {}
            )

            # Ignore exhausted wandering asteroids.
            if (
                sum(resource_amounts.values()) == 0
                and obj.get("mannyMineable", False)
            ):
                continue

            resources.append(
                {
                    "id": obj["id"],

                    "classification": (
                        "dynamic"
                        if obj.get("mannyMineable", False)
                        else "persistent"
                    ),

                    "resource_types": (
                        obj.get("resources")
                        or obj.get("resourceTypes")
                        or []
                    ),

                    "resources": resource_amounts,

                    "composition": obj.get(
                        "resourceComposition",
                        {},
                    ),
                }
            )

        return resources

    def _discover_mineables(self, snapshot):
        """
        Collect every mineable object from the sector.

        This includes:

        - Persistent mineables
          (solar_system.minableTargets)

        - Dynamic mineables
          (objects with mannyMineable=True)
        """

        sector = snapshot["sector"]

        mineables = []

        for obj in sector["objects"]:

            # Persistent mineable targets.
            mineables.extend(
                obj.get("minableTargets", [])
            )

            # Dynamic mineable objects.
            if obj.get("mannyMineable", False):
                mineables.append(obj)

        return mineables