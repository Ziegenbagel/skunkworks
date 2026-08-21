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

        available_resources, _available_items = (
            operations.manufacturing.available_inputs()
        )
        resource_parts = []
        for resource, required in production["required_resources"].items():
            onboard = min(
                float(required), float(available_resources.get(resource, 0) or 0),
            )
            missing = float(
                production["missing_resources"].get(resource, 0) or 0
            )
            committed = float(active_commitments.get(resource, 0) or 0)
            # Mining commitments use the probe tank's hundredths-of-an-ECE
            # convention, while recipe requirements and this explanation use
            # ECE.
            if resource == "deuterium":
                committed /= 100.0
            inbound = min(missing, committed)
            uncovered = max(0.0, float(missing) - committed)
            resource_parts.append(
                f"{resource.replace('_', ' ')}: {float(required):.4f} ECE required, "
                f"{onboard:.4f} onboard, {inbound:.4f} inbound, "
                f"{uncovered:.4f} still uncovered"
            )
        resource_note = (
            " Next unit resources — " + "; ".join(resource_parts) + "."
            if resource_parts else ""
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
                    + resource_note
                ),
                category="manufacturing",
                target=goal.recipe_id,
                quantity=shortage,
                constraints=production["blockers"],
                priority=goal.priority,
            )
        )

    return tasks
