"""Derived mining-depot intelligence over real game entities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MiningDepot:
    asteroid_id: str
    name: str
    resource_types: tuple[str, ...]
    remaining: float
    containers: tuple[dict, ...]
    miners: tuple[dict, ...]
    transporters: tuple[dict, ...]
    storage_free: float
    storage_capacity: float
    storage_used: float
    storage_fill_percent: float
    needs_transport: bool
    status: str


class DepotService:
    def __init__(self, world, mannies, containers):
        self.world = world
        self.mannies = mannies
        self.containers = containers

    def all(self):
        depots = []
        detached = self.containers.detached()
        for asteroid in self.world.sector.get("resources", ()):
            asteroid_id = asteroid["id"]
            containers = tuple(
                item for item in detached
                if self._parent_id(item) == asteroid_id
            )
            miners = tuple(
                manny for manny in self.mannies.mining()
                if self._task_target(manny) == asteroid_id
            )
            transporters = tuple(
                manny for manny in self.mannies.by_task("transporting")
                if self._task_target(manny) == asteroid_id
            )
            if not (containers or miners or transporters):
                continue
            remaining = sum(asteroid.get("resources", {}).values())
            free = sum(
                self.containers.free_capacity(item)
                for item in containers
            )
            capacity = sum(item.get("capacity", 0) for item in containers)
            used = max(0.0, capacity - free)
            status = self._status(remaining, free, miners)
            depots.append(
                MiningDepot(
                    asteroid_id=asteroid_id,
                    name=asteroid.get("name", asteroid_id),
                    resource_types=tuple(
                        key for key, value
                        in asteroid.get("resources", {}).items()
                        if value > 0
                    ),
                    remaining=remaining,
                    containers=containers,
                    miners=miners,
                    transporters=transporters,
                    storage_free=free,
                    storage_capacity=capacity,
                    storage_used=used,
                    storage_fill_percent=(
                        used / capacity * 100 if capacity else 0
                    ),
                    needs_transport=(capacity > 0 and free / capacity <= 0.2),
                    status=status,
                )
            )
        return tuple(depots)

    @staticmethod
    def _parent_id(value):
        return (
            value.get("asteroidId")
            or value.get("parentObjectId")
            or value.get("attachedToObjectId")
            or (value.get("location") or {}).get("objectId")
        )

    @staticmethod
    def _task_target(manny):
        task = manny.get("currentTask") or {}
        if not isinstance(task, dict):
            return None
        payload = task.get("payload") or {}
        return (
            task.get("objectId")
            or task.get("targetObjectId")
            or payload.get("objectId")
        )

    @staticmethod
    def _status(remaining, storage_free, miners):
        if remaining <= 0:
            return "depleted"
        if storage_free <= 0:
            return "storage_full"
        if not miners:
            return "unstaffed"
        return "operational"
