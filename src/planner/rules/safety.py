"""Safety planning rules."""

from src.planner.task import Task
from src.planner.priorities import (
    CRITICAL,
    HIGH,
)

def plan(operations, desired_state=None) -> list[Task]:
    """
    Generate safety-related tasks.
    """

    tasks: list[Task] = []

    probe_service = operations.probes
    snapshot_service = operations.snapshots

    # Probe repair is optional and probe-scoped. The API repair value is the
    # percentage restored, rather than a target integrity percentage.
    if desired_state is not None and desired_state.repair.trigger_percent > 0:
        current = float(operations.world.probe.get("systems", {}).get("integrityPercent", 100))
        goal = desired_state.repair
        if current <= goal.trigger_percent and current < goal.target_percent:
            constraints = () if operations.mining.idle_mannies() else ("no_idle_manny",)
            tasks.append(Task(
                action="Repair Probe",
                reason=(f"Probe integrity is {current:.1f}%, at or below the "
                        f"{goal.trigger_percent:.1f}% repair trigger; restore to "
                        f"{goal.target_percent:.1f}%."),
                category="repair",
                quantity=goal.target_percent - current,
                constraints=constraints,
                priority=goal.priority,
            ))

    #
    # Snapshot freshness
    #

    if (
        not snapshot_service.is_fresh()
        and probe_service.current()["telemetry_available"]
        and not probe_service.is_traveling()
    ):

        tasks.append(
            Task(
                action="Refresh Snapshot",
                reason="Snapshot is stale.",
                category="safety",
                priority=HIGH,
            )
        )

    #
    # Probe movement
    #

    if probe_service.is_traveling():

        tasks.append(
            Task(
                action="Wait for Probe Arrival",
                reason=(
                    "Probe is currently traveling "
                    "between sectors."
                ),
                category="safety",
                priority=CRITICAL,
            )
        )

    #
    # Inventory pressure
    #

    if probe_service.inventory_used_percent() >= 85:

        tasks.append(
            Task(
                action="Unload Probe",
                reason=(
                    "Probe cargo capacity is becoming "
                    "limited."
                ),
                category="safety",
                priority=HIGH,
            )
        )

    return tasks
