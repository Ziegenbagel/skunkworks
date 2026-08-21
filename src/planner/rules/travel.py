"""Desired destination and FCC route planning."""

from src.planner.priorities import NORMAL
from src.planner.task import Task


def plan(operations, desired_state) -> list[Task]:
    if desired_state.travel is None:
        return []

    requested_target = desired_state.travel.target
    target = requested_target
    redirected = False
    if operations.travel_safety.is_black_hole_sector(requested_target):
        safe_target = operations.travel_safety.nearest_safe_scut_sector(requested_target)
        if safe_target is None:
            return [Task(
                action="Prepare Probe Travel",
                reason="Requested destination contains a confirmed black hole and no verified safe SCUT-covered fallback sector is available.",
                category="travel",
                target=f"{requested_target.x}:{requested_target.y}:{requested_target.z}",
                constraints=("black_hole_destination_without_safe_fallback",),
                destination=requested_target,
                priority=NORMAL,
            )]
        target = safe_target
        redirected = True
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
    ) and not desired_state.travel.scut_exit_acknowledged:
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
                (
                    f"Requested destination {requested_target.x}:{requested_target.y}:{requested_target.z} contains a confirmed black hole; redirecting to nearest verified safe SCUT sector {target.x}:{target.y}:{target.z}. "
                    if redirected else f"Desired destination is {target.x}:{target.y}:{target.z}; "
                )
                + f"selected route is {route_name} "
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
            require_scut_coverage=(
                not desired_state.travel.scut_exit_acknowledged
            ),
            risk_acknowledged=desired_state.travel.risk_acknowledged,
            # Saving an automatic destination or transport cycle is the
            # operator's authorization for its ordinary travel legs. Keep
            # hazard acknowledgement separate so genuinely risky routes still
            # pause for explicit consent.
            workflow_authorized=True,
            priority=NORMAL,
        )
    ]
