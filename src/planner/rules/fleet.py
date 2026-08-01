"""Desired assembled-fleet planning."""

from src.planner.task import Task
from src.planner.assembly import empty_assembly_containers, tanker_shortage


def plan(operations, desired_state) -> list[Task]:
    probes = (getattr(operations.world, "fleet", None) or {}).get("probes", ())
    counts = {}
    for probe in probes:
        model = probe.get("model", "generic")
        counts[model] = counts.get(model, 0) + 1

    tasks = []
    for goal in desired_state.fleet:
        shortage = max(0, goal.quantity - counts.get(goal.model, 0))
        if shortage == 0:
            continue
        if goal.model != "deuterium_tanker":
            tasks.append(Task(
                action="Prepare Probe Assembly",
                reason=(
                    f"Desired {goal.model.replace('_', ' ')} fleet is "
                    f"{goal.quantity}; current fleet is {counts.get(goal.model, 0)}."
                ),
                category="fleet_assembly",
                target=goal.model,
                quantity=shortage,
                priority=goal.priority,
            ))
            continue

        missing = tanker_shortage(operations)
        if missing is not None:
            component, amount, required, current = missing
            active = operations.manufacturing.active_production_count(component)
            if amount == 0:
                tasks.append(Task(
                    action="Await Active Production",
                    reason=(
                        f"Priority {goal.priority} tanker goal reserves {active} active "
                        f"{component.replace('_', ' ')} craft; no duplicate order is needed."
                    ),
                    category="fleet_assembly",
                    target=component,
                    quantity=active,
                    constraints=("active_production_pending",),
                    priority=goal.priority,
                ))
                continue
            production = operations.manufacturing.production_plan(
                component, quantity=amount,
            )
            blockers = ("unknown_recipe",) if production is None else production["blockers"]
            tasks.append(Task(
                action="Craft Item" if production and production["achievable"] else "Prepare Manufacturing",
                reason=(
                    f"Priority {goal.priority} tanker goal requires {required} "
                    f"{component.replace('_', ' ')}; {current} available."
                ),
                category="fleet_assembly",
                target=component,
                quantity=amount,
                constraints=blockers,
                priority=goal.priority,
            ))
            continue

        containers = empty_assembly_containers(operations)
        tasks.append(Task(
            action="Assemble Probe" if len(containers) >= 2 else "Prepare Probe Assembly",
            reason=(
                f"Priority {goal.priority} tanker goal has all crafted components; "
                f"{len(containers)} of 2 empty attached containers are ready."
            ),
            category="fleet_assembly",
            target=goal.model,
            quantity=shortage,
            constraints=() if len(containers) >= 2 else ("two_empty_containers_required",),
            priority=goal.priority,
        ))
    return tasks
