"""Operational inventory of attached and persistent detached containers."""


class ContainerService:
    DETACHED_TYPES = frozenset(
        {
            "detached_container",
            "storage_container",
            "hidden_container",
            "drifting_container",
            "dropped_on_planet_container",
        }
    )

    def __init__(self, world):
        self.world = world

    def attached(self):
        return tuple(
            container
            for container in self.world.probe.get(
                "inventory",
                {},
            ).get("containers", ())
            if container.get("kind") == "container"
        )

    def detached(self):
        snapshot = self.world.sector.get("snapshot") or {}
        objects = (snapshot.get("sector") or {}).get("objects", ())
        return tuple(
            object_ for object_ in objects
            if self._is_detached(object_)
        )

    def all(self):
        return self.attached() + self.detached()

    def free_capacity(self, container):
        if "freeCapacity" in container:
            return container["freeCapacity"]
        capacity = container.get("capacity", 0)
        used = container.get("usedCapacity", container.get("used", 0))
        return max(0.0, capacity - used)

    @classmethod
    def _is_detached(cls, object_):
        type_ = str(
            object_.get("type")
            or object_.get("kind")
            or object_.get("objectType")
            or ""
        ).lower()
        return (
            type_ in cls.DETACHED_TYPES
            or "container" in type_
            and object_.get("detached", True)
        )
