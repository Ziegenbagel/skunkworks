"""Desired fuel-reserve planning."""

from src.planner.priorities import HIGH
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    current = operations.probes.fuel_percent()
    minimum = desired_state.fuel.minimum_percent

    if current >= minimum:
        return []

    target = operations.mining.best_target("deuterium")
    fuel = operations.world.probe.get("fuel") or {}
    maximum = float(fuel.get("maxDeuterium", 0) or 0)
    desired_amount = maximum * float(minimum) / 100
    current_amount = float(fuel.get("deuterium", 0) or 0)
    committed = float(operations.mining.active_commitments().get("deuterium", 0) or 0)
    uncovered = max(0, desired_amount - current_amount - committed)
    if uncovered <= 0.00001:
        return []
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
                f"desired minimum is {minimum:.1f}%. "
                f"The tank needs {desired_amount - current_amount:.3f} ECE; "
                f"{committed:.3f} ECE is already committed and "
                f"{uncovered:.3f} ECE remains uncovered."
            ),
            category="fuel",
            target=(
                target["id"]
                if target is not None
                else "deuterium"
            ),
            constraints=tuple(constraints),
            quantity=round(min(
                uncovered,
                float(target.get("available_amount", uncovered)) if target is not None else uncovered,
            ), 3),
            maximum_order_amount=desired_state.maximum_mining_order_amount,
            resource_type="deuterium",
            priority=desired_state.fuel.priority,
        )
    ]
