import unittest

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


if __name__ == "__main__":
    unittest.main()
