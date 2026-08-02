"""Authoritative special probe-assembly requirements."""

from collections import Counter


TANKER_COMPONENTS = (
    ("deuterium_engine", 1),
    ("scut_relay", 1),
    ("electric_motor", 5),
    ("atomic_printer_part", 2),
    ("solar_panel", 4),
    ("linear_actuator", 2),
    ("integrated_circuit", 1),
    # Steel plates are also ingredients of several components above. Build the
    # tanker's final plate allotment only after those consumers are complete so
    # the same ten plates are not mistakenly credited and then consumed.
    ("steel_plate", 10),
)


def tanker_component_statuses(operations):
    """Return every tanker component's stored, active, and outstanding state."""

    inventory = operations.world.probe.get("inventory", {})
    counts = Counter()
    for item in inventory.get("items", ()):
        value = item.get("quantity", item.get("count", 1))
        try:
            quantity = max(0, int(value))
        except (TypeError, ValueError):
            quantity = 1
        counts[item.get("type")] += quantity
    statuses = []
    for component, required in TANKER_COMPONENTS:
        completed = counts.get(component, 0)
        active = operations.manufacturing.active_production_count(component)
        credited_active = min(active, max(0, required - completed))
        statuses.append({
            "component": component,
            "required": required,
            "completed": completed,
            "active": active,
            "credited_active": credited_active,
            "allocated_stored": min(completed, required),
            "allocated_active": credited_active,
            "surplus_stored": max(0, completed - required),
            "surplus_active": max(0, active - credited_active),
            "missing": max(0, required - completed - credited_active),
        })
    return tuple(statuses)


def tanker_shortage(operations):
    """Return the first unfinished component for compatibility callers."""

    for status in tanker_component_statuses(operations):
        if status["completed"] < status["required"]:
            return (
                status["component"],
                status["missing"],
                status["required"],
                status["completed"],
            )
    return None


def empty_assembly_containers(operations):
    """Select empty, attached, policy-unassigned assembly containers."""

    result = []
    inventory = operations.world.probe.get("inventory", {})
    for container in inventory.get("containers", ()):
        if container.get("kind") != "container":
            continue
        used = float(container.get("usedCapacity", container.get("used", 0)) or 0)
        capacity = float(container.get("capacity", 0) or 0)
        free = float(container.get("freeCapacity", capacity - used) or 0)
        rules = container.get("rules") or {}
        assigned = any(
            rules.get(key)
            for key in ("priority", "exclusion", "strictExclusion")
        ) or bool(
            container.get("assignedResource")
            or container.get("resourceType")
        )
        if (
            not assigned
            and used <= 0.00001
            and (capacity <= 0 or free + 0.00001 >= capacity)
        ):
            identifier = container.get("id") or container.get("containerId")
            if identifier is not None:
                result.append(identifier)
    return result
