import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.data import DataEngine
from src.models.galaxy import SectorCoordinates
from src.safety.resources import (
    ResourceSafetyPolicy,
    ResourceSustainabilityService,
)
from src.planner.desired_state import (
    DesiredState,
    FuelGoal,
    InventoryGoal,
)
from src.planner.planner import Planner
from tests.test_planner_missions import build_operations


def record_source(
    engine,
    *,
    coordinates,
    object_id,
    amount,
    observed_at,
):
    world = SimpleNamespace(
        probe={
            "id": 1,
            "name": "Probe",
            "model": "generic",
            "status": "idle",
            "sector": {
                "relative": {
                    "x": coordinates.x,
                    "y": coordinates.y,
                    "z": coordinates.z,
                }
            },
        },
        sector={
            "snapshot": {
                "sector": {
                    "relativeCoordinates": {
                        "x": coordinates.x,
                        "y": coordinates.y,
                        "z": coordinates.z,
                    }
                }
            },
            "resources": [
                {
                    "id": object_id,
                    "classification": "dynamic",
                    "resources": {"metals": amount},
                    "composition": {"metals": 1},
                }
            ],
        },
    )
    engine.record_world(world, observed_at=observed_at)


class ResourceSustainabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.engine = DataEngine(
            Path(self.temporary.name) / "resources.sqlite3"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_warns_when_asteroid_falls_below_history(self):
        origin = SectorCoordinates(0, 0, 0)
        record_source(
            self.engine,
            coordinates=origin,
            object_id="asteroid-1",
            amount=10,
            observed_at="first",
        )
        operations = build_operations(metals=2)
        operations.world.sector["resources"][0][
            "resources"
        ]["metals"] = 2
        service = ResourceSustainabilityService(
            operations.world,
            self.engine,
            ResourceSafetyPolicy(),
        )
        warning = next(
            warning
            for warning in service.report().warnings
            if warning.code == "asteroid_resource_low"
        )

        self.assertEqual(warning.remaining_percent, 20)
        self.assertEqual(warning.severity, "warning")

    def test_finds_replacement_and_builds_logistics_roles(self):
        origin = SectorCoordinates(0, 0, 0)
        replacement = SectorCoordinates(2, 0, 0)
        record_source(
            self.engine,
            coordinates=origin,
            object_id="asteroid-1",
            amount=10,
            observed_at="first",
        )
        record_source(
            self.engine,
            coordinates=replacement,
            object_id="asteroid-2",
            amount=20,
            observed_at="second",
        )
        operations = build_operations(metals=0.2)
        operations.world.sector["resources"][0][
            "resources"
        ]["metals"] = 0.2
        service = ResourceSustainabilityService(
            operations.world,
            self.engine,
            ResourceSafetyPolicy(),
        )
        report = service.report()

        self.assertEqual(
            report.replacements[0].coordinates,
            replacement,
        )
        self.assertEqual(
            {
                role.role
                for role in report.logistics_plans[0].roles
            },
            {"hub", "miner", "transport"},
        )

    def test_wandering_field_is_reported_as_finite(self):
        operations = build_operations()
        operations.world.sector["snapshot"] = {
            "sector": {
                "objects": [
                    {"mannyMineable": True}
                    for _ in range(5)
                ]
            }
        }
        report = ResourceSustainabilityService(
            operations.world,
            self.engine,
            ResourceSafetyPolicy(),
        ).report()

        self.assertEqual(report.wandering_asteroid_count, 5)
        self.assertEqual(
            report.wandering_generation_maximum,
            5,
        )
        self.assertFalse(report.replenishment_observed)
        self.assertTrue(
            any(
                warning.code
                == "finite_wandering_asteroid_field"
                for warning in report.warnings
            )
        )

    def test_never_present_zero_resource_is_not_depleted(self):
        operations = build_operations()
        operations.world.sector["resources"][0][
            "resources"
        ]["ice"] = 0
        report = ResourceSustainabilityService(
            operations.world,
            self.engine,
            ResourceSafetyPolicy(),
        ).report()

        self.assertFalse(
            any(
                warning.resource_type == "ice"
                for warning in report.warnings
            )
        )

    def test_latest_source_excludes_depleted_deposit(self):
        coordinates = SectorCoordinates(2, 0, 0)
        record_source(
            self.engine,
            coordinates=coordinates,
            object_id="asteroid-2",
            amount=5,
            observed_at="first",
        )
        record_source(
            self.engine,
            coordinates=coordinates,
            object_id="asteroid-2",
            amount=0,
            observed_at="second",
        )

        self.assertEqual(
            self.engine.latest_resource_sources(
                "metals",
                minimum_amount=1,
            ),
            [],
        )

    def test_planner_recommends_replacement_and_logistics(self):
        origin = SectorCoordinates(0, 0, 0)
        replacement = SectorCoordinates(2, 0, 0)
        record_source(
            self.engine,
            coordinates=origin,
            object_id="asteroid-1",
            amount=10,
            observed_at="first",
        )
        record_source(
            self.engine,
            coordinates=replacement,
            object_id="asteroid-2",
            amount=20,
            observed_at="second",
        )
        operations = build_operations(metals=0.2)
        operations.world.sector["resources"][0][
            "resources"
        ]["metals"] = 0.2
        operations.resource_sustainability = (
            ResourceSustainabilityService(
                operations.world,
                self.engine,
                ResourceSafetyPolicy(),
            )
        )
        tasks = Planner(
            operations,
            DesiredState(
                fuel=FuelGoal(0),
                inventory=InventoryGoal(0),
            ),
        ).tasks()
        actions = {task.action for task in tasks}

        self.assertIn(
            "Prepare Replacement Resource Source",
            actions,
        )
        self.assertIn("Stage Resource Logistics", actions)


if __name__ == "__main__":
    unittest.main()
