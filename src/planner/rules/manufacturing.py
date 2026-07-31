"""Desired-State manufacturing planning."""

from src.planner.priorities import NORMAL
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    tasks = []

    for goal in desired_state.production:
        current = operations.manufacturing.inventory_count(
            goal.recipe_id
        )
        shortage = max(0, goal.quantity - current)

        if shortage == 0:
            continue

        production = operations.manufacturing.production_plan(
            goal.recipe_id,
            quantity=shortage,
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
                    priority=NORMAL,
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
                    f"Desired quantity is {goal.quantity}; "
                    f"current quantity is {current}."
                ),
                category="manufacturing",
                target=goal.recipe_id,
                quantity=shortage,
                constraints=production["blockers"],
                priority=NORMAL,
            )
        )

    return tasks
