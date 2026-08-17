"""Inventory stock and capacity intelligence."""


class InventoryService:
    # A Manny occupies this much probe storage when aboard.  Keep one berth
    # free so an outbound miner can always return, even if its cargo is empty.
    MANNY_BERTH_CAPACITY = 0.05
    def __init__(self, world):
        self.world = world

    def resource_amounts(self):
        amounts = {
            stock["type"]: stock["amount"]
            for stock in self.world.probe[
                "inventory"
            ].get("resourceStocks", [])
        }
        amounts["deuterium"] = self.world.probe[
            "fuel"
        ].get("deuterium", 0)
        return amounts

    def resource_amount(self, resource_type):
        return self.resource_amounts().get(
            resource_type,
            0,
        )

    def free_capacity(self):
        return self.world.probe["inventory"].get(
            "freeCapacity",
            0,
        )

    def mining_return_capacity(self, active_commitments=None):
        """Capacity safe to promise to another non-fuel mining order."""

        commitments = active_commitments or {}
        inbound_cargo = sum(
            max(0.0, float(amount or 0))
            for resource, amount in commitments.items()
            if resource != "deuterium"
        )
        return max(
            0.0,
            float(self.free_capacity() or 0)
            - inbound_cargo
            - self.MANNY_BERTH_CAPACITY,
        )

    def reserve_shortages(self, goals):
        return {
            goal.resource_type: round(
                goal.minimum_amount
                - self.resource_amount(goal.resource_type),
                3,
            )
            for goal in goals
            if self.resource_amount(goal.resource_type)
            < goal.minimum_amount
        }
