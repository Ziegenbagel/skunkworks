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

    probe = operations.world.probe
    snapshot = operations.world.snapshot

    #
    # Snapshot freshness
    #

    if not snapshot["fresh"]:

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

    movement = probe["movement"]

    if movement["status"] != "arrived":

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

    return tasks