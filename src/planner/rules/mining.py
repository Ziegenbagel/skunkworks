"""Resource-reserve and manufacturing-shortage mining planning."""

from src.planner.priorities import HIGH, NORMAL
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    shortages = operations.inventory.reserve_shortages(
        desired_state.resources
    )
    manufacturing_resources = set()
    priorities = {
        goal.resource_type: goal.priority
        for goal in desired_state.resources
    }

    for goal in desired_state.production:
        current = operations.manufacturing.inventory_count(
            goal.recipe_id
        )
        shortage = max(0, goal.quantity - current)

        if shortage <= 0:
            continue

        production = operations.manufacturing.production_plan(
            goal.recipe_id,
            quantity=shortage,
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
            priorities[resource_type] = min(
                priorities.get(resource_type, goal.priority),
                goal.priority,
            )

    tasks = []

    for resource_type, amount in shortages.items():
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

        order_amount = amount
        if target is not None:
            order_amount = min(order_amount, target.get("available_amount", order_amount))
        if resource_type != "deuterium":
            order_amount = min(order_amount, free_capacity)

        tasks.append(
            Task(
                action=(
                    "Mine Resource"
                    if not constraints
                    else "Locate Mining Opportunity"
                ),
                reason=(
                    f"Need {amount:.3f} additional "
                    f"{resource_type.replace('_', ' ')}."
                ),
                category="mining",
                target=(
                    target["id"]
                    if target is not None
                    else resource_type
                ),
                quantity=round(order_amount, 3),
                constraints=tuple(constraints),
                resource_type=resource_type,
                priority=priorities.get(
                    resource_type,
                    HIGH if resource_type in manufacturing_resources else NORMAL,
                ),
            )
        )

    return tasks
