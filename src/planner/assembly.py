"""Authoritative special probe-assembly requirements."""

from collections import Counter


GENERIC_COMPONENTS = (
    ("deuterium_engine", 1),
    ("scut_relay", 1),
    ("electric_motor", 5),
    ("atomic_printer_part", 2),
    ("solar_panel", 4),
)

TANKER_COMPONENTS = GENERIC_COMPONENTS + (
    ("linear_actuator", 2),
    ("integrated_circuit", 1),
    # Steel plates are also ingredients of several components above. Build the
    # tanker's final plate allotment only after those consumers are complete so
    # the same ten plates are not mistakenly credited and then consumed.
    ("steel_plate", 10),
)

# One registry drives both planning documentation and the operator-facing
# assembly catalog. Adding a future game model is intentionally one entry.
PROBE_ASSEMBLY_REQUIREMENTS = {
    "generic": GENERIC_COMPONENTS,
    "deuterium_tanker": TANKER_COMPONENTS,
}


def active_probe_assembly_count(operations, model):
    """Count probe assemblies accepted by the game but not yet completed.

    The API removes the committed components from inventory as soon as an
    assembly task starts.  Without crediting that in-flight probe, the next
    planning refresh sees both an unmet fleet goal and an empty component
    inventory and incorrectly starts building the entire kit again.
    """

    count = 0
    for manny in operations.world.mannies.get("mannies", ()):
        current = manny.get("currentTask")
        details = current if isinstance(current, dict) else manny.get("task")
        details = details if isinstance(details, dict) else {}
        task_type = current.get("type") if isinstance(current, dict) else current
        normalized = str(task_type or "").strip().lower().replace("-", "_")
        if normalized not in {"assemble_probe", "assembling_probe"}:
            continue
        payload = details.get("payload") if isinstance(details.get("payload"), dict) else {}
        active_model = (
            details.get("model")
            or details.get("probeModel")
            or details.get("targetModel")
            or payload.get("model")
        )
        # Current automated assembly only supports the tanker recipe. Some API
        # task snapshots expose the operation but omit its payload, so an
        # unlabelled in-flight assembly can safely satisfy that one known model.
        if active_model is None and model == "deuterium_tanker":
            count += 1
        elif str(active_model).strip().lower().replace("-", "_") == model:
            count += 1
    return count


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
