import unittest
import tempfile
from pathlib import Path

from src.models.galaxy import SectorCoordinates
from src.planner.desired_state import DesiredState, TravelGoal
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

    def test_auto_travel_journey_uses_durable_target_and_live_leg_eta(self):
        from src.data import DataEngine
        from src.ui.controller import MissionControlDataService
        from tests.test_planner_missions import build_operations

        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "journey.sqlite3")
            operations = build_operations()
            operations.world.probe["movement"] = {
                "originSector": {"relative": {"x": 0, "y": 0, "z": 0}},
                "arrivalSector": {"relative": {"x": 1, "y": 1, "z": 0}},
                "remainingSeconds": 60,
            }
            desired = DesiredState(
                travel=TravelGoal(SectorCoordinates(3, 3, 0), "segmented"),
            )
            service = MissionControlDataService(data_engine=engine)

            journey = service._transport_journey_view(operations, 7, desired)

            self.assertEqual(journey["phase"], "auto_travel")
            self.assertEqual(journey["hopNumber"], 1)
            self.assertEqual(journey["totalHops"], 3)
            self.assertEqual(journey["finalDestinationLabel"], "3:3:0")
            self.assertGreater(journey["estimatedFinalArrivalEpochMs"], 0)

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
            self.assertEqual(
                DesiredStateStore(engine).load(7).travel.route_mode,
                "segmented",
            )
            self.assertTrue(service.delete_transport_cycle(operation["id"]))
            self.assertEqual(engine.operation_records(), [])

    def test_start_skips_source_and_loading_when_tanker_is_already_full(self):
        from src.data import DataEngine
        from src.planner.desired_state_store import DesiredStateStore
        from src.ui.controller import MissionControlDataService
        from tests.test_planner_missions import build_operations

        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "transport.sqlite3")
            service = MissionControlDataService(client=object(), data_engine=engine)
            service._selected_probe_id = 7
            service._operations = build_operations(fuel=100)
            service._operations.world.probe["id"] = 7
            service._operations.world.probe["model"] = "deuterium_tanker"
            service._operations.world.probe["fuel"]["maxDeuterium"] = 100
            operation = service.save_transport_cycle({
                "probeId": 7,
                "resourceType": "deuterium",
                "source": {"x": 0, "y": 0, "z": 0},
                "destination": {"x": 2, "y": 0, "z": 0},
                "returnPoint": {"x": 0, "y": 0, "z": 0},
                "loadAmount": 100,
                "unloadAmount": 20,
                "loadSourceMode": "mine_in_sector",
            })

            active = service.start_transport_cycle(operation["id"])

            self.assertEqual(active["metadata"]["transportPhase"], "to_destination")
            self.assertEqual(
                DesiredStateStore(engine).load(7).travel.target,
                SectorCoordinates(2, 0, 0),
            )
            self.assertEqual(
                DesiredStateStore(engine).load(7).travel.route_mode,
                "segmented",
            )

            paused = service.pause_transport_cycle(operation["id"])

            self.assertEqual(paused["state"], "paused")
            self.assertIsNone(DesiredStateStore(engine).load(7).travel)

    def test_unloading_uses_target_free_space_and_protects_return_fuel(self):
        from src.data import DataEngine
        from src.ui.controller import MissionControlDataService
        from tests.test_planner_missions import build_operations

        class Client:
            def get_probe(self, probe_id):
                return {"probe": {
                    "id": probe_id,
                    "status": "idle",
                    "fuel": {"deuterium": 4, "maxDeuterium": 100},
                }}

        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "transport.sqlite3")
            service = MissionControlDataService(client=Client(), data_engine=engine)
            service._selected_probe_id = 7
            service._operations = build_operations(fuel=100)
            service._operations.world.probe.update({"id": 7, "model": "deuterium_tanker"})
            operation = service.save_transport_cycle({
                "probeId": 7,
                "resourceType": "deuterium",
                "source": {"x": 2, "y": 0, "z": 0},
                "destination": {"x": 0, "y": 0, "z": 0},
                "returnPoint": {"x": 2, "y": 0, "z": 0},
                "destinationProbeId": 9,
                "loadAmount": 100,
                "protectedDeuterium": 20,
                "reserveHops": 1,
            })
            service.start_transport_cycle(operation["id"])

            runtime = service.automation_view(service._operations, 7)
            transfer = next(
                item for item in runtime["queue"]
                if item["metadata"].get("transportTransfer")
            )

            # 100 source - 20 protected - three 2-ECE travel hops leaves
            # 74 ECE, less than the target's 96 ECE free capacity.
            self.assertEqual(transfer["payload"]["amount"], 74)
            self.assertEqual(transfer["payload"]["targetProbeId"], 9)

    def test_unloading_waits_while_one_transfer_is_already_active(self):
        from src.data import DataEngine
        from src.ui.controller import MissionControlDataService
        from tests.test_planner_missions import build_operations

        class Client:
            def get_probe(self, probe_id):
                return {"probe": {
                    "id": probe_id,
                    "status": "idle",
                    "fuel": {"deuterium": 4, "maxDeuterium": 100},
                }}

        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "transport.sqlite3")
            service = MissionControlDataService(
                client=Client(),
                data_engine=engine,
            )
            service._selected_probe_id = 7
            service._operations = build_operations(fuel=100)
            service._operations.world.probe.update({
                "id": 7,
                "model": "deuterium_tanker",
            })
            service._operations.world.mannies["mannies"][0]["currentTask"] = (
                "transferring_deuterium_to_probe"
            )
            operation = service.save_transport_cycle({
                "probeId": 7,
                "resourceType": "deuterium",
                "source": {"x": 2, "y": 0, "z": 0},
                "destination": {"x": 0, "y": 0, "z": 0},
                "returnPoint": {"x": 2, "y": 0, "z": 0},
                "destinationProbeId": 9,
                "loadAmount": 100,
                "protectedDeuterium": 20,
                "reserveHops": 1,
            })
            service.start_transport_cycle(operation["id"])

            runtime = service.automation_view(service._operations, 7)

            self.assertFalse(any(
                item["metadata"].get("transportTransfer")
                for item in runtime["queue"]
            ))

    def test_reserve_tanker_tops_up_live_hub_free_capacity(self):
        from src.data import DataEngine
        from src.operations.logistics import FleetRoleService
        from src.ui.controller import MissionControlDataService
        from tests.test_planner_missions import build_operations

        sector = {"relative": {"x": 0, "y": 0, "z": 0}}

        class Client:
            def get_probe(self, probe_id):
                return {"probe": {
                    "id": probe_id,
                    "model": "generic",
                    "status": "idle",
                    "sector": sector,
                    "fuel": {"deuterium": 35, "maxDeuterium": 100},
                }}

        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "reserve.sqlite3")
            roles = FleetRoleService(engine)
            roles.assign(
                "probe", 7, "deuterium_reserve",
                metadata={"protectedDeuterium": 100, "targetProbeId": 8},
            )
            roles.assign("probe", 9, "hub")
            operations = build_operations(fuel=350)
            operations.world.probe.update({
                "id": 7,
                "model": "deuterium_tanker",
                "status": "idle",
                "sector": sector,
                "fuel": {"deuterium": 350, "maxDeuterium": 400},
            })
            service = MissionControlDataService(client=Client(), data_engine=engine)

            tasks = service._reserve_tanker_delivery_tasks(operations, 7)

            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].target, "8")
            self.assertEqual(tasks[0].quantity, 65)
            self.assertIn("live free capacity", tasks[0].reason)

    def test_completed_one_time_travel_is_retired_at_safe_destination(self):
        from dataclasses import replace
        from src.data import DataEngine
        from src.planner.desired_state import TravelGoal
        from src.planner.desired_state_store import DesiredStateStore
        from src.ui.controller import MissionControlDataService
        from tests.test_planner_missions import build_operations

        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "travel.sqlite3")
            service = MissionControlDataService(client=object(), data_engine=engine)
            operations = build_operations()
            goal = replace(
                DesiredStateStore(engine).load(7),
                travel=TravelGoal(SectorCoordinates(0, 0, 0), "segmented"),
            )
            DesiredStateStore(engine).save(goal, 7)

            service.automation_view(operations, 7)

            self.assertIsNone(DesiredStateStore(engine).load(7).travel)


if __name__ == "__main__":
    unittest.main()
