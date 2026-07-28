"""Idle planning rules."""

from src.planner.task import Task
from src.planner.priorities import INFO


def plan(operations) -> list[Task]:
    """
    Generate tasks related to idle probes.
    """

    tasks: list[Task] = []

    probe_service = operations.probes

    if probe_service.is_idle():

        tasks.append(
            Task(
                action="Assess Current Probe",
                reason="Probe is idle and awaiting work.",
                category="exploration",
                target="Current Probe",
                priority=INFO,
            )
        )

    return tasks