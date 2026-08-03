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

    def test_repeat_craft_identity_advances_after_inventory_changes(self):
        from src.planner.task import Task

        task = Task(
            action="Craft Item",
            reason="Repeated container production",
            target="storage_container",
            quantity=3,
            priority=1,
        )
        first = TaskCommandTranslator(self.operations, 1).translate(task)
        unchanged_retry = TaskCommandTranslator(self.operations, 1).translate(task)

        self.assertEqual(first.fingerprint, unchanged_retry.fingerprint)

        self.operations.world.probe["inventory"].setdefault("items", []).append({
            "id": "completed-container",
            "type": "storage_container",
        })
        next_unit = TaskCommandTranslator(self.operations, 1).translate(task)

        self.assertNotEqual(first.fingerprint, next_unit.fingerprint)
        self.assertEqual(next_unit.metadata["storedBefore"], first.metadata["storedBefore"] + 1)

    def test_repeat_craft_identity_advances_when_same_count_has_new_item(self):
        from src.planner.task import Task

        task = Task(
            action="Craft Item", reason="Replacement production",
            target="storage_container", priority=1,
        )
        items = self.operations.world.probe["inventory"].setdefault("items", [])
        items.append({"id": "old-output", "type": "storage_container"})
        first = TaskCommandTranslator(self.operations, 1).translate(task)
        items[-1] = {"id": "replacement-output", "type": "storage_container"}
        replacement = TaskCommandTranslator(self.operations, 1).translate(task)

        self.assertEqual(first.metadata["storedBefore"], replacement.metadata["storedBefore"])
        self.assertNotEqual(first.fingerprint, replacement.fingerprint)

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

    def test_reserve_floor_mining_cannot_saturate_manny_workforce(self):
        for manny_id in range(102, 110):
            self.operations.world.mannies["mannies"].append({
                "id": manny_id,
                "currentTask": None,
                "canReceiveOrders": True,
                "location": {"type": "probe"},
            })
        desired = DesiredState(resources=(
            ResourceGoal("metals", 10, priority=2),
            ResourceGoal("ice", 10, priority=2),
            ResourceGoal("carbon_compounds", 10, priority=2),
            ResourceGoal("deuterium", 10, priority=2),
        ))
        self.operations.world.sector["resources"][0]["resources"].update({
            "ice": 20,
            "carbon_compounds": 20,
        })

        prepared = self.prepare(desired)
        mining = [item for item in prepared if item.command.type == CommandType.MANNY_MINE]

        self.assertEqual(len(mining), 3)
        self.assertTrue(all("background work" in item.command.reason for item in mining))

    def test_production_dependency_mining_is_not_background_throttled(self):
        self.operations = build_operations(metals=0)
        tasks = Planner(
            self.operations,
            DesiredState(production=(ProductionGoal("storage_container", 1, priority=1),)),
        ).tasks()
        mining = next(task for task in tasks if task.category == "mining")

        self.assertFalse(mining.background_work)

    def test_automatic_mining_prefers_resource_assigned_detached_container(self):
        self.operations.world.sector["snapshot"] = {"sector": {"objects": [
            {
                "id": "unassigned", "type": "detached_container",
                "mode": "drifting", "capacity": 1, "usedCapacity": 0,
                "rules": {},
            },
            {
                "id": "metals-depot", "type": "detached_container",
                "mode": "hidden_on_asteroid", "targetObjectId": "asteroid-1",
                "capacity": 1, "usedCapacity": 0,
                "rules": {"priority": ["metals"]},
            },
        ]}}
        from src.planner.task import Task
        command = TaskCommandTranslator(self.operations, 1).translate(Task(
            action="Mine Resource", reason="Metals reserve", target="asteroid-1",
            quantity=0.5, resource_type="metals", priority=3,
        ))

        self.assertEqual(command.payload["targetContainerId"], "metals-depot")

    def test_active_tanker_component_does_not_request_zero_quantity_recipe_plan(self):
        from src.planner.assembly import TANKER_COMPONENTS

        component, required = TANKER_COMPONENTS[0]
        self.operations.world.probe["inventory"]["items"] = [
            item for item in self.operations.world.probe["inventory"].get("items", ())
            if item.get("type") != component
        ]
        self.operations.world.mannies["mannies"][0]["currentTask"] = {
            "type": "crafting", "recipe": component,
        }
        desired = DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=1),))

        tasks = Planner(self.operations, desired).tasks()

        self.assertTrue(any(task.action == "Await Active Production" for task in tasks))
        self.assertFalse(any(
            task.action in {"Mine Resource", "Mine Deuterium"}
            and component in task.reason
            for task in tasks
        ))

    def test_tanker_mining_reason_names_component_it_unlocks(self):
        from src.planner.assembly import TANKER_COMPONENTS

        for component, _quantity in TANKER_COMPONENTS:
            self.operations.manufacturing.recipes._recipes[component] = {
                "id": component,
                "name": component.replace("_", " ").title(),
                "craftableBy": ["manny"],
                "durationSeconds": 60,
                "ingredients": [
                    {"type": "metals", "quantity": 1, "kind": "resource"},
                ],
                "output": {"type": component, "containerSpace": 0.1},
            }
        self.operations.world.probe["inventory"]["resourceStocks"][0]["amount"] = 0
        desired = DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=1),))

        mining = next(
            task for task in Planner(self.operations, desired).tasks()
            if task.category == "mining" and task.resource_type == "metals"
        )

        self.assertIn("tanker component: integrated circuit", mining.reason)
        self.assertIn("This mining order unlocks", mining.reason)

    def test_lower_priority_craft_cannot_reuse_reserved_resources(self):
        from src.planner.task import Task

        self.operations.world.probe["inventory"]["resourceStocks"][0]["amount"] = 1
        self.operations.manufacturing.recipes._recipes["priority_component"] = {
            "id": "priority_component",
            "name": "Priority component",
            "craftableBy": ["manny"],
            "durationSeconds": 60,
            "ingredients": [{"type": "metals", "quantity": 1, "kind": "resource"}],
            "output": {"type": "priority_component", "containerSpace": 0.1},
        }
        self.operations.world.mannies["mannies"].append({
            "id": 202, "currentTask": None, "canReceiveOrders": True,
            "location": {"type": "probe"},
        })
        policy = ExecutionPolicy(
            mode=ExecutionMode.AUTOMATIC,
            live_execution_enabled=True,
            allowed_command_types=frozenset({CommandType.MANNY_CRAFT}),
            max_commands_per_cycle=10,
        )
        prepared = CommandPreparer(self.operations, 1, policy).prepare([
            Task(action="Craft Item", reason="Tanker component", target="priority_component", priority=1),
            Task(action="Craft Item", reason="Lower goal", target="storage_container", priority=5),
        ])

        self.assertEqual(prepared[0].disposition, "ready")
        self.assertEqual(prepared[1].disposition, "blocked")
        self.assertIn("resource_reserved_by_higher_priority_goal", prepared[1].blockers)

    def test_lower_priority_recipe_cannot_consume_stored_tanker_components(self):
        from src.planner.task import Task

        self.operations.world.probe["inventory"].setdefault("items", []).extend(
            {"id": f"plate-{index}", "type": "steel_plate"}
            for index in range(9)
        )
        self.operations.manufacturing.recipes._recipes["uses_plate"] = {
            "id": "uses_plate", "name": "Uses plate", "craftableBy": ["manny"],
            "durationSeconds": 60,
            "ingredients": [{"type": "steel_plate", "quantity": 1, "kind": "item"}],
            "output": {"type": "uses_plate", "containerSpace": 0.1},
        }
        self.operations.world.mannies["mannies"].append({
            "id": 202, "currentTask": None, "canReceiveOrders": True,
            "location": {"type": "probe"},
        })
        prepared = CommandPreparer(self.operations, 1, self.policy).prepare([
            Task(
                action="Prepare Manufacturing", reason="Protected tanker plates",
                target="steel_plate", constraints=("fabricator_unavailable",),
                reserved_items=(("steel_plate", 9),), priority=1,
            ),
            Task(
                action="Craft Item", reason="Lower-priority consumer",
                target="uses_plate", priority=2,
            ),
        ])

        consumer = next(
            item for item in prepared
            if item.command.reason == "Lower-priority consumer"
        )
        self.assertIn("item_reserved_by_higher_priority_goal", consumer.blockers)

    def test_blocked_craft_releases_manny_for_following_mining_order(self):
        from src.planner.task import Task

        self.operations.world.probe["inventory"].setdefault("items", []).append(
            {"id": "reserved-plate", "type": "steel_plate"}
        )
        self.operations.manufacturing.recipes._recipes["uses_plate"] = {
            "id": "uses_plate", "name": "Uses plate", "craftableBy": ["manny"],
            "durationSeconds": 60,
            "ingredients": [{"type": "steel_plate", "quantity": 1, "kind": "item"}],
            "output": {"type": "uses_plate", "containerSpace": 0.1},
        }
        prepared = CommandPreparer(self.operations, 1, self.policy).prepare([
            Task(
                action="Prepare Manufacturing", reason="Protected tanker plate",
                target="steel_plate", constraints=("active_production_pending",),
                reserved_items=(("steel_plate", 1),), priority=1,
            ),
            Task(
                action="Craft Item", reason="Blocked lower consumer",
                target="uses_plate", priority=2,
            ),
            Task(
                action="Mine Resource", reason="Useful fallback work",
                target="asteroid-1", resource_type="metals", quantity=0.55,
                priority=2,
            ),
        ])

        blocked = next(item for item in prepared if item.command.source_action == "Craft Item")
        mining = next(item for item in prepared if item.command.source_action == "Mine Resource")
        self.assertEqual(blocked.disposition, "blocked")
        self.assertNotEqual(mining.disposition, "blocked")
        self.assertEqual(mining.command.target_id, 101)

    def test_lower_priority_craft_can_use_surplus_beyond_reservation(self):
        from src.planner.task import Task

        self.operations.world.probe["inventory"]["resourceStocks"][0]["amount"] = 3
        self.operations.world.mannies["mannies"].append({
            "id": 202, "currentTask": None, "canReceiveOrders": True,
            "location": {"type": "probe"},
        })
        prepared = CommandPreparer(self.operations, 1, self.policy).prepare([
            Task(
                action="Craft Item", reason="High-priority containers",
                target="storage_container", quantity=2, priority=1,
            ),
            Task(
                action="Craft Item", reason="Opportunistic container",
                target="storage_container", quantity=1, priority=5,
            ),
        ])

        self.assertEqual(len(prepared), 2)
        self.assertNotIn(
            "resource_reserved_by_higher_priority_goal",
            prepared[1].blockers,
        )

    def test_equal_priority_goal_does_not_monopolize_inputs(self):
        from src.planner.task import Task

        self.operations.world.probe["inventory"]["resourceStocks"][0]["amount"] = 1
        self.operations.world.mannies["mannies"].append({
            "id": 202, "currentTask": None, "canReceiveOrders": True,
            "location": {"type": "probe"},
        })
        prepared = CommandPreparer(self.operations, 1, self.policy).prepare([
            Task(
                action="Prepare Manufacturing", reason="Large Manny target",
                target="storage_container", quantity=100, priority=2,
                constraints=("missing_resources",),
            ),
            Task(
                action="Craft Item", reason="Opportunistic short craft",
                target="storage_container", quantity=1, priority=2,
            ),
        ])

        opportunistic = next(
            item for item in prepared
            if item.command.reason == "Opportunistic short craft"
        )
        self.assertNotIn(
            "resource_reserved_by_higher_priority_goal",
            opportunistic.blockers,
        )

    def test_large_high_priority_batch_reserves_only_its_next_craft(self):
        from src.planner.task import Task

        self.operations.world.probe["inventory"]["resourceStocks"][0]["amount"] = 2
        self.operations.world.mannies["mannies"].append({
            "id": 202, "currentTask": None, "canReceiveOrders": True,
            "location": {"type": "probe"},
        })
        prepared = CommandPreparer(self.operations, 1, self.policy).prepare([
            Task(
                action="Prepare Manufacturing", reason="Large protected batch",
                target="storage_container", quantity=100, priority=1,
                constraints=("missing_resources",),
            ),
            Task(
                action="Craft Item", reason="Use genuine surplus",
                target="storage_container", quantity=1, priority=2,
            ),
        ])

        surplus_craft = next(
            item for item in prepared
            if item.command.reason == "Use genuine surplus"
        )
        self.assertNotIn(
            "resource_reserved_by_higher_priority_goal",
            surplus_craft.blockers,
        )

    def test_large_goal_can_dispatch_one_order_before_full_batch_is_funded(self):
        self.operations.world.probe["inventory"]["resourceStocks"][0]["amount"] = 1
        tasks = Planner(
            self.operations,
            DesiredState(production=(ProductionGoal("storage_container", 100, priority=1),)),
        ).tasks()
        manufacturing = next(task for task in tasks if task.category == "manufacturing")

        self.assertEqual(manufacturing.action, "Craft Item")
        self.assertEqual(manufacturing.quantity, 100)
        self.assertIn("one craft at a time", manufacturing.reason)

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
        self.assertEqual(command.payload, {
            "model": "deuterium_tanker",
            "containerIds": ["container-a", "container-b"],
        })

    def test_tanker_assembly_preserves_resource_assigned_containers(self):
        from src.planner.assembly import TANKER_COMPONENTS

        self.operations.world.fleet = {"probes": [{"model": "generic"}]}
        inventory = self.operations.world.probe["inventory"]
        inventory["items"] = [
            {"id": f"{item}-{index}", "type": item}
            for item, quantity in TANKER_COMPONENTS
            for index in range(quantity)
        ]
        inventory["containers"] = [
            {
                "id": "metals-depot", "kind": "container", "capacity": 1,
                "usedCapacity": 0, "rules": {"priority": ["metals"]},
            },
            {
                "id": "unassigned-a", "kind": "container", "capacity": 1,
                "usedCapacity": 0, "rules": {},
            },
            {
                "id": "unassigned-b", "kind": "container", "capacity": 1,
                "usedCapacity": 0,
                "rules": {"priority": [], "exclusion": [], "strictExclusion": []},
            },
        ]

        prepared = self.prepare(DesiredState(
            fleet=(FleetGoal("deuterium_tanker", 1, priority=1),),
        ))

        self.assertEqual(
            prepared[0].command.payload["containerIds"],
            ["unassigned-a", "unassigned-b"],
        )

    def test_tanker_assembly_waits_instead_of_consuming_assigned_container(self):
        from src.planner.assembly import TANKER_COMPONENTS

        self.operations.world.fleet = {"probes": [{"model": "generic"}]}
        inventory = self.operations.world.probe["inventory"]
        inventory["items"] = [
            {"id": f"{item}-{index}", "type": item}
            for item, quantity in TANKER_COMPONENTS
            for index in range(quantity)
        ]
        inventory["containers"] = [
            {
                "id": "assigned", "kind": "container", "capacity": 1,
                "usedCapacity": 0, "rules": {"priority": ["ice"]},
            },
            {
                "id": "unassigned", "kind": "container", "capacity": 1,
                "usedCapacity": 0, "rules": {},
            },
        ]

        tasks = Planner(
            self.operations,
            DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=1),)),
        ).tasks()
        assembly = next(task for task in tasks if task.category == "fleet_assembly")

        self.assertEqual(assembly.action, "Prepare Probe Assembly")
        self.assertEqual(
            assembly.constraints,
            ("two_unassigned_empty_containers_required",),
        )

    def test_active_tanker_component_is_not_ordered_twice(self):
        self.operations.world.fleet = {"probes": [{"model": "generic"}]}
        self.operations.world.probe["inventory"]["items"] = [
            {"id": "engine-1", "type": "deuterium_engine"},
        ]
        self.operations.world.mannies["mannies"][0].update({
            "currentTask": "crafting",
            "task": {"recipe": "scut_relay", "recipeName": "SCUT relay"},
        })
        tasks = Planner(
            self.operations,
            DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=1),)),
        ).tasks()

        self.assertEqual(tasks[0].action, "Await Active Production")
        self.assertIn("no duplicate order", tasks[0].reason)
        self.assertIn("1 active craft allocated", tasks[0].reason)
        self.assertEqual(CommandPreparer(self.operations, 1, self.policy).prepare(tasks), ())

    def test_tanker_builds_final_steel_plate_allotment_after_consuming_components(self):
        from src.planner.assembly import TANKER_COMPONENTS

        component_names = [component for component, _quantity in TANKER_COMPONENTS]

        self.assertEqual(component_names[-1], "steel_plate")
        self.assertLess(component_names.index("scut_relay"), component_names.index("steel_plate"))
        self.assertLess(component_names.index("integrated_circuit"), component_names.index("steel_plate"))
        self.assertLess(component_names.index("linear_actuator"), component_names.index("steel_plate"))

    def test_tanker_component_status_credits_stacked_api_inventory_quantity(self):
        from src.planner.assembly import tanker_component_statuses

        self.operations.world.probe["inventory"]["items"] = [{
            "id": "plate-stack", "type": "steel_plate", "quantity": 10,
        }]

        plate = next(
            status for status in tanker_component_statuses(self.operations)
            if status["component"] == "steel_plate"
        )
        self.assertEqual(plate["completed"], 10)
        self.assertEqual(plate["allocated_stored"], 10)
        self.assertEqual(plate["missing"], 0)

    def test_active_tanker_component_does_not_hide_remaining_build_plan(self):
        from src.planner.assembly import TANKER_COMPONENTS

        self.operations.world.fleet = {"probes": [{"model": "generic"}]}
        self.operations.world.probe["inventory"]["items"] = [
            {"id": "engine-1", "type": "deuterium_engine"},
        ]
        self.operations.world.mannies["mannies"][0].update({
            "currentTask": "crafting",
            "task": {"recipe": "scut_relay", "recipeName": "SCUT relay"},
        })

        tasks = Planner(
            self.operations,
            DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=1),)),
        ).tasks()
        tanker_tasks = [task for task in tasks if task.category == "fleet_assembly"]
        targets = {task.target for task in tanker_tasks}

        self.assertIn("scut_relay", targets)
        self.assertIn("electric_motor", targets)
        self.assertIn("integrated_circuit", targets)
        self.assertEqual(
            targets,
            {component for component, _ in TANKER_COMPONENTS} - {"deuterium_engine"},
        )
        self.assertTrue(all(task.priority == 1 for task in tanker_tasks))
        self.assertIn("component 2/8", tanker_tasks[0].reason.lower())

    def test_tanker_resource_mining_inherits_tanker_priority(self):
        from src.planner.assembly import TANKER_COMPONENTS

        self.operations.world.fleet = {"probes": [{"model": "generic"}]}
        for component, _ in TANKER_COMPONENTS:
            self.operations.manufacturing.recipes._recipes[component] = {
                "id": component,
                "name": component.replace("_", " ").title(),
                "craftableBy": ["manny"],
                "durationSeconds": 60,
                "ingredients": [
                    {"type": "metals", "quantity": 1, "kind": "resource"},
                ],
                "output": {"type": component, "containerSpace": 0.1},
            }
        for stock in self.operations.world.probe["inventory"]["resourceStocks"]:
            stock["amount"] = 0

        tasks = Planner(
            self.operations,
            DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=1),)),
        ).tasks()
        mining = [task for task in tasks if task.category == "mining"]

        self.assertTrue(mining)
        self.assertTrue(all(task.priority == 1 for task in mining))

    def test_tanker_component_can_start_before_full_batch_is_funded(self):
        self.operations.world.fleet = {"probes": [{"model": "generic"}]}
        self.operations.manufacturing.recipes._recipes["steel_plate"] = {
            "id": "steel_plate",
            "name": "Steel plate",
            "craftableBy": ["manny"],
            "durationSeconds": 60,
            "ingredients": [
                {"type": "metals", "quantity": 1, "kind": "resource"},
            ],
            "output": {"type": "steel_plate", "containerSpace": 0.1},
        }
        self.operations.world.probe["inventory"]["items"] = [
            {"id": f"{component}-{index}", "type": component}
            for component, quantity in (
                ("deuterium_engine", 1),
                ("scut_relay", 1),
                ("electric_motor", 5),
                ("atomic_printer_part", 2),
                ("solar_panel", 4),
            )
            for index in range(quantity)
        ]
        self.operations.world.probe["inventory"]["resourceStocks"][0]["amount"] = 1

        tasks = Planner(
            self.operations,
            DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=1),)),
        ).tasks()
        plate = next(task for task in tasks if task.target == "steel_plate")

        self.assertEqual(plate.action, "Craft Item")
        self.assertEqual(plate.quantity, 10)

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

    def test_execution_policy_store_isolates_probe_policies(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ExecutionPolicyStore(Path(temporary) / "execution.json")
            first = ExecutionPolicy(
                mode=ExecutionMode.AUTOMATIC,
                live_execution_enabled=True,
                allowed_command_types=frozenset({CommandType.MANNY_MINE}),
                max_commands_per_cycle=2,
            )
            second = ExecutionPolicy(
                mode=ExecutionMode.APPROVE,
                allowed_command_types=frozenset({CommandType.MOVE_PROBE}),
            )

            store.save(first, probe_id=11)
            store.save(second, probe_id=12)

            self.assertEqual(store.load(11), first)
            self.assertEqual(store.load(12), second)
            self.assertEqual(store.load(13), ExecutionPolicy())

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
