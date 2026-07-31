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
