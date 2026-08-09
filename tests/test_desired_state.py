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
    RepairGoal,
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

    def test_repair_goal_round_trips_and_plans_only_below_trigger(self):
        state = DesiredState.from_dict({
            "repairTriggerPercent": 70,
            "repairTargetPercent": 95,
            "repairPriority": 2,
            "priorityScaleMax": 10,
        })
        self.assertEqual(state.repair, RepairGoal(70, 95, 2))
        self.assertEqual(state.to_dict()["repairTargetPercent"], 95)

        operations = build_operations()
        operations.world.probe["systems"] = {"integrityPercent": 65}
        repair = next(
            task for task in Planner(operations, state).tasks()
            if task.action == "Repair Probe"
        )
        self.assertEqual(repair.quantity, 30)
        self.assertEqual(repair.priority, 2)

    def test_auto_travel_waits_for_repair_completion_and_manny_return(self):
        state = DesiredState(
            repair=RepairGoal(70, 95, 2),
            travel=TravelGoal(SectorCoordinates(1, 1, 0)),
        )
        operations = build_operations()
        operations.world.probe["systems"] = {"integrityPercent": 65}

        travel = next(task for task in Planner(operations, state).tasks() if task.category == "travel")
        self.assertIn("repair_required_before_travel", travel.constraints)

        operations.world.probe["systems"]["integrityPercent"] = 80
        operations.world.mannies["mannies"][0]["currentTask"] = {"type": "repairing"}
        travel = next(task for task in Planner(operations, state).tasks() if task.category == "travel")
        self.assertIn("repair_required_before_travel", travel.constraints)
        self.assertIn("manny_tasks_in_progress", travel.constraints)

        operations.world.probe["systems"]["integrityPercent"] = 95
        operations.world.mannies["mannies"][0]["currentTask"] = None
        operations.world.mannies["mannies"][0]["location"] = {"type": "sector"}
        travel = next(task for task in Planner(operations, state).tasks() if task.category == "travel")
        self.assertIn("mannies_not_aboard", travel.constraints)

        operations.world.mannies["mannies"][0]["location"] = {"type": "probe"}
        travel = next(task for task in Planner(operations, state).tasks() if task.category == "travel")
        self.assertEqual(travel.action, "Move Probe")
        self.assertEqual(travel.constraints, ())

    def test_negative_goal_is_invalid(self):
        with self.assertRaises(ValueError):
            ProductionGoal(
                recipe_id="manny",
                quantity=-1,
            )

    def test_priority_must_be_positive(self):
        with self.assertRaises(ValueError):
            FleetGoal("deuterium_tanker", 1, priority=0)
        with self.assertRaises(ValueError):
            ProductionGoal("manny", 1, priority=11)

    def test_legacy_priority_values_migrate_to_ten_point_scale(self):
        state = DesiredState.from_dict({
            "production": [{"recipeId": "manny", "quantity": 1, "priority": 50}],
            "fuelPriority": 30,
            "fleetTargets": {"deuterium_tanker": 1},
            "fleetPriorities": {"deuterium_tanker": 10},
        })

        self.assertEqual(state.production[0].priority, 5)
        self.assertEqual(state.fuel.priority, 3)
        self.assertEqual(state.fleet[0].priority, 1)

    def test_tanker_target_enters_planner_at_selected_priority(self):
        operations = build_operations()
        operations.world.fleet = {"probes": [{"model": "generic"}]}

        tasks = Planner(
            operations,
            DesiredState(fleet=(FleetGoal("deuterium_tanker", 1, priority=4),)),
        ).tasks()

        tanker = next(task for task in tasks if task.category == "fleet_assembly")
        self.assertEqual(tanker.action, "Prepare Manufacturing")
        self.assertEqual(tanker.target, "deuterium_engine")
        self.assertIn("tanker goal", tanker.reason)
        self.assertEqual(tanker.priority, 4)

    def test_round_trips_all_goal_types(self):
        state = DesiredState(
            production=(ProductionGoal("manny", 6, priority=2),),
            resources=(ResourceGoal("metals", 4.5, priority=4),),
            fuel=FuelGoal(35, priority=8),
            inventory=InventoryGoal(2, priority=6),
            maximum_mining_order_amount=0.25,
            travel=TravelGoal(SectorCoordinates(2, 0, 0)),
            fleet=(FleetGoal("deuterium_tanker", 2, priority=1),),
        )

        self.assertEqual(
            DesiredState.from_dict(state.to_dict()),
            state,
        )

    def test_mining_order_amount_requires_game_increment(self):
        self.assertEqual(
            DesiredState.from_dict({"maximumMiningOrderAmount": 0.25}).maximum_mining_order_amount,
            0.25,
        )
        with self.assertRaises(ValueError):
            DesiredState(maximum_mining_order_amount=0.26)

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

    def test_store_keeps_probe_desired_states_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = DesiredStateStore(
                DataEngine(Path(directory) / "data.sqlite3"),
            )
            probe_one = DesiredState(fuel=FuelGoal(30))
            probe_two = DesiredState(fuel=FuelGoal(70))

            store.save(probe_one, 1)
            store.save(probe_two, 2)

            self.assertEqual(store.load(1), probe_one)
            self.assertEqual(store.load(2), probe_two)


if __name__ == "__main__":
    unittest.main()
