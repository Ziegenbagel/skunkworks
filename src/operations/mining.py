"""Mining target and Manny availability intelligence."""


class MiningService:
    def __init__(self, world):
        self.world = world

    def targets(self, resource_type):
        candidates = []

        for target in self.world.sector.get(
            "resources",
            [],
        ):
            if target.get("requiresAutomationApproval") and not target.get("automationApproved"):
                continue
            amount = target.get(
                "resources",
                {},
            ).get(resource_type, 0)

            if amount <= 0:
                continue

            # Mining endpoints express deuterium asteroid contents in the
            # same fractional units used by mining-order payloads (4.42 means
            # 442 tank ECE). Planner shortages, probe fuel, and active mining
            # commitments use tank ECE, so normalize availability before it
            # is used to cap a planned order. Keep the world snapshot itself
            # untouched so API-facing displays can retain the reported value.
            available_amount = (
                float(amount) * 100.0
                if resource_type == "deuterium"
                else float(amount)
            )

            candidate = dict(target)
            candidate["resource_type"] = resource_type
            candidate["available_amount"] = available_amount
            candidate["score"] = self._score(
                target,
                resource_type,
                available_amount,
            )
            candidates.append(candidate)

        return sorted(
            candidates,
            key=lambda target: target["score"],
            reverse=True,
        )

    def best_target(self, resource_type):
        targets = self.targets(resource_type)
        return targets[0] if targets else None

    def idle_mannies(self):
        return [
            manny
            for manny in self.world.mannies.get(
                "mannies",
                [],
            )
            if manny.get("currentTask") is None
            and manny.get("canReceiveOrders", False)
        ]

    def can_mine(self, resource_type):
        return (
            bool(self.idle_mannies())
            and self.best_target(resource_type) is not None
            and self.world.probe["status"] == "idle"
        )

    def active_commitments(self):
        """Return undelivered resources already assigned to active Mannys."""

        commitments = {}
        for manny in self.world.mannies.get("mannies", []):
            current = manny.get("currentTask")
            details = current if isinstance(current, dict) else manny.get("task") or {}
            task_type = details.get("type") if isinstance(current, dict) else current
            if task_type != "mining" or not isinstance(details, dict):
                continue
            resource_type = details.get("resourceType")
            if not resource_type:
                resource_types = details.get("resourceTypes") or details.get("resources") or ()
                resource_type = resource_types[0] if resource_types else None
            if resource_type in {"organic_compound", "organic_compounds"}:
                resource_type = "carbon_compounds"
            if not resource_type:
                continue
            target = float(details.get("targetAmount", 0) or 0)
            deposited = float(details.get("depositedAmount", 0) or 0)
            if resource_type == "deuterium":
                target *= 100
                deposited *= 100
            commitments[resource_type] = commitments.get(resource_type, 0) + max(
                0, target - deposited,
            )
        return commitments

    def _score(self, target, resource_type, amount):
        composition = target.get(
            "composition",
            {},
        ).get(resource_type, 0)
        dynamic_bonus = (
            0.05
            if target.get("classification") == "dynamic"
            else 0
        )
        return amount * (1 + composition + dynamic_bonus)
