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

    assessment = operations.travel_safety.assess(target)
    route = (
        assessment.recommended.hops
        if assessment is not None
        else ()
    )
    distance = len(route)
    route_name = (
        assessment.recommended.name
        if assessment is not None
        else "unavailable"
    )

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
                f"recommended route is {route_name} "
                f"with {distance} hop(s)."
            ),
            category="travel",
            target=f"{target.x}:{target.y}:{target.z}",
            constraints=blockers,
            destination=target,
            route=route,
            hazards=(
                assessment.hazards
                if assessment is not None
                else ()
            ),
            priority=NORMAL,
        )
    ]
