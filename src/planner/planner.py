"""Planner for generating recommended tasks."""

from .task import Task
from .desired_state import DesiredState
from .rules import (
    fuel,
    fleet,
    idle,
    inventory,
    manufacturing,
    mining,
    safety,
    sustainability,
    travel,
)


class Planner:
    """Generates recommended tasks from the current operational state."""

    def __init__(self, operations, desired_state=None):
        self.operations = operations
        self.desired_state = (
            desired_state
            if desired_state is not None
            else DesiredState.empty()
        )

    def tasks(self) -> list[Task]:
        """Return the current recommended task list."""

        tasks: list[Task] = []

        tasks.extend(
            safety.plan(self.operations)
        )

        tasks.extend(
            inventory.plan(
                self.operations,
                self.desired_state,
            )
        )
        tasks.extend(
            fuel.plan(
                self.operations,
                self.desired_state,
            )
        )
        tasks.extend(
            manufacturing.plan(
                self.operations,
                self.desired_state,
            )
        )
        tasks.extend(fleet.plan(self.operations, self.desired_state))
        tasks.extend(
            mining.plan(
                self.operations,
                self.desired_state,
            )
        )
        tasks.extend(
            sustainability.plan(self.operations)
        )
        tasks.extend(
            travel.plan(
                self.operations,
                self.desired_state,
            )
        )

        if not tasks:
            tasks.extend(idle.plan(self.operations))

        tasks.sort(
            key=lambda task: task.priority
        )

        return tasks
