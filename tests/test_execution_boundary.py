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
from src.execution.policy import ExecutionPolicyStore
from src.execution.translator import TaskCommandTranslator
from src.models.galaxy import SectorCoordinates
from src.planner.desired_state import (
    DesiredState,
    FuelGoal,
    FleetGoal,
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
                "targetAmount": 0.55,
            },
        )
        self.assertEqual(command.metadata["remainingAmount"], 0.45)
        self.assertEqual(command.metadata["estimatedTrips"], 11)

    def test_prepared_mining_orders_claim_distinct_idle_mannies(self):
        self.operations.world.mannies["mannies"].append({
            "id": 202,
            "currentTask": None,
            "canReceiveOrders": True,
            "location": {"type": "probe"},
            "cargo": {"capacity": 0.05},
        })
        translator = TaskCommandTranslator(self.operations, 1)
        from src.planner.task import Task
        first = translator.translate(Task(
            action="Mine Resource", reason="Metals reserve", target="asteroid-1",
            quantity=2, resource_type="metals", priority=3,
        ))
        second = translator.translate(Task(
            action="Mine Resource", reason="Ice reserve", target="asteroid-1",
            quantity=2, resource_type="ice", priority=3,
        ))

        self.assertEqual({first.target_id, second.target_id}, {101, 202})

    def test_ready_tanker_goal_becomes_special_assembly_command(self):
        from src.planner.assembly import TANKER_COMPONENTS

        self.operations.world.fleet = {"probes": [{"model": "generic"}]}
        inventory = self.operations.world.probe["inventory"]
        inventory["items"] = [
            {"id": f"{item}-{index}", "type": item}
            for item, quantity in TANKER_COMPONENTS
            for index in range(quantity)
        ]
        inventory["containers"] = [
            {"id": "container-a", "kind": "container", "capacity": 1, "usedCapacity": 0},
            {"id": "container-b", "kind": "container", "capacity": 1, "usedCapacity": 0},
        ]

        prepared = self.prepare(DesiredState(
            fleet=(FleetGoal("deuterium_tanker", 1, priority=1),),
        ))
        command = prepared[0].command

        self.assertEqual(command.type, CommandType.MANNY_ASSEMBLE_PROBE)
        self.assertEqual(command.priority, 1)
        self.assertEqual(command.payload, {"containerIds": ["container-a", "container-b"]})

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

    def test_execution_policy_store_round_trips_live_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ExecutionPolicyStore(Path(temporary) / "execution.json")
            expected = ExecutionPolicy(
                mode=ExecutionMode.AUTOMATIC,
                live_execution_enabled=True,
                allowed_command_types=frozenset({CommandType.MANNY_CRAFT}),
                max_commands_per_cycle=3,
            )

            store.save(expected)

            self.assertEqual(store.load(), expected)

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
