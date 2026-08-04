"""Resource-reserve and manufacturing-shortage mining planning."""

from collections import defaultdict

from src.planner.priorities import HIGH, NORMAL
from src.planner.task import Task
from src.planner.assembly import tanker_component_statuses
from src.planner.reservations import (
    first_reserved_dependency,
    higher_priority_item_reservations,
)


def plan(operations, desired_state) -> list[Task]:
    shortages = operations.inventory.reserve_shortages(
        desired_state.resources
    )
    manufacturing_resources = set()
    resource_reasons = defaultdict(set)
    priorities = {
        goal.resource_type: goal.priority
        for goal in desired_state.resources
    }
    for goal in desired_state.resources:
        resource_reasons[goal.resource_type].add(
            f"the {goal.minimum_amount:g} {goal.resource_type.replace('_', ' ')} reserve target"
        )

    for goal in desired_state.production:
        current = operations.manufacturing.inventory_count(
            goal.recipe_id
        )
        shortage = max(0, goal.quantity - current)

        if shortage <= 0:
            continue

        # A desired quantity is a persistent destination, not permission to
        # reserve the inputs for the entire outstanding batch. Manufacturing
        # dispatches one unit at a time, so mining should fund the same bounded
        # scheduling horizon and let the next cycle compare every goal again.
        reservations = higher_priority_item_reservations(
            operations, desired_state, goal.priority,
        )
        dependency = first_reserved_dependency(
            operations, goal.recipe_id, reservations,
        )
        planned_recipe = dependency or goal.recipe_id
        production = operations.manufacturing.production_plan(
            planned_recipe,
            quantity=1,
            include_operational_constraints=False,
        )

        if production is None:
            continue

        for resource_type, amount in production[
            "missing_resources"
        ].items():
            shortages[resource_type] = max(
                shortages.get(resource_type, 0),
                amount,
            )
            manufacturing_resources.add(resource_type)
            resource_reasons[resource_type].add(
                f"next production unit: {goal.recipe_id.replace('_', ' ')}"
                + (
                    f" via surplus {dependency.replace('_', ' ')}"
                    if dependency else ""
                )
            )
            priorities[resource_type] = min(
                priorities.get(resource_type, goal.priority),
                goal.priority,
            )

    for goal in desired_state.fleet:
        if goal.model != "deuterium_tanker":
            continue
        current_fleet = sum(
            probe.get("model", "generic") == goal.model
            for probe in (getattr(operations.world, "fleet", None) or {}).get("probes", ())
        )
        if current_fleet >= goal.quantity:
            continue
        requests = {
            status["component"]: status["missing"]
            for status in tanker_component_statuses(operations)
            if status["missing"] > 0
        }
        production = operations.manufacturing.production_bundle_plan(requests)
        if production is None:
            continue
        for component, quantity in requests.items():
            component_plan = operations.manufacturing.production_plan(
                component,
                quantity=quantity,
                include_operational_constraints=False,
            )
            if component_plan is None:
                continue
            for resource_type, amount in component_plan["missing_resources"].items():
                if amount > 0:
                    resource_reasons[resource_type].add(
                        f"tanker component: {component.replace('_', ' ')}"
                    )
        for resource_type, resource_amount in production["missing_resources"].items():
            shortages[resource_type] = max(shortages.get(resource_type, 0), resource_amount)
            manufacturing_resources.add(resource_type)
            priorities[resource_type] = min(priorities.get(resource_type, goal.priority), goal.priority)

    tasks = []
    active_commitments = operations.mining.active_commitments()

    for resource_type, amount in shortages.items():
        committed = float(active_commitments.get(resource_type, 0))
        uncovered_amount = max(0, float(amount) - committed)
        if uncovered_amount <= 0.00001:
            continue
        target = operations.mining.best_target(resource_type)
        constraints = []

        if target is None:
            constraints.append("resource_not_in_current_sector")

        if not operations.mining.idle_mannies():
            constraints.append("no_idle_manny")

        if operations.world.probe["status"] != "idle":
            constraints.append("probe_unavailable")

        free_capacity = operations.inventory.free_capacity()
        if resource_type != "deuterium" and free_capacity <= 0:
            constraints.append("insufficient_probe_storage")

        order_amount = uncovered_amount
        if target is not None:
            order_amount = min(order_amount, target.get("available_amount", order_amount))
        if resource_type != "deuterium":
            order_amount = min(order_amount, free_capacity)

        reasons = sorted(resource_reasons.get(resource_type, ()))
        purpose = (
            "; ".join(reasons)
            if reasons
            else "the highest-priority unmet goal"
        )
        background_work = resource_type not in manufacturing_resources
        tasks.append(
            Task(
                action=(
                    "Mine Resource"
                    if not constraints
                    else "Locate Mining Opportunity"
                ),
                reason=(
                    f"Need {amount:.3f} additional {resource_type.replace('_', ' ')}; "
                    f"{committed:.3f} is already committed to active mining and "
                    f"{uncovered_amount:.3f} remains uncovered. "
                    f"This mining order unlocks {purpose}."
                    + (
                        " Reserve-floor mining runs as background work so "
                        "fabrication capacity remains available."
                        if background_work else ""
                    )
                ),
                category="mining",
                target=(
                    target["id"]
                    if target is not None
                    else resource_type
                ),
                quantity=round(order_amount, 3),
                maximum_order_amount=desired_state.maximum_mining_order_amount,
                background_work=background_work,
                constraints=tuple(constraints),
                resource_type=resource_type,
                priority=priorities.get(
                    resource_type,
                    HIGH if resource_type in manufacturing_resources else NORMAL,
                ),
            )
        )

    # Equal-priority resource orders are balanced by current active coverage.
    # This prevents the first resource in saved settings from claiming every
    # newly-idle Manny while other requirements remain completely uncovered.
    tasks.sort(key=lambda task: (
        task.priority,
        active_commitments.get(task.resource_type, 0)
        / max(float(shortages.get(task.resource_type, 0)), 0.00001),
        -float(shortages.get(task.resource_type, 0)),
    ))
    return tasks
