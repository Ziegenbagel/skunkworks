"""Desired destination and FCC route planning."""

from src.planner.priorities import NORMAL
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    if desired_state.travel is None:
        return []

    target = desired_state.travel.target
    blockers = operations.travel.travel_blockers(target)

    if blockers == ("already_at_destination",):
        return []

    route = operations.travel.route_to(target)
    distance = len(route) if route is not None else 0

    return [
        Task(
            action=(
                "Move Probe"
                if not blockers
                else "Prepare Probe Travel"
            ),
            reason=(
                f"Desired destination is "
                f"{target.x}:{target.y}:{target.z}; "
                f"FCC distance is {distance}."
            ),
            category="travel",
            target=f"{target.x}:{target.y}:{target.z}",
            constraints=blockers,
            priority=NORMAL,
        )
    ]
