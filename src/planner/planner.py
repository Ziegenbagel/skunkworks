"""Planner for generating recommended tasks."""

from .task import Task


class Planner:
    """Generates recommended tasks from the current operational state."""

    def __init__(
        self,
        operations,
    ):
        self.operations = operations

    def tasks(self) -> list[Task]:
        """Return the current recommended task list."""

        tasks: list[Task] = []

        probe_service = self.operations.probes

        if probe_service.is_idle():

            tasks.append(
                Task(
                    category="Exploration",
                    action="Assess Current Probe",
                    target="Current Probe",
                    priority=1,
                    reason=(
                        "Probe is idle and awaiting work."
                    ),
                )
            )

        return tasks