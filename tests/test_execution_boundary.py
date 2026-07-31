import tempfile
import unittest
from pathlib import Path

from src.data import DataEngine
from src.execution import (
    CommandPreparer,
    CommandType,
    ExecutionMode,
    ExecutionPolicy,
)
from src.execution.journal import ActionJournal
from src.models.galaxy import SectorCoordinates
from src.planner.desired_state import (
    DesiredState,
    FuelGoal,
    InventoryGoal,
    ProductionGoal,
    ResourceGoal,
    TravelGoal,
)
from src.planner.planner import Planner
from tests.test_planner_missions import build_operations


class ExecutionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.operations = build_operations()
        self.policy = ExecutionPolicy(
            mode=ExecutionMode.OBSERVE,
            live_execution_enabled=False,
            max_commands_per_cycle=10,
        )

    def prepare(self, desired_state, journal=None):
        tasks = Planner(
            self.operations,
            desired_state,
        ).tasks()
        return CommandPreparer(
            self.operations,
            probe_id=1,
            policy=self.policy,
            journal=journal,
        ).prepare(tasks)

    def test_craft_task_becomes_typed_dry_run_command(self):
        prepared = self.prepare(
            DesiredState(
                production=(
                    ProductionGoal("storage_container", 1),
                )
            )
        )

        self.assertEqual(len(prepared), 1)
        self.assertEqual(
            prepared[0].command.type,
            CommandType.MANNY_CRAFT,
        )
        self.assertEqual(
            prepared[0].command.payload,
            {"recipe": "storage_container"},
        )
        self.assertEqual(
            prepared[0].disposition,
            "dry_run",
        )

    def test_mining_task_uses_contract_payload(self):
        self.operations = build_operations(metals=0)
        prepared = self.prepare(
            DesiredState(
                resources=(ResourceGoal("metals", 1),),
            )
        )
        command = prepared[0].command

        self.assertEqual(
            command.type,
            CommandType.MANNY_MINE,
        )
        self.assertEqual(
            command.payload,
            {
                "objectId": "asteroid-1",
                "resources": ["metals"],
                "targetAmount": 1,
            },
        )

    def test_travel_command_uses_safe_direct_distance(self):
        prepared = self.prepare(
            DesiredState(
                fuel=FuelGoal(0),
                inventory=InventoryGoal(0),
                travel=TravelGoal(
                    SectorCoordinates(2, 0, 0)
                ),
            )
        )
        command = prepared[0].command

        self.assertEqual(
            command.type,
            CommandType.MOVE_PROBE,
        )
        self.assertEqual(
            command.metadata["remainingHops"],
            1,
        )
        self.assertEqual(
            sum(command.payload["target"].values()) % 2,
            0,
        )

    def test_constrained_tasks_never_become_commands(self):
        self.operations = build_operations(status="cruising")

        self.assertEqual(
            self.prepare(
                DesiredState(
                    production=(
                        ProductionGoal(
                            "storage_container",
                            1,
                        ),
                    )
                )
            ),
            (),
        )

    def test_policy_requires_explicit_allowlist_for_ready(self):
        task = Planner(
            self.operations,
            DesiredState(
                production=(
                    ProductionGoal("storage_container", 1),
                )
            ),
        ).tasks()
        policy = ExecutionPolicy(
            mode=ExecutionMode.AUTOMATIC,
            live_execution_enabled=True,
            allowed_command_types=frozenset(),
        )
        prepared = CommandPreparer(
            self.operations,
            1,
            policy,
        ).prepare(task)

        self.assertEqual(
            prepared[0].disposition,
            "awaiting_approval",
        )

    def test_travel_warning_is_advisory_by_default(self):
        self.operations.world.probe["inventory"][
            "containers"
        ] = [
            {"kind": "probe"},
            *({"kind": "container"} for _ in range(5)),
        ]
        prepared = self.prepare(
            DesiredState(
                fuel=FuelGoal(0),
                inventory=InventoryGoal(0),
                travel=TravelGoal(
                    SectorCoordinates(2, 0, 0)
                ),
            )
        )[0]

        self.assertEqual(prepared.disposition, "dry_run")
        self.assertEqual(prepared.blockers, ())
        self.assertTrue(prepared.warnings)

    def test_journal_blocks_completed_command(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = ActionJournal(
                DataEngine(Path(directory) / "journal.sqlite3")
            )
            first = self.prepare(
                DesiredState(
                    production=(
                        ProductionGoal(
                            "storage_container",
                            1,
                        ),
                    )
                ),
                journal,
            )[0]
            journal.data_engine.record_action(
                first.command.fingerprint,
                first.command.to_dict(),
                "succeeded",
            )
            repeated = self.prepare(
                DesiredState(
                    production=(
                        ProductionGoal(
                            "storage_container",
                            1,
                        ),
                    )
                ),
                journal,
            )[0]

            self.assertEqual(
                repeated.disposition,
                "blocked",
            )
            self.assertIn(
                "already_completed",
                repeated.blockers,
            )


if __name__ == "__main__":
    unittest.main()
