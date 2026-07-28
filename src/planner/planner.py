"""Planner for generating recommended tasks."""

from .task import Task
from .rules import (
    idle,
    safety,
)


class Planner:
    """Generates recommended tasks from the current operational state."""

    def __init__(self, operations):
        self.operations = operations

    def tasks(self) -> list[Task]:
        """Return the current recommended task list."""

        tasks: list[Task] = []

        tasks.extend(
            safety.plan(self.operations)
        )

        tasks.extend(
            idle.plan(self.operations)
        )

        tasks.sort(
            key=lambda task: task.priority
        )

        return tasks