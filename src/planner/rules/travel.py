"""Desired destination and FCC route planning."""

from src.planner.priorities import NORMAL
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    if desired_state.travel is None:
        return []

    target = desired_state.travel.target
    blockers = list(operations.travel.travel_blockers(target))

    # Auto-travel is a durable destination, not permission to leave during a
    # safety intervention. Hold the route between hops while repair is needed
    # or active, and until every Manny task has completed and any deployed
    # Manny has returned aboard the probe. The unchanged desired destination
    # makes the next planning cycle resume automatically once these clear.
    repair = desired_state.repair
    integrity = float(
        operations.world.probe.get("systems", {}).get("integrityPercent", 100)
    )
    mannies = operations.mannies.all()
    repair_active = any(
        operations.mannies._task_type(manny) == "repairing"
        or operations.mannies._task_type(manny) == "repair"
        for manny in mannies
    )
    if repair.trigger_percent > 0 and (
        integrity <= repair.trigger_percent or repair_active
    ) and integrity < repair.target_percent:
        blockers.append("repair_required_before_travel")
    if any(manny.get("currentTask") is not None for manny in mannies):
        blockers.append("manny_tasks_in_progress")
    if operations.mannies.deployed():
        blockers.append("mannies_not_aboard")
    if blockers == ["already_at_destination"]:
        return []

    assessment = operations.travel_safety.assess(
        target,
        route_mode=desired_state.travel.route_mode,
        maximum_segment_distance=desired_state.maximum_safe_hop_distance,
    )
    route = (
        assessment.recommended.hops
        if assessment is not None
        else ()
    )
    next_hop_assessment = (
        operations.travel_safety.assess(
            route[0],
            route_mode=desired_state.travel.route_mode,
            maximum_segment_distance=desired_state.maximum_safe_hop_distance,
        )
        if route
        else None
    )
    distance = len(route)
    route_name = (
        assessment.recommended.name
        if assessment is not None
        else "unavailable"
    )
    if assessment is not None and (
        operations.travel_safety.scut_route_covered(
            assessment.origin,
            route,
        ) is False
    ):
        blockers.append("route_leaves_scut_coverage")
    blockers = tuple(dict.fromkeys(blockers))

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
                f"selected route is {route_name} "
                f"with {distance} hop(s)."
            ),
            category="travel",
            target=f"{target.x}:{target.y}:{target.z}",
            constraints=blockers,
            destination=target,
            route=route,
            hazards=(
                next_hop_assessment.hazards
                if next_hop_assessment is not None
                else ()
            ),
            require_scut_coverage=True,
            risk_acknowledged=desired_state.travel.risk_acknowledged,
            priority=NORMAL,
        )
    ]
