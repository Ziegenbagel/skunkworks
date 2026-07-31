import unittest

from src.planner.desired_state import (
    DesiredState,
    ProductionGoal,
)
from src.planner.planner import Planner


class DesiredStateTests(unittest.TestCase):
    def test_planner_defaults_to_empty_desired_state(self):
        planner = Planner(operations=object())

        self.assertEqual(
            planner.desired_state,
            DesiredState.empty(),
        )

    def test_production_goal_is_declarative(self):
        state = DesiredState(
            production=(
                ProductionGoal(
                    recipe_id="manny",
                    quantity=6,
                ),
            )
        )

        self.assertEqual(
            state.production[0].recipe_id,
            "manny",
        )

    def test_negative_goal_is_invalid(self):
        with self.assertRaises(ValueError):
            ProductionGoal(
                recipe_id="manny",
                quantity=-1,
            )


if __name__ == "__main__":
    unittest.main()
