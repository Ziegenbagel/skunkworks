"""Desired fuel-reserve planning."""

from src.planner.priorities import HIGH
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    current = operations.probes.fuel_percent()
    minimum = desired_state.fuel.minimum_percent
    fuel = operations.world.probe.get("fuel") or {}
    maximum = float(fuel.get("maxDeuterium", 0) or 0)
    desired_amount = maximum * float(minimum) / 100
    current_amount = float(fuel.get("deuterium", 0) or 0)
    current_sector = operations.travel.current_sector()
    travel_pending = (
        desired_state.travel is not None
        and current_sector is not None
        and current_sector != desired_state.travel.target
    )
    if travel_pending:
        # The configured floor is arrival fuel, not departure fuel. Refill the
        # next leg's fixed cost before automatic travel can consume the floor.
        desired_amount = min(maximum, desired_amount + operations.travel.fuel_cost())

    if current_amount + 0.00001 >= desired_amount:
        return []

    target = operations.mining.best_target("deuterium")
    committed = float(operations.mining.active_commitments().get("deuterium", 0) or 0)
    uncovered = max(0, desired_amount - current_amount - committed)
    if uncovered <= 0.00001:
        return []
    constraints = []

    if (
        current_sector is not None
        and operations.travel_safety.is_black_hole_sector(current_sector)
    ):
        constraints.append("black_hole_sector_unsafe_for_refueling")

    if target is None:
        constraints.append("deuterium_not_in_current_sector")

    if not operations.mining.idle_mannies():
        constraints.append("no_idle_manny")

    if operations.world.probe["status"] != "idle":
        constraints.append("probe_unavailable")

    travel_reason = (
        f"The pending travel leg also requires {operations.travel.fuel_cost():.3f} ECE. "
        if travel_pending else ""
    )

    return [
        Task(
            action=(
                "Mine Deuterium"
                if not constraints
                else "Restore Fuel Reserve"
            ),
            reason=(
                f"Fuel is {current:.1f}%; "
                f"desired arrival minimum is {minimum:.1f}%. "
                f"{travel_reason}"
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
