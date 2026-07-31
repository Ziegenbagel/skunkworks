"""Desired free-capacity planning."""

from src.planner.priorities import HIGH
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    current = operations.inventory.free_capacity()
    minimum = (
        desired_state.inventory.minimum_free_capacity
    )

    if current >= minimum:
        return []

    return [
        Task(
            action="Free Cargo Capacity",
            reason=(
                f"Free capacity is {current:.3f} ECE; "
                f"desired minimum is {minimum:.3f} ECE."
            ),
            category="inventory",
            target="Current Probe",
            quantity=round(minimum - current, 3),
            constraints=("inventory_capacity_low",),
            priority=desired_state.inventory.priority,
        )
    ]
