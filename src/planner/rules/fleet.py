"""Desired assembled-fleet planning."""

from src.planner.task import Task
from src.planner.assembly import (
    active_probe_assembly_count,
    empty_assembly_containers,
    probe_component_statuses,
    recorded_probe_assembly_count,
)


def _component_summary(component_statuses):
    return "; ".join(
        (
            f"{status['component'].replace('_', ' ')}: "
            f"{status['allocated_stored']} stored"
            + (
                f", {status['allocated_active']} active"
                if status["allocated_active"] else ""
            )
            + f" / {status['required']} required"
            + (
                f", {status['missing']} still required"
                if status["missing"] else ", covered"
            )
        )
        for status in component_statuses
    )


def plan(operations, desired_state) -> list[Task]:
    tasks = []
    for goal in desired_state.fleet:
        completed = recorded_probe_assembly_count(operations, goal.model)
        active = active_probe_assembly_count(operations, goal.model)
        credited = max(completed, active)
        shortage = max(0, goal.quantity - credited)
        if shortage == 0:
            if active and completed < goal.quantity:
                tasks.append(Task(
                    action="Await Active Assembly",
                    reason=(
                        f"Desired {goal.model.replace('_', ' ')} fleet is "
                        f"{goal.quantity}; {completed} recorded and {active} assembly "
                        "in progress. Its committed components have already been "
                        "consumed by the game and must not be rebuilt."
                    ),
                    category="fleet_assembly",
                    target=goal.model,
                    quantity=active,
                    constraints=("active_assembly_pending",),
                    priority=goal.priority,
                ))
            continue
        component_statuses = probe_component_statuses(operations, goal.model)
        reserved_items = tuple(
            (status["component"], status["allocated_stored"])
            for status in component_statuses
            if status["allocated_stored"] > 0
        )
        unfinished = [
            status for status in component_statuses
            if status["completed"] < status["required"]
        ]
        if unfinished:
            # Keep the configured fleet target visible while its actionable
            # children describe individual component work. Without this
            # parent status, the complete planner list looks as though the
            # tanker goal disappeared precisely while it is driving claims.
            tasks.append(Task(
                action="Prepare Probe Assembly",
                reason=(
                    f"Desired {goal.model.replace('_', ' ')} fleet is {goal.quantity}; "
                    f"this probe has recorded {completed} successful assembly "
                    f"order(s), {active} assembly order(s) are active, and "
                    f"{shortage} still remain. Next assembly kit — "
                    f"{_component_summary(component_statuses)}."
                ),
                category="fleet_assembly",
                target=goal.model,
                quantity=shortage,
                constraints=("assembly_components_incomplete",),
                reserved_items=reserved_items,
                priority=goal.priority,
            ))
            for index, status in enumerate(component_statuses, start=1):
                component = status["component"]
                amount = status["missing"]
                if status["completed"] >= status["required"]:
                    continue
                progress = (
                    f"{'Tanker' if goal.model == 'deuterium_tanker' else 'Assembly'} "
                    f"component {index}/{len(component_statuses)}: "
                    f"{component.replace('_', ' ')} — "
                    f"{status['required']} required; "
                    f"{status['allocated_stored']} stored and allocated, "
                    f"{status['allocated_active']} active craft allocated, "
                    f"{amount} still required."
                )
                if amount == 0:
                    surplus = status["surplus_active"]
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
                        reserved_items=reserved_items,
                        priority=goal.priority,
                    ))
                    continue
                production = operations.manufacturing.production_plan(
                    component, quantity=1, use_inventory_items=False,
                )
                blockers = ("unknown_recipe",) if production is None else production["blockers"]
                tasks.append(Task(
                    action="Craft Item" if production and production["achievable"] else "Prepare Manufacturing",
                    reason=(
                        f"{progress} Priority {goal.priority} "
                        f"{'tanker' if goal.model == 'deuterium_tanker' else 'assembly'} "
                        "goal reserves "
                        f"this work ahead of lower-priority goals."
                    ),
                    category="fleet_assembly",
                    target=component,
                    quantity=amount,
                    constraints=blockers,
                    reserved_items=reserved_items,
                    priority=goal.priority,
                ))
            continue

        containers = (
            empty_assembly_containers(operations)
            if goal.model == "deuterium_tanker" else ()
        )
        ready_to_assemble = (
            len(containers) >= 2
            if goal.model == "deuterium_tanker" else True
        )
        tasks.append(Task(
            action="Assemble Probe" if ready_to_assemble else "Prepare Probe Assembly",
            reason=(
                f"Priority {goal.priority} {goal.model.replace('_', ' ')} goal has "
                "all crafted components."
                + (
                    f" {len(containers)} of 2 empty, unassigned attached containers are ready."
                    if goal.model == "deuterium_tanker" else ""
                )
            ),
            category="fleet_assembly",
            target=goal.model,
            quantity=shortage,
            constraints=(
                ()
                if ready_to_assemble
                else ("two_unassigned_empty_containers_required",)
            ),
            reserved_items=reserved_items,
            priority=goal.priority,
        ))
    return tasks
