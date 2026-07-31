"""Desired assembled-fleet planning."""

from src.planner.task import Task


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
    return tasks
