"""Authoritative special probe-assembly requirements."""

from collections import Counter


TANKER_COMPONENTS = (
    ("deuterium_engine", 1),
    ("scut_relay", 1),
    ("electric_motor", 5),
    ("atomic_printer_part", 2),
    ("solar_panel", 4),
    ("steel_plate", 10),
    ("linear_actuator", 2),
    ("integrated_circuit", 1),
)


def tanker_shortage(operations):
    """Return the first missing component, preserving build order."""

    inventory = operations.world.probe.get("inventory", {})
    counts = Counter(item.get("type") for item in inventory.get("items", ()))
    for component, required in TANKER_COMPONENTS:
        missing = max(0, required - counts.get(component, 0))
        if missing:
            return component, missing, required, counts.get(component, 0)
    return None


def empty_assembly_containers(operations):
    """Select empty attached additional containers accepted by the API."""

    result = []
    inventory = operations.world.probe.get("inventory", {})
    for container in inventory.get("containers", ()):
        if container.get("kind") != "container":
            continue
        used = float(container.get("usedCapacity", container.get("used", 0)) or 0)
        capacity = float(container.get("capacity", 0) or 0)
        free = float(container.get("freeCapacity", capacity - used) or 0)
        if used <= 0.00001 and (capacity <= 0 or free + 0.00001 >= capacity):
            identifier = container.get("id") or container.get("containerId")
            if identifier is not None:
                result.append(identifier)
    return result
