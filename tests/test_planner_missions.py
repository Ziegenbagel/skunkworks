import unittest
from types import SimpleNamespace

from src.models.galaxy import SectorCoordinates
from src.operations.operations import Operations
from src.planner.desired_state import (
    DesiredState,
    FuelGoal,
    InventoryGoal,
    ProductionGoal,
    ResourceGoal,
    TravelGoal,
)
from src.planner.planner import Planner
from src.recipes.manager import RecipeManager


RECIPES = {
    "recipes": [
        {
            "id": "storage_container",
            "name": "Storage container",
            "craftableBy": ["manny"],
            "durationSeconds": 60,
            "ingredients": [
                {
                    "type": "metals",
                    "quantity": 1,
                    "kind": "resource",
                }
            ],
            "output": {
                "type": "storage_container",
                "containerSpace": 0.1,
            },
        },
        {
            "id": "manny",
            "name": "Manny",
            "craftableBy": ["manny"],
            "durationSeconds": 60,
            "ingredients": [
                {
                    "type": "deuterium",
                    "quantity": 2,
                    "kind": "resource",
                }
            ],
            "output": {
                "type": "manny",
                "containerSpace": 0.1,
            },
        }
    ]
}


def build_operations(
    *,
    metals=2,
    fuel=50,
    free_capacity=5,
    status="idle",
):
    recipes = RecipeManager()
    recipes.load(RECIPES)
    world = SimpleNamespace(
        snapshot={
            "probe": "Test Probe",
            "age": "now",
            "age_seconds": 0,
            "fresh": True,
        },
        probe={
            "id": 1,
            "status": status,
            "telemetry_available": True,
            "sector": {
                "relative": {"x": 0, "y": 0, "z": 0},
            },
            "fuel": {
                "deuterium": fuel,
                "maxDeuterium": 100,
            },
            "inventory": {
                "capacity": 10,
                "usedCapacity": 10 - free_capacity,
                "freeCapacity": free_capacity,
                "items": [],
                "resourceStocks": [
                    {"type": "metals", "amount": metals},
                ],
            },
        },
        sector={
            "resources": [
                {
                    "id": "asteroid-1",
                    "classification": "persistent",
                    "resources": {
                        "metals": 20,
                        "deuterium": 10,
                    },
                    "composition": {
                        "metals": 0.8,
                        "deuterium": 0.2,
                    },
                }
            ]
        },
        mannies={
            "mannies": [
                {
                    "id": 101,
                    "currentTask": None,
                    "canReceiveOrders": True,
                    "location": {"type": "probe"},
                }
            ]
        },
        galaxy=None,
    )
    return Operations(world, recipes)


