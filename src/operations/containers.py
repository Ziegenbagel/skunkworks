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
        detached = []
        for object_ in objects:
            if self._is_detached(object_):
                detached.append(self._normalized_detached(object_))
            for container in object_.get("storageContainers", ()) or ():
                nested = dict(container)
                nested.setdefault("targetObjectId", object_.get("id"))
                nested.setdefault("targetObjectName", object_.get("name"))
                nested.setdefault("mode", "hidden_on_asteroid")
                detached.append(self._normalized_detached(nested))
        return tuple(detached)

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

    @staticmethod
    def _normalized_detached(object_):
        """Retain the sector-object ID while exposing its attached-item ID."""
        normalized = dict(object_)
        identifier = str(normalized.get("id", ""))
        source_id = (
            normalized.get("containerId")
            or normalized.get("sourceContainerId")
        )
        if not source_id and identifier.startswith("detached-container-"):
            source_id = identifier[len("detached-container-"):]
        if not source_id:
            source_id = identifier
        if source_id:
            normalized["containerId"] = str(source_id)
        return normalized
