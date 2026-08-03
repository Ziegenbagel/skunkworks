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
            amount = target.get(
                "resources",
                {},
            ).get(resource_type, 0)

            if amount <= 0:
                continue

            candidate = dict(target)
            candidate["resource_type"] = resource_type
            candidate["available_amount"] = amount
            candidate["score"] = self._score(
                target,
                resource_type,
                amount,
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
                resource_types = details.get("resourceTypes") or ()
                resource_type = resource_types[0] if resource_types else None
            if resource_type in {"organic_compound", "organic_compounds"}:
                resource_type = "carbon_compounds"
            if not resource_type:
                continue
            target = float(details.get("targetAmount", 0) or 0)
            deposited = float(details.get("depositedAmount", 0) or 0)
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
