"""Inventory stock and capacity intelligence."""


class InventoryService:
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
