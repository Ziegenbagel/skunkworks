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
