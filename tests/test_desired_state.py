import unittest
import tempfile
from pathlib import Path

from src.data import DataEngine
from src.planner.desired_state import (
    DesiredState,
    FuelGoal,
    FleetGoal,
    InventoryGoal,
    ProductionGoal,
    ResourceGoal,
    TravelGoal,
)
from src.planner.desired_state_store import DesiredStateStore
from src.planner.planner import Planner
from src.models.galaxy import SectorCoordinates
from tests.test_planner_missions import build_operations


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

    def test_priority_must_be_positive(self):
        with self.assertRaises(ValueError):
            FleetGoal("deuterium_tanker", 1, priority=0)

    def test_tanker_target_enters_planner_at_selected_priority(self):
        operations = build_operations()
        operations.world.fleet = {"probes": [{"model": "generic"}]}

        tasks = Planner(
            operations,
            DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=4),)),
        ).tasks()

        tanker = next(task for task in tasks if task.target == "deuterium_tanker")
        self.assertEqual(tanker.action, "Prepare Probe Assembly")
        self.assertEqual(tanker.priority, 4)

    def test_round_trips_all_goal_types(self):
        state = DesiredState(
            production=(ProductionGoal("manny", 6, priority=12),),
            resources=(ResourceGoal("metals", 4.5, priority=18),),
            fuel=FuelGoal(35, priority=8),
            inventory=InventoryGoal(2, priority=25),
            travel=TravelGoal(SectorCoordinates(2, 0, 0)),
            fleet=(FleetGoal("deuterium_tanker", 2, priority=1),),
        )

        self.assertEqual(
            DesiredState.from_dict(state.to_dict()),
            state,
        )

    def test_store_loads_config_then_persisted_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "desired_state.json"
            config.write_text(
                '{"minimumFuelPercent": 25}',
                encoding="utf-8",
            )
            store = DesiredStateStore(
                DataEngine(root / "data.sqlite3"),
                config,
            )

            self.assertEqual(
                store.load().fuel.minimum_percent,
                25,
            )

            saved = DesiredState(fuel=FuelGoal(40))
            store.save(saved)
            self.assertEqual(store.load(), saved)


if __name__ == "__main__":
    unittest.main()