class PlannerMissionTests(unittest.TestCase):
    def test_mission_11_recommends_achievable_craft(self):
        tasks = Planner(
            build_operations(),
            DesiredState(
                production=(
                    ProductionGoal("storage_container", 1),
                )
            ),
        ).tasks()

        craft = next(
            task for task in tasks
            if task.category == "manufacturing"
        )
        self.assertEqual(craft.action, "Craft Item")
        self.assertEqual(craft.constraints, ())

    def test_mission_11_shortage_unlocks_mining(self):
        tasks = Planner(
            build_operations(metals=0),
            DesiredState(
                production=(
                    ProductionGoal("storage_container", 1),
                )
            ),
        ).tasks()

        self.assertTrue(
            any(
                task.action == "Prepare Manufacturing"
                for task in tasks
            )
        )
        mining = next(
            task for task in tasks
            if task.category == "mining"
        )
        self.assertEqual(mining.action, "Mine Resource")
        self.assertEqual(mining.target, "asteroid-1")
        self.assertIn("next production unit: storage container", mining.reason)

    def test_large_goal_mines_for_next_unit_by_default(self):
        tasks = Planner(
            build_operations(metals=0),
            DesiredState(
                production=(
                    ProductionGoal("storage_container", 100),
                )
            ),
        ).tasks()

        mining = next(task for task in tasks if task.category == "mining")
        self.assertEqual(mining.quantity, 1)
        self.assertIn("Need 1.000 additional metals", mining.reason)
        self.assertIn("next production unit: storage container", mining.reason)

    def test_idle_lookahead_funds_remaining_batch_with_storage_cap(self):
        tasks = Planner(
            build_operations(metals=0),
            DesiredState(production=(ProductionGoal("storage_container", 100),)),
            dependency_mining_lookahead=True,
        ).tasks()

        mining = next(task for task in tasks if task.category == "mining")
        self.assertEqual(mining.quantity, 4.95)
        self.assertIn("Need 100.000 additional metals", mining.reason)
        self.assertIn("remaining production target: storage container", mining.reason)

    def test_idle_lookahead_does_not_mine_when_next_unit_is_craftable(self):
        tasks = Planner(
            build_operations(metals=1),
            DesiredState(production=(ProductionGoal("storage_container", 100),)),
            dependency_mining_lookahead=True,
        ).tasks()

        self.assertTrue(any(
            task.category == "manufacturing" and task.action == "Craft Item"
            for task in tasks
        ))
        self.assertFalse(any(
            task.category == "mining"
            and "production target" in task.reason
            for task in tasks
        ))

    def test_dependency_mining_does_not_inherit_lower_reserve_quantity(self):
        tasks = Planner(
            build_operations(metals=0),
            DesiredState(
                production=(
                    ProductionGoal("storage_container", 100, priority=1),
                ),
                resources=(ResourceGoal("metals", 50, priority=3),),
            ),
        ).tasks()

        mining = next(task for task in tasks if task.category == "mining")
        self.assertEqual(mining.priority, 1)
        self.assertEqual(mining.quantity, 1)
        self.assertIn("Need 1.000 additional metals", mining.reason)
        self.assertIn("next production unit: storage container", mining.reason)
        self.assertNotIn("50 metals reserve target", mining.reason)

    def test_unavailable_top_dependency_does_not_hide_next_craftable_goal(self):
        operations = build_operations(metals=1, fuel=0)
        operations.world.sector["resources"][0]["resources"].pop("deuterium")
        operations.world.sector["resources"][0]["composition"].pop("deuterium")
        tasks = Planner(
            operations,
            DesiredState(production=(
                ProductionGoal("manny", 2, priority=1),
                ProductionGoal("storage_container", 1, priority=2),
            )),
        ).tasks()

        unavailable = next(
            task for task in tasks
            if task.category == "mining" and task.resource_type == "deuterium"
        )
        fallback = next(
            task for task in tasks
            if task.category == "manufacturing"
            and task.target == "storage_container"
        )
        self.assertIn("resource_not_in_current_sector", unavailable.constraints)
        self.assertEqual(fallback.action, "Craft Item")
        self.assertEqual(fallback.constraints, ())

    def test_mission_12_plans_resource_and_fuel_reserves(self):
        tasks = Planner(
            build_operations(metals=1, fuel=10),
            DesiredState(
                resources=(ResourceGoal("metals", 4),),
                fuel=FuelGoal(20),
            ),
        ).tasks()

        categories = {task.category for task in tasks}
        self.assertIn("mining", categories)
        self.assertIn("fuel", categories)

    def test_equal_priority_mining_balances_against_active_commitments(self):
        operations = build_operations(metals=0)
        operations.world.sector["resources"].extend([
            {
                "id": "carbon-rock", "classification": "persistent",
                "resources": {"carbon_compounds": 100},
                "composition": {"carbon_compounds": 1},
            },
            {
                "id": "ice-rock", "classification": "persistent",
                "resources": {"ice": 100}, "composition": {"ice": 1},
            },
        ])
        operations.world.mannies["mannies"].append({
            "id": 102, "currentTask": "mining", "canReceiveOrders": False,
            "location": {"type": "sector"},
            "task": {
                "resourceType": "carbon_compounds",
                "targetAmount": 0.55,
                "depositedAmount": 0,
            },
        })
        tasks = Planner(
            operations,
            DesiredState(resources=(
                ResourceGoal("carbon_compounds", 10, priority=2),
                ResourceGoal("ice", 10, priority=2),
            )),
        ).tasks()
        mining = [task for task in tasks if task.category == "mining"]

        self.assertEqual(mining[0].resource_type, "ice")
        carbon = next(task for task in mining if task.resource_type == "carbon_compounds")
        self.assertIn("0.550 is already committed", carbon.reason)
        self.assertEqual(carbon.quantity, 4.4)

    def test_blocked_manufacturing_explains_inbound_resource_coverage(self):
        operations = build_operations(metals=0)
        operations.world.mannies["mannies"][0].update({
            "currentTask": "mining",
            "canReceiveOrders": False,
            "task": {
                "resourceType": "metals",
                "targetAmount": 0.75,
                "depositedAmount": 0,
            },
        })
        task = next(task for task in Planner(
            operations,
            DesiredState(production=(ProductionGoal("storage_container", 1),)),
        ).tasks() if task.category == "manufacturing")

        self.assertIn("metals: 1.0000 ECE required", task.reason)
        self.assertIn("0.0000 onboard, 0.7500 inbound", task.reason)
        self.assertIn("0.2500 still uncovered", task.reason)

    def test_deuterium_active_commitment_converts_api_fraction_to_tank_ece(self):
        operations = build_operations()
        operations.world.mannies["mannies"][0].update({
            "currentTask": "mining",
            "canReceiveOrders": False,
            "task": {
                "resourceType": "deuterium",
                "targetAmount": 0.22,
                "depositedAmount": 0,
            },
        })

        self.assertEqual(
            operations.mining.active_commitments()["deuterium"], 22,
        )

    def test_manufacturing_deuterium_shortage_uses_tank_units_for_mining(self):
        operations = build_operations()
        operations.world.probe["fuel"].update({
            "deuterium": 20, "maxDeuterium": 100,
        })
        tasks = Planner(
            operations,
            DesiredState(production=(ProductionGoal("manny", 2),)),
        ).tasks()
        craft = next(task for task in tasks if task.category == "manufacturing")
        task = next(task for task in tasks
                    if task.category == "mining" and task.resource_type == "deuterium")

        self.assertIn("2.0000 ECE required, 0.2000 onboard", craft.reason)
        self.assertIn("1.8000 still uncovered", craft.reason)
        self.assertIn("Need 1.800 ECE additional deuterium", task.reason)
        self.assertIn("0.000 ECE is already committed", task.reason)
        self.assertGreater(task.quantity, 0)
        self.assertIn("next production unit: manny", task.reason)

    def test_mining_order_uses_probe_specific_maximum(self):
        operations = build_operations(metals=0)
        tasks = Planner(
            operations,
            DesiredState(
                resources=(ResourceGoal("metals", 4, priority=2),),
                maximum_mining_order_amount=0.25,
            ),
        ).tasks()

        mining = next(task for task in tasks if task.category == "mining")
        self.assertEqual(mining.quantity, 4)
        self.assertEqual(mining.maximum_order_amount, 0.25)

        from src.execution.translator import TaskCommandTranslator
        command = TaskCommandTranslator(operations, 1).translate(mining)
        self.assertEqual(command.payload["targetAmount"], 0.25)
        self.assertEqual(command.metadata["remainingAmount"], 3.75)

    def test_deuterium_order_converts_probe_maximum_to_25_ece_cap(self):
        operations = build_operations()
        operations.world.probe["fuel"].update({
            "deuterium": 20, "maxDeuterium": 100,
        })
        operations.world.sector["resources"][0]["resources"]["deuterium"] = 4.42
        task = next(task for task in Planner(
            operations,
            DesiredState(
                production=(ProductionGoal("manny", 100),),
                maximum_mining_order_amount=0.25,
            ),
            dependency_mining_lookahead=True,
        ).tasks() if task.category == "mining" and task.resource_type == "deuterium")

        from src.execution.translator import TaskCommandTranslator
        command = TaskCommandTranslator(operations, 1).translate(task)

        self.assertEqual(command.payload["targetAmount"], 0.25)
        self.assertEqual(command.metadata["orderAmount"], 25.0)
        self.assertEqual(
            operations.mining.best_target("deuterium")["available_amount"],
            442.0,
        )

    def test_mining_deficit_uses_full_per_order_cap_before_final_remainder(self):
        operations = build_operations(metals=0)
        operations.world.mannies["mannies"].extend([
            {
                "id": manny_id, "currentTask": None, "canReceiveOrders": True,
                "location": {"type": "probe"},
            }
            for manny_id in (102, 103, 104)
        ])
        task = next(task for task in Planner(
            operations,
            DesiredState(
                resources=(ResourceGoal("metals", 0.88, priority=2),),
                maximum_mining_order_amount=0.25,
            ),
        ).tasks() if task.category == "mining")

        from src.execution.translator import TaskCommandTranslator
        command = TaskCommandTranslator(operations, 1).translate(task)

        self.assertEqual(command.payload["targetAmount"], 0.25)
        self.assertEqual(command.metadata["plannedMiningWorkers"], 4)

    def test_small_mining_deficit_uses_one_manny(self):
        operations = build_operations(metals=0)
        operations.world.mannies["mannies"].extend([
            {
                "id": manny_id, "currentTask": None, "canReceiveOrders": True,
                "location": {"type": "probe"},
            }
            for manny_id in (102, 103, 104)
        ])
        task = next(task for task in Planner(
            operations,
            DesiredState(
                resources=(ResourceGoal("metals", 0.20, priority=2),),
                maximum_mining_order_amount=0.25,
            ),
        ).tasks() if task.category == "mining")

        from src.execution.translator import TaskCommandTranslator
        command = TaskCommandTranslator(operations, 1).translate(task)

        self.assertEqual(command.payload["targetAmount"], 0.20)
        self.assertEqual(command.metadata["plannedMiningWorkers"], 1)

    def test_mining_preserves_return_berth_and_inbound_cargo_capacity(self):
        operations = build_operations(metals=0, free_capacity=0.24)
        operations.world.mannies["mannies"].append({
            "id": 102,
            "currentTask": "mining",
            "task": {
                "resourceType": "metals",
                "targetAmount": 0.20,
                "depositedAmount": 0,
            },
            "canReceiveOrders": False,
        })

        tasks = Planner(
            operations,
            DesiredState(resources=(ResourceGoal("metals", 1, priority=2),)),
        ).tasks()
        mining = next(task for task in tasks if task.category == "mining")

        self.assertIn("insufficient_probe_storage", mining.constraints)
        self.assertEqual(mining.quantity, 0)

    def test_fuel_refill_uses_exact_uncovered_deficit_and_probe_maximum(self):
        operations = build_operations(fuel=78)
        operations.world.probe["fuel"]["maxDeuterium"] = 400
        operations.world.probe["fuel"]["deuterium"] = 312
        tasks = Planner(
            operations,
            DesiredState(
                fuel=FuelGoal(78.22),
                maximum_mining_order_amount=0.25,
            ),
        ).tasks()

        fuel_task = next(task for task in tasks if task.category == "fuel")
        self.assertAlmostEqual(fuel_task.quantity, 0.88)
        self.assertEqual(fuel_task.maximum_order_amount, 0.25)
        from src.execution.translator import TaskCommandTranslator
        command = TaskCommandTranslator(operations, 1).translate(fuel_task)
        self.assertEqual(command.payload["targetAmount"], 0.0088)
        self.assertEqual(command.metadata["apiUnitScale"], 100)

    def test_large_deuterium_deficit_is_split_in_tank_units(self):
        operations = build_operations(fuel=94.5)
        operations.world.probe["fuel"] = {
            "deuterium": 378, "maxDeuterium": 400,
        }
        operations.world.sector["resources"][0]["resources"]["deuterium"] = 100
        operations.world.mannies["mannies"].extend([
            {
                "id": manny_id, "currentTask": None,
                "canReceiveOrders": True, "location": {"type": "probe"},
            }
            for manny_id in (102, 103, 104)
        ])
        task = next(task for task in Planner(
            operations,
            DesiredState(
                fuel=FuelGoal(100), maximum_mining_order_amount=0.25,
            ),
        ).tasks() if task.category == "fuel")

        from src.execution.translator import TaskCommandTranslator
        command = TaskCommandTranslator(operations, 1).translate(task)

        self.assertEqual(task.quantity, 22)
        self.assertEqual(command.payload["targetAmount"], 0.22)
        self.assertEqual(command.metadata["plannedMiningWorkers"], 1)

    def test_mission_13_plans_capacity_and_travel(self):
        operations = build_operations(free_capacity=0.5)
        target = SectorCoordinates(2, 0, 0)
        tasks = Planner(
            operations,
            DesiredState(
                inventory=InventoryGoal(1),
                travel=TravelGoal(target),
            ),
        ).tasks()

        categories = {task.category for task in tasks}
        self.assertIn("inventory", categories)
        self.assertIn("travel", categories)
        self.assertEqual(
            operations.travel.route_to(target)[-1],
            target,
        )
        self.assertEqual(
            len(operations.travel.route_to(target)),
            2,
        )

    def test_no_goal_differences_falls_back_to_idle(self):
        tasks = Planner(
            build_operations(),
            DesiredState(
                fuel=FuelGoal(0),
                inventory=InventoryGoal(0),
            ),
        ).tasks()

        self.assertEqual(
            [task.action for task in tasks],
            ["Assess Current Probe"],
        )


if __name__ == "__main__":
    unittest.main()
