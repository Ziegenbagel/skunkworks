"""Desired-State manufacturing planning."""

from src.planner.priorities import NORMAL
from src.planner.task import Task
from src.planner.reservations import (
    first_reserved_dependency,
    higher_priority_item_reservations,
)


def plan(operations, desired_state) -> list[Task]:
    tasks = []

    for goal in desired_state.production:
        stored = operations.manufacturing.inventory_count(
            goal.recipe_id, include_active=False,
        )
        active = operations.manufacturing.active_production_count(
            goal.recipe_id
        )
        shortage = max(0, goal.quantity - stored - active)

        if shortage == 0:
            continue

        reservations = higher_priority_item_reservations(
            operations, desired_state, goal.priority,
        )
        dependency = first_reserved_dependency(
            operations, goal.recipe_id, reservations,
        )
        if dependency is not None:
            dependency_plan = operations.manufacturing.production_plan(
                dependency, quantity=1,
            )
            if dependency_plan is not None:
                tasks.append(Task(
                    action=(
                        "Craft Item"
                        if dependency_plan["achievable"]
                        else "Prepare Manufacturing"
                    ),
                    reason=(
                        f"Build one surplus {dependency.replace('_', ' ')} for the next "
                        f"{goal.recipe_id.replace('_', ' ')}. Existing {dependency.replace('_', ' ')} "
                        "inventory is committed to a higher-priority goal and will not be consumed."
                    ),
                    category="manufacturing",
                    target=dependency,
                    quantity=1,
                    constraints=dependency_plan["blockers"],
                    priority=goal.priority,
                ))
                continue

        production = operations.manufacturing.production_plan(
            goal.recipe_id,
            quantity=1,
        )

        if production is None:
            tasks.append(
                Task(
                    action="Review Production Goal",
                    reason="The requested recipe is unavailable.",
                    category="manufacturing",
                    target=goal.recipe_id,
                    quantity=shortage,
                    constraints=("unknown_recipe",),
                    priority=goal.priority,
                )
            )
            continue

        tasks.append(
            Task(
                action=(
                    "Craft Item"
                    if production["achievable"]
                    else "Prepare Manufacturing"
                ),
                reason=(
                    f"Desired quantity is {goal.quantity}; {stored} stored, "
                    f"{active} crafting, and {shortage} still unallocated. "
                    "Dispatch readiness is evaluated one craft at a time: "
                    "only the next unit's inputs are reserved, and all goals "
                    "are reconsidered after each planning cycle."
                ),
                category="manufacturing",
                target=goal.recipe_id,
                quantity=shortage,
                constraints=production["blockers"],
                priority=goal.priority,
            )
        )

    return tasks
