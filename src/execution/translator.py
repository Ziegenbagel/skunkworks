"""Translate actionable planner tasks into typed commands."""

from .commands import Command, CommandType


class TaskCommandTranslator:
    def __init__(self, operations, probe_id):
        self.operations = operations
        self.probe_id = probe_id
        self._claimed_manny_ids = set()

    def translate(self, task):
        if task.constraints:
            return None

        handler = {
            "Craft Item": self._craft,
            "Mine Resource": self._mine,
            "Mine Deuterium": self._mine,
            "Move Probe": self._move,
        }.get(task.action)

        return handler(task) if handler is not None else None

    def _craft(self, task):
        recipe = self.operations.manufacturing.recipes.get(
            task.target
        )

        if recipe is None:
            return None

        craftable_by = recipe.get("craftableBy", [])

        if "manny" in craftable_by:
            manny = self._claim_idle_manny()
            if manny is None:
                return None
            command_type = CommandType.MANNY_CRAFT
            target_id = manny["id"]
        elif "atomic_3d_printer" in craftable_by:
            command_type = CommandType.ATOMIC_PRINTER_CRAFT
            target_id = None
        else:
            return None

        return Command(
            type=command_type,
            probe_id=self.probe_id,
            target_id=target_id,
            payload={"recipe": task.target},
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={"remainingOrders": int(task.quantity)},
        )

    def _mine(self, task):
        manny = self._claim_idle_manny()
        resource_type = task.resource_type

        if manny is None or resource_type is None:
            return None

        cargo = manny.get("cargo") or {}
        trip_capacity = float(cargo.get("capacity", 0.05) or 0.05)
        target_amount = round(min(float(task.quantity), trip_capacity), 3)

        return Command(
            type=CommandType.MANNY_MINE,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload={
                "objectId": task.target,
                "resources": [resource_type],
                "targetAmount": target_amount,
            },
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={"remainingAmount": max(0, round(float(task.quantity) - target_amount, 3))},
        )

    def _move(self, task):
        route = task.route or self.operations.travel.route_to(
            task.destination
        )

        if not route:
            return None

        next_sector = route[0]
        return Command(
            type=CommandType.MOVE_PROBE,
            probe_id=self.probe_id,
            payload={
                "target": {
                    "x": next_sector.x,
                    "y": next_sector.y,
                    "z": next_sector.z,
                }
            },
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                "finalDestination": {
                    "x": task.destination.x,
                    "y": task.destination.y,
                    "z": task.destination.z,
                },
                "remainingHops": len(route),
                "hazards": [
                    {
                        "code": hazard.code,
                        "severity": hazard.severity,
                        "message": hazard.message,
                        "acknowledgementRecommended": (
                            hazard.acknowledgement_recommended
                        ),
                    }
                    for hazard in task.hazards
                ],
            },
        )

    def _claim_idle_manny(self):
        mannies = self.operations.mining.idle_mannies()
        manny = next(
            (item for item in mannies if item["id"] not in self._claimed_manny_ids),
            None,
        )
        if manny is not None:
            self._claimed_manny_ids.add(manny["id"])
        return manny
