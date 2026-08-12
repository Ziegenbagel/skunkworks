import tempfile
import unittest
from pathlib import Path

from src.data import DataEngine
from src.operations import (
    CargoLogisticsService,
    FleetRoleService,
    OperationFactory,
    OperationState,
    OperationStore,
    TankerLogisticsService,
)
from tests.test_planner_missions import build_operations


class OperationsLogisticsDepotTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.engine = DataEngine(Path(self.temporary.name) / "ops.sqlite3")

    def tearDown(self):
        self.temporary.cleanup()

    def test_operation_templates_persist_and_resume(self):
        operation = OperationFactory.create("fuel_recovery", probe_id=1).activate()
        store = OperationStore(self.engine)
        store.save(operation)

        restored = store.all(OperationState.ACTIVE)

        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0], operation)
        self.assertEqual(restored[0].current.action, "select_deuterium_source")

    def test_fleet_role_assignment_is_single_and_durable(self):
        roles = FleetRoleService(self.engine)
        roles.assign("probe", 8, "explorer")
        roles.assign("probe", 8, "deuterium_tanker", metadata={"reserve": 80})

        records = roles.all("probe")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["role"], "deuterium_tanker")

    def test_tanker_delivery_preserves_return_reserve(self):
        tanker = {
            "id": 8, "model": "deuterium_tanker", "status": "idle",
            "sector": {"relative": {"x": 0, "y": 0, "z": 0}},
            "fuel": {"deuterium": 500, "maxDeuterium": 800},
        }
        target = {
            "id": 9, "status": "idle",
            "sector": {"relative": {"x": 0, "y": 0, "z": 0}},
            "fuel": {"deuterium": 10, "maxDeuterium": 100},
        }

        plan = TankerLogisticsService().plan_delivery(tanker, target, 150, 100)

        self.assertEqual(plan.deliverable_amount, 90)
        self.assertEqual(plan.blockers, ())

    def test_reserve_tanker_can_refill_probe_in_arrived_stationary_state(self):
        sector = {"relative": {"x": 0, "y": 0, "z": 0}}
        tanker = {
            "id": 8, "model": "deuterium_tanker", "status": "idle",
            "sector": sector,
            "fuel": {"deuterium": 350, "maxDeuterium": 400},
        }
        target = {
            "id": 9, "status": "arrived", "sector": sector,
            "fuel": {"deuterium": 35, "maxDeuterium": 100},
        }

        plan = TankerLogisticsService().plan_delivery(tanker, target, 65, 100)

        self.assertEqual(plan.deliverable_amount, 65)
        self.assertEqual(plan.blockers, ())

    def test_arriving_tanker_fills_reserve_tanker_before_hub(self):
        sector = {"relative": {"x": 0, "y": 0, "z": 0}}
        arriving = {
            "id": 8, "model": "deuterium_tanker", "status": "idle",
            "sector": sector,
            "fuel": {"deuterium": 500, "maxDeuterium": 800},
        }
        reserve = {
            "id": 9, "model": "deuterium_tanker", "status": "idle",
            "sector": sector,
            "fuel": {"deuterium": 300, "maxDeuterium": 400},
        }
        hub = {
            "id": 10, "model": "generic", "status": "idle",
            "sector": sector,
            "fuel": {"deuterium": 20, "maxDeuterium": 100},
        }

        sequence = TankerLogisticsService().plan_delivery_sequence(
            arriving, (reserve, hub), requested_amount=180,
            return_reserve=100,
            roles={9: "deuterium_reserve", 10: "hub"},
            hub_probe_id=10,
        )

        self.assertEqual(
            [(leg.target_probe_id, leg.target_kind, leg.amount) for leg in sequence.legs],
            [(9, "reserve_tanker", 100), (10, "hub_probe", 80)],
        )
        self.assertEqual(sequence.undelivered_amount, 0)
        self.assertEqual(sequence.blockers, ())

    def test_tanker_sequence_never_spends_return_reserve(self):
        sector = {"relative": {"x": 0, "y": 0, "z": 0}}
        arriving = {
            "id": 8, "model": "deuterium_tanker", "status": "idle",
            "sector": sector,
            "fuel": {"deuterium": 130, "maxDeuterium": 400},
        }
        reserve = {
            "id": 9, "model": "deuterium_tanker", "status": "idle",
            "sector": sector,
            "fuel": {"deuterium": 0, "maxDeuterium": 400},
        }

        sequence = TankerLogisticsService().plan_delivery_sequence(
            arriving, (reserve,), requested_amount=200, return_reserve=100,
        )

        self.assertEqual(sequence.legs[0].amount, 30)
        self.assertEqual(sequence.undelivered_amount, 170)

    def test_reserve_role_tanker_is_a_protected_deuterium_source(self):
        roles = FleetRoleService(self.engine)
        roles.assign(
            "probe", 9, "deuterium_reserve",
            metadata={"protectedDeuterium": 100},
        )
        sources = roles.deuterium_sources(({
            "id": 9, "name": "Reserve One", "model": "deuterium_tanker",
            "isReachable": True,
            "sector": {"relative": {"x": 1, "y": 2, "z": 3}},
            "fuel": {"deuterium": 350, "maxDeuterium": 800},
        },))

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["availableAmount"], 250)
        self.assertEqual(sources[0]["coordinates"], {"x": 1, "y": 2, "z": 3})

    def test_cargo_delivery_reports_capacity_and_trip_count(self):
        plan = CargoLogisticsService().plan_delivery(
            "metals", 12, source_available=20,
            carrier_capacity=5, target_free_capacity=20,
        )

        self.assertEqual(plan.deliverable_amount, 5)
        self.assertEqual(plan.remaining_amount, 7)
        self.assertEqual(plan.trips_required, 3)

    def test_manny_container_and_depot_views_use_real_entities(self):
        operations = build_operations()
        operations.world.mannies["mannies"][0].update(
            {
                "currentTask": {"type": "mining", "objectId": "asteroid-1"},
                "taskProgressPercent": 40,
                "location": {"type": "asteroid", "objectId": "asteroid-1"},
            }
        )
        operations.world.sector["snapshot"] = {
            "sector": {
                "objects": [
                    {
                        "id": "container-1", "type": "detached_container",
                        "asteroidId": "asteroid-1", "capacity": 10,
                        "usedCapacity": 9,
                    }
                ]
            }
        }

        depot = operations.depots.all()[0]

        self.assertEqual(operations.mannies.progress(), {101: 40})
        self.assertEqual(len(operations.containers.detached()), 1)
        self.assertEqual(depot.status, "operational")
        self.assertEqual(depot.storage_fill_percent, 90)
        self.assertTrue(depot.needs_transport)


if __name__ == "__main__":
    unittest.main()
