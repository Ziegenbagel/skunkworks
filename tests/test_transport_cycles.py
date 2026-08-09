import unittest
import tempfile
from pathlib import Path

from src.models.galaxy import SectorCoordinates
from src.operations import (
    RoundTripTransportPlan,
    RoundTripTransportService,
    TransportCycleState,
)


class TransportCycleTests(unittest.TestCase):
    def setUp(self):
        self.plan = RoundTripTransportPlan(
            probe_id=7,
            resource_type="metals",
            source=SectorCoordinates(0, 0, 0),
            destination=SectorCoordinates(2, 0, 0),
            return_point=SectorCoordinates(0, 0, 0),
            load_until_percent=90,
            unload_until_percent=10,
            fuel_per_hop=5,
            protected_deuterium=20,
            reserve_hops=1,
        )
        self.probe = {
            "id": 7,
            "status": "idle",
            "fuel": {"deuterium": 80, "maxDeuterium": 100},
        }

    def test_round_trip_reserves_destination_return_and_contingency_fuel(self):
        self.assertEqual(self.plan.minimum_departure_deuterium, 45)
        self.assertEqual(self.plan.transferable_deuterium(80), 35)

    def test_loading_waits_for_selected_fill_threshold(self):
        assessment = RoundTripTransportService().assess(
            self.plan, self.probe, cargo_amount=8, cargo_capacity=10,
            state=TransportCycleState.LOADING,
        )
        self.assertFalse(assessment.ready)
        self.assertIn("waiting_for_load_threshold", assessment.warnings)

    def test_mine_in_sector_selects_planner_loading_action(self):
        from dataclasses import replace
        from src.operations import OperationFactory
        plan = replace(self.plan, load_source_mode="mine_in_sector")

        self.assertEqual(plan.loading_action, "mine_resource_to_threshold")
        self.assertEqual(plan.to_dict()["loadSourceMode"], "mine_in_sector")
        operation = OperationFactory.create(
            "round_trip_transport",
            probe_id=plan.probe_id,
            metadata={
                "cycle": plan.to_dict(),
                "loadingAction": plan.loading_action,
            },
        )
        self.assertIn(
            "mine_resource_to_threshold",
            tuple(step.action for step in operation.steps),
        )

    def test_unloading_waits_until_selected_remaining_percentage(self):
        service = RoundTripTransportService()
        waiting = service.assess(
            self.plan, self.probe, cargo_amount=2, cargo_capacity=10,
            state=TransportCycleState.UNLOADING,
        )
        ready = service.assess(
            self.plan, self.probe, cargo_amount=1, cargo_capacity=10,
            state=TransportCycleState.UNLOADING,
        )
        self.assertFalse(waiting.ready)
        self.assertTrue(ready.ready)

    def test_cycle_pauses_when_return_reserve_is_not_met(self):
        probe = {**self.probe, "fuel": {"deuterium": 40}}
        assessment = RoundTripTransportService().assess(
            self.plan, probe, cargo_amount=10, cargo_capacity=10,
            state=TransportCycleState.TO_DESTINATION,
        )
        self.assertFalse(assessment.ready)
        self.assertIn("return_deuterium_reserve_unmet", assessment.blockers)

    def test_transport_operation_template_is_repeatable(self):
        from src.operations import OperationFactory
        operation = OperationFactory.create(
            "round_trip_transport", probe_id=7,
            metadata={"cycle": self.plan.to_dict()},
        )
        self.assertEqual(operation.metadata["cycle"]["resourceType"], "metals")

    def test_repeat_returns_to_loading_at_source(self):
        service = RoundTripTransportService()
        self.assertEqual(
            service.next_state(self.plan, TransportCycleState.UNLOADING),
            TransportCycleState.TO_RETURN_POINT,
        )
        self.assertEqual(
            service.next_state(self.plan, TransportCycleState.TO_RETURN_POINT),
            TransportCycleState.LOADING,
        )

    def test_configured_refuel_stop_requires_fresh_sufficient_source(self):
        from dataclasses import replace
        plan = replace(
            self.plan,
            refuel_sectors=(self.plan.destination,),
            minimum_refuel_source_amount=25,
        )
        service = RoundTripTransportService()
        missing = service.assess(
            plan, self.probe, cargo_amount=10, cargo_capacity=10,
            state=TransportCycleState.TO_DESTINATION,
        )
        verified = service.assess(
            plan, self.probe, cargo_amount=10, cargo_capacity=10,
            state=TransportCycleState.TO_DESTINATION,
            deuterium_sources=(
                {"coordinates": {"x": 2, "y": 0, "z": 0},
                 "amount": 30, "fresh": True},
            ),
        )
        self.assertIn("deuterium_source_unknown:2,0,0", missing.blockers)
        self.assertTrue(verified.ready)

    def test_configured_refuel_stop_requires_available_manny(self):
        from dataclasses import replace
        plan = replace(self.plan, refuel_sectors=(self.plan.destination,))
        assessment = RoundTripTransportService().assess(
            plan, self.probe, cargo_amount=10, cargo_capacity=10,
            state=TransportCycleState.TO_DESTINATION,
            deuterium_sources=(
                {"coordinates": self.plan.destination, "amount": 30, "fresh": True},
            ),
            refill_manny_available=False,
        )
        self.assertIn("refill_manny_unavailable", assessment.blockers)

    def test_ui_service_persists_complete_round_trip_operation(self):
        from src.data import DataEngine
        from src.ui.controller import MissionControlDataService

        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "transport.sqlite3")
            service = MissionControlDataService(client=object(), data_engine=engine)
            operation = service.save_transport_cycle({
                "probeId": 7,
                "resourceType": "metals",
                "source": {"x": 0, "y": 0, "z": 0},
                "destination": {"x": 2, "y": 0, "z": 0},
                "returnPoint": {"x": 0, "y": 2, "z": 0},
                "loadUntilPercent": 90,
                "unloadUntilPercent": 10,
                "protectedDeuterium": 25,
                "reserveHops": 2,
                "repeat": True,
            })

            cycle = operation["metadata"]["cycle"]
            self.assertEqual(cycle["source"], {"x": 0, "y": 0, "z": 0})
            self.assertEqual(cycle["destination"], {"x": 2, "y": 0, "z": 0})
            self.assertEqual(cycle["returnPoint"], {"x": 0, "y": 2, "z": 0})
            self.assertEqual(engine.operation_records()[0]["state"], "planned")

    def test_saved_transport_can_be_started_and_removed(self):
        from src.data import DataEngine
        from src.planner.desired_state_store import DesiredStateStore
        from src.ui.controller import MissionControlDataService

        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "transport.sqlite3")
            service = MissionControlDataService(client=object(), data_engine=engine)
            service._selected_probe_id = 7
            operation = service.save_transport_cycle({
                "probeId": 7,
                "resourceType": "deuterium",
                "source": {"x": 2, "y": 0, "z": 0},
                "destination": {"x": 4, "y": 0, "z": 0},
                "returnPoint": {"x": 0, "y": 0, "z": 0},
                "loadSourceMode": "mine_in_sector",
            })

            active = service.start_transport_cycle(operation["id"])

            self.assertEqual(active["state"], "active")
            self.assertEqual(
                DesiredStateStore(engine).load(7).travel.target,
                SectorCoordinates(2, 0, 0),
            )
            self.assertTrue(service.delete_transport_cycle(operation["id"]))
            self.assertEqual(engine.operation_records(), [])


if __name__ == "__main__":
    unittest.main()
