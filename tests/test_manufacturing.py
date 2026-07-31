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
            "ingredients": [
                {
                    "type": "metals",
                    "quantity": 0.2,
                    "kind": "resource",
                },
            ],
        },
        {
            "id": "electric_motor",
            "name": "Electric motor",
            "craftableBy": ["manny"],
            "ingredients": [
                {
                    "type": "steel_bar",
                    "quantity": 2,
                    "kind": "item",
                },
                {
                    "type": "carbon_compounds",
                    "quantity": 0.1,
                    "kind": "resource",
                },
            ],
        },
    ],
}


class ManufacturingServiceTests(unittest.TestCase):
    def setUp(self):
        recipes = RecipeManager()
        recipes.load(RECIPES)
        world = SimpleNamespace(
            probe={
                "inventory": {
                    "items": [{"type": "steel_bar"}],
                    "resourceStocks": [
                        {"type": "metals", "amount": 1.0},
                        {
                            "type": "carbon_compounds",
                            "amount": 0.05,
                        },
                    ],
                },
            },
        )
        self.service = ManufacturingService(world, recipes)

    def test_reports_direct_missing_ingredients(self):
        self.assertEqual(
            self.service.missing_ingredients("electric_motor"),
            {
                "resources": {"carbon_compounds": 0.05},
                "items": {"steel_bar": 1},
            },
        )
        self.assertFalse(
            self.service.can_build("electric_motor")
        )

    def test_expands_recursive_raw_resources(self):
        self.assertEqual(
            self.service.raw_resources("electric_motor"),
            {
                "metals": 0.4,
                "carbon_compounds": 0.1,
            },
        )

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

    def test_plans_missing_components_in_dependency_order(self):
        plan = self.service.production_plan(
            "electric_motor"
        )

        self.assertEqual(
            [
                (step["recipe_id"], step["quantity"])
                for step in plan["steps"]
            ],
            [
                ("steel_bar", 1),
                ("electric_motor", 1),
            ],
        )
        self.assertEqual(
            plan["required_resources"],
            {
                "metals": 0.2,
                "carbon_compounds": 0.1,
            },
        )
        self.assertEqual(
            plan["missing_resources"],
            {"carbon_compounds": 0.05},
        )
        self.assertFalse(plan["achievable"])

    def test_plan_rejects_invalid_quantity(self):
        with self.assertRaises(ValueError):
            self.service.production_plan(
                "electric_motor",
                0,
            )

    def test_report_includes_production_plan(self):
        report = self.service.build_report(
            "electric_motor"
        )

        self.assertEqual(
            report["production_plan"]["target"],
            "electric_motor",
        )


if __name__ == "__main__":
    unittest.main()
