"""Desired assembled-fleet planning."""

from src.planner.task import Task
from src.planner.assembly import empty_assembly_containers, tanker_component_statuses


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

        component_statuses = tanker_component_statuses(operations)
        unfinished = [
            status for status in component_statuses
            if status["completed"] < status["required"]
        ]
        if unfinished:
            for index, status in enumerate(component_statuses, start=1):
                component = status["component"]
                amount = status["missing"]
                if status["completed"] >= status["required"]:
                    continue
                progress = (
                    f"Tanker component {index}/{len(component_statuses)}: "
                    f"{component.replace('_', ' ')} — "
                    f"{status['required']} required, {status['completed']} stored, "
                    f"{status['active']} crafting, {amount} still unallocated."
                )
                if amount == 0:
                    surplus = max(0, status["active"] - status["credited_active"])
                    surplus_text = (
                        f" {surplus} additional active craft will be surplus to this tanker."
                        if surplus else ""
                    )
                    tasks.append(Task(
                        action="Await Active Production",
                        reason=(
                            f"{progress} Active production covers this requirement; "
                            f"no duplicate order is needed.{surplus_text}"
                        ),
                        category="fleet_assembly",
                        target=component,
                        quantity=status["credited_active"],
                        constraints=("active_production_pending",),
                        priority=goal.priority,
                    ))
                    continue
                production = operations.manufacturing.production_plan(
                    component, quantity=1,
                )
                blockers = ("unknown_recipe",) if production is None else production["blockers"]
                tasks.append(Task(
                    action="Craft Item" if production and production["achievable"] else "Prepare Manufacturing",
                    reason=(
                        f"{progress} Priority {goal.priority} tanker goal reserves "
                        f"this work ahead of lower-priority goals."
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
                f"{len(containers)} of 2 empty, unassigned attached containers are ready."
            ),
            category="fleet_assembly",
            target=goal.model,
            quantity=shortage,
            constraints=(
                ()
                if len(containers) >= 2
                else ("two_unassigned_empty_containers_required",)
            ),
            priority=goal.priority,
        ))
    return tasks
