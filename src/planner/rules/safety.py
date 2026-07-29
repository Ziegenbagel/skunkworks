"""Safety planning rules."""

from src.planner.task import Task
from src.planner.priorities import (
    CRITICAL,
    HIGH,
)

def plan(operations) -> list[Task]:
    """
    Generate safety-related tasks.
    """

    tasks: list[Task] = []

    probe_service = operations.probes
    snapshot_service = operations.snapshots

    #
    # Snapshot freshness
    #

    if not snapshot_service.is_fresh():

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

    #
    # Fuel awareness
    #

    if probe_service.fuel_percent() < 20:

        tasks.append(
            Task(
                action="Refuel Probe",
                reason=(
                    "Internal deuterium reserves are "
                    "running low."
                ),
                category="safety",
                priority=HIGH,
            )
        )

    return tasks