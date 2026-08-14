"""Planner for generating recommended tasks."""

from .task import Task
from .desired_state import DesiredState
from .scheduling import ordered_tasks
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

    def __init__(
        self, operations, desired_state=None, *, dependency_mining_lookahead=False,
    ):
        self.operations = operations
        self.desired_state = (
            desired_state
            if desired_state is not None
            else DesiredState.empty()
        )
        self.dependency_mining_lookahead = dependency_mining_lookahead

    def tasks(self) -> list[Task]:
        """Return the current recommended task list."""

        tasks: list[Task] = []

        tasks.extend(
            safety.plan(self.operations, self.desired_state)
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
        # At the same explicit priority, fleet assembly is the primary goal.
        # Its component work and dependency mining should be considered before
        # ordinary production quantities. Across different priorities, the
        # configured number is authoritative and is reconsidered every cycle.
        tasks.extend(fleet.plan(self.operations, self.desired_state))
        tasks.extend(
            manufacturing.plan(
                self.operations,
                self.desired_state,
            )
        )
        tasks.extend(
            mining.plan(
                self.operations,
                self.desired_state,
                dependency_lookahead=self.dependency_mining_lookahead,
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

        return ordered_tasks(tasks)
