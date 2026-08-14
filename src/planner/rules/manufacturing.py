"""Desired-State manufacturing planning."""

from src.planner.priorities import NORMAL
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    tasks = []
    active_commitments = operations.mining.active_commitments()

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
            use_inventory_items=False,
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

        inbound_parts = []
        for resource, missing in production["missing_resources"].items():
            committed = float(active_commitments.get(resource, 0) or 0)
            if committed <= 0:
                continue
            covered = min(float(missing), committed)
            uncovered = max(0.0, float(missing) - committed)
            inbound_parts.append(
                f"{resource.replace('_', ' ')} {covered:.3f} ECE inbound, "
                f"{uncovered:.3f} ECE uncovered"
            )
        inbound_note = (
            " Active mining commitments: " + "; ".join(inbound_parts) + "."
            if inbound_parts else ""
        )

        tasks.append(
            Task(
                action=(
                    "Craft Item"
                    if production["achievable"]
                    else "Prepare Manufacturing"
                ),
                reason=(
                    f"Desired quantity is {goal.quantity}; {stored} stored, "
                    f"{active} crafting, and {shortage} still required. "
                    "Dispatch readiness is evaluated one craft at a time: "
                    "only the next unit's inputs are reserved, and all goals "
                    "are reconsidered after each planning cycle."
                    " Ordinary recipes are submitted as one direct game recipe; "
                    "Skunkworks does not create surplus intermediate inventory."
                    + inbound_note
                ),
                category="manufacturing",
                target=goal.recipe_id,
                quantity=shortage,
                constraints=production["blockers"],
                priority=goal.priority,
            )
        )

    return tasks
