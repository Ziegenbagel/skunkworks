"""Desired-State manufacturing planning."""

from src.planner.priorities import NORMAL
from src.planner.task import Task


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
