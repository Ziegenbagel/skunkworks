import unittest
from types import SimpleNamespace

from src.operations.manufacturing import ManufacturingService
from src.recipes.manager import RecipeManager


RECIPES = {
    "recipes": [
        {
            "id": "steel_bar",
            "name": "Steel bar",
            "craftableBy": ["manny"],
            "durationSeconds": 300,
            "ingredients": [
                {
                    "type": "metals",
                    "quantity": 0.2,
                    "unit": "earth_container_equivalent",
                    "kind": "resource",
                },
            ],
            "output": {
                "type": "steel_bar",
                "containerSpace": 0.01,
            },
        },
        {
            "id": "electric_motor",
            "name": "Electric motor",
            "craftableBy": ["manny"],
            "durationSeconds": 900,
            "ingredients": [
                {
                    "type": "steel_bar",
                    "quantity": 2,
                    "unit": "item",
                    "kind": "item",
                },
                {
                    "type": "carbon_compounds",
                    "quantity": 0.1,
                    "unit": "earth_container_equivalent",
                    "kind": "resource",
                },
                {
                    "type": "deuterium",
                    "quantity": 0.5,
                    "unit": "earth_container_equivalent",
                    "kind": "resource",
                },
            ],
            "output": {
                "type": "electric_motor",
                "containerSpace": 0.006,
            },
        },
    ],
}


class ManufacturingServiceTests(unittest.TestCase):
    def setUp(self):
        recipes = RecipeManager()
        recipes.load(RECIPES)
        self.world = SimpleNamespace(
            probe={
                "status": "idle",
                "telemetry_available": True,
                "fuel": {
                    "deuterium": 1.0,
                    "maxDeuterium": 100,
                },
                "inventory": {
                    "freeCapacity": 1.0,
                    "items": [
                        {
                            "type": "steel_bar",
                            "containerSpace": 0.01,
                        },
                    ],
                    "resourceStocks": [
                        {"type": "metals", "amount": 1.0},
                        {
                            "type": "carbon_compounds",
                            "amount": 0.05,
                        },
                    ],
                },
            },
            mannies={
                "mannies": [
                    {
                        "currentTask": None,
                        "canReceiveOrders": True,
                        "location": {"type": "probe"},
                    },
                ],
            },
        )
        self.service = ManufacturingService(
            self.world,
            recipes,
        )

    def test_recursively_synthesizes_missing_components(self):
        plan = self.service.production_plan(
            "electric_motor"
        )

        self.assertEqual(
            plan["orders"],
            [
                {
                    "recipe_id": "electric_motor",
                    "quantity": 1,
                    "craftable_by": ("manny",),
                },
            ],
        )
        self.assertEqual(
            plan["synthesized_components"],
            {"steel_bar": 1},
        )
        self.assertEqual(
            plan["consumed_inventory_items"],
            {"steel_bar": 1},
        )
        self.assertEqual(plan["duration_seconds"], 1200)

    def test_reports_only_terminal_shortages(self):
        self.assertEqual(
            self.service.missing_ingredients(
                "electric_motor"
            ),
            {
                "resources": {
                    "carbon_compounds": 0.05,
                },
                "items": {},
            },
        )

    def test_uses_probe_fuel_for_crafting_deuterium(self):
        plan = self.service.production_plan(
            "electric_motor"
        )

        self.assertNotIn(
            "deuterium",
            plan["missing_resources"],
        )

    def test_becomes_achievable_when_resources_exist(self):
        self.world.probe["inventory"][
            "resourceStocks"
        ][1]["amount"] = 0.1

        self.assertTrue(
            self.service.can_build("electric_motor")
        )

    def test_requires_an_available_fabricator(self):
        self.world.mannies["mannies"][0][
            "currentTask"
        ] = "mining"

        plan = self.service.production_plan(
            "electric_motor"
        )

        self.assertIn(
            "fabricator_unavailable",
            plan["blockers"],
        )

    def test_inventory_count_credits_active_crafting_output(self):
        self.world.mannies["mannies"][0].update({
            "currentTask": "crafting",
            "task": {
                "recipe": "steel_bar",
                "recipeName": "Steel bar",
            },
        })

        self.assertEqual(self.service.inventory_count("steel_bar"), 2)
        self.assertEqual(self.service.inventory_count("steel_bar", include_active=False), 1)

    def test_inventory_count_and_dependency_allocation_expand_api_item_stacks(self):
        self.world.probe["inventory"]["items"] = [{
            "id": "plates", "type": "steel_bar", "quantity": 3,
            "containerSpace": 0.03,
        }]

        self.assertEqual(self.service.inventory_count("steel_bar", include_active=False), 3)
        resources, items = self.service.available_inputs()
        self.assertEqual(items["steel_bar"], 3)

    def test_stale_task_detail_does_not_credit_idle_manny_production(self):
        self.world.mannies["mannies"][0].update({
            "currentTask": None,
            "task": {
                "type": "crafting",
                "recipe": "steel_bar",
                "recipeName": "Steel bar",
            },
        })

        self.assertEqual(self.service.active_production_count("steel_bar"), 0)

    def test_stale_task_detail_does_not_credit_mining_manny_production(self):
        self.world.mannies["mannies"][0].update({
            "currentTask": "mining",
            "task": {
                "type": "crafting",
                "recipe": "steel_bar",
                "recipeName": "Steel bar",
            },
        })

        self.assertEqual(self.service.active_production_count("steel_bar"), 0)

    def test_builds_dependency_tree(self):
        tree = self.service.dependency_tree(
            "electric_motor"
        )

        self.assertEqual(
            tree["children"][0]["recipe"]["id"],
            "steel_bar",
        )

    def test_unknown_recipe_is_not_buildable(self):
        self.assertIsNone(
            self.service.missing_ingredients("unknown")
        )
        self.assertFalse(self.service.can_build("unknown"))

    def test_plan_rejects_invalid_quantity(self):
        with self.assertRaises(ValueError):
            self.service.production_plan(
                "electric_motor",
                0,
            )


if __name__ == "__main__":
    unittest.main()
