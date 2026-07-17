class InventoryAnalyzer:
    """
    Extract inventory intelligence from a sector snapshot.
    """

    def get_inventory(self, snapshot):

        inventory = snapshot["inventory"]

        return {
            "capacity": inventory["capacity"],
            "used_capacity": inventory["usedCapacity"],
            "free_capacity": inventory["freeCapacity"],
            "resource_stocks": self._resource_stocks(
                inventory
            ),
        }

    def _resource_stocks(self, inventory):

        stocks = {}

        for resource in inventory.get(
            "resourceStocks",
            [],
        ):

            stocks[
                resource["type"]
            ] = resource["amount"]

        return stocks