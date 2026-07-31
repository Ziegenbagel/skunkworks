"""Desired fuel-reserve planning."""

from src.planner.priorities import HIGH
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    current = operations.probes.fuel_percent()
    minimum = desired_state.fuel.minimum_percent

    if current >= minimum:
        return []

    target = operations.mining.best_target("deuterium")
    constraints = []

    if target is None:
        constraints.append("deuterium_not_in_current_sector")

    if not operations.mining.idle_mannies():
        constraints.append("no_idle_manny")

    if operations.world.probe["status"] != "idle":
        constraints.append("probe_unavailable")

    return [
        Task(
            action=(
                "Mine Deuterium"
                if not constraints
                else "Restore Fuel Reserve"
            ),
            reason=(
                f"Fuel is {current:.1f}%; "
                f"desired minimum is {minimum:.1f}%."
            ),
            category="fuel",
            target=(
                target["id"]
                if target is not None
                else "deuterium"
            ),
            constraints=tuple(constraints),
            priority=HIGH,
        )
    ]
