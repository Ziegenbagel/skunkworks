import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from src.data import DataEngine
from src.execution import ExecutionMode
from src.operations.operations import Operations
from src.operations.logistics import FleetRoleService
from src.presentation import MissionControlViewModelBuilder
from src.ui.controller import (
    ManualCraftReservationConflict,
    MissionControlController,
    MissionControlDataService,
    _FleetAutomationWorker,
)
from tests.test_planner_missions import build_operations


class UiPreparationTests(unittest.TestCase):
    def test_slow_startup_releases_splash_without_cancelling_refresh(self):
        controller = MissionControlController()
        controller._refreshing = True

        controller._release_slow_startup()

        self.assertFalse(controller.startupLoading)
        self.assertTrue(controller.refreshing)
        self.assertIn("taking longer than expected", controller.error)

    def test_shutdown_stops_schedulers_clears_queue_and_quits_when_idle(self):
        class Pool:
            def __init__(self):
                self.cleared = False

            def clear(self):
                self.cleared = True

            def activeThreadCount(self):
                return 0

        pool = Pool()
        controller = MissionControlController(thread_pool=pool)
        controller._automation_timer.start()
        controller._compatibility_timer.start()

        with patch("src.ui.controller.QCoreApplication.quit") as quit_app:
            controller.shutdown()

        self.assertTrue(controller.shuttingDown)
        self.assertTrue(pool.cleared)
        self.assertFalse(controller._automation_timer.isActive())
        self.assertFalse(controller._compatibility_timer.isActive())
        quit_app.assert_called_once_with()

    def test_view_model_exposes_ui_domains_without_api_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "ui.sqlite3")
            base = build_operations()
            operations = Operations(
                base.world, base.manufacturing.recipes, data_engine=engine
            )

            view = MissionControlViewModelBuilder(operations, engine).build()

            self.assertEqual(view["connection"], "connected")
            self.assertEqual(view["focus"]["probeId"], 1)
            self.assertIn("health", view)
            self.assertIn("operations", view)
            self.assertIn("archive", view)
            self.assertIn("sector", view)
            self.assertIn("galaxy", view)
            self.assertIn("resources", view)
            self.assertIn("alerts", view)
            self.assertIn("missions", view)
            self.assertIn("production", view)
            self.assertIn("navigation", view)
            self.assertEqual(len(view["navigation"]["neighbors"]), 12)
            self.assertEqual(view["connectionLabel"], "CONNECTED")

    def test_archive_is_separate_from_game_logbook(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "ui.sqlite3")
            engine.save_archive_report("brief-1", "Command Brief", "Local report")

            self.assertEqual(engine.archive_reports()[0]["title"], "Command Brief")
            self.assertEqual(engine.records("logbook_pages"), [])

    def test_qt_controller_refreshes_and_switches_probe_context(self):
        class Service:
            def __init__(self):
                self.requested = []

            def load(self, probe_id):
                selected = probe_id or 7
                self.requested.append(selected)
                return {
                    "focus": {"probeId": selected},
                    "probeOptions": (
                        {"id": 7, "name": "Explorer", "model": "generic"},
                        {"id": 9, "name": "Tanker", "model": "deuterium_tanker"},
                    ),
                    "connection": "connected",
                    "missions": ({"id": "mission-1"},),
                }

        class ImmediatePool:
            @staticmethod
            def start(worker):
                worker.run()

        service = Service()
        controller = MissionControlController(service, ImmediatePool())

        controller.refresh()
        self.assertEqual(controller.focusedProbeId, 7)
        self.assertEqual(len(controller.availableProbes), 2)
        self.assertIsInstance(controller.dashboard["missions"], list)
        self.assertFalse(controller.refreshing)

        controller.selectProbe(9)
        self.assertEqual(controller.focusedProbeId, 9)
        self.assertEqual(service.requested, [7, 9])

    def test_probe_switch_requests_recent_fleet_index_reuse(self):
        class Service:
            def __init__(self):
                self.requests = []

            def load(self, probe_id, progress=None, prefer_cached_fleet=False):
                selected = probe_id or 7
                self.requests.append((selected, prefer_cached_fleet))
                return {
                    "focus": {"probeId": selected},
                    "probeOptions": (
                        {"id": 7, "name": "Explorer"},
                        {"id": 9, "name": "Tanker"},
                    ),
                    "connection": "connected",
                }

        class ImmediatePool:
            @staticmethod
            def start(worker):
                worker.run()

        service = Service()
        controller = MissionControlController(service, ImmediatePool())
        controller.refresh()
        controller.selectProbe(9)

        self.assertEqual(service.requests, [(7, False), (9, True)])

    def test_failed_refresh_retains_snapshot_and_marks_it_stale(self):
        class Service:
            fail = False

            def load(self, probe_id):
                if self.fail:
                    raise RuntimeError("Game service is temporarily unavailable")
                return {
                    "focus": {"probeId": 7},
                    "probeOptions": ({"id": 7, "name": "Explorer"},),
                    "connection": "connected",
                    "connectionLabel": "CONNECTED",
                    "resources": ({"name": "Ice", "amount": 3},),
                }

        class ImmediatePool:
            @staticmethod
            def start(worker):
                worker.run()

        service = Service()
        controller = MissionControlController(service, ImmediatePool())
        controller.refresh()
        service.fail = True
        controller.refresh()

        self.assertEqual(controller.dashboard["resources"][0]["amount"], 3)
        self.assertEqual(controller.dashboard["connection"], "stale")
        self.assertEqual(controller.dashboard["connectionLabel"], "LIVE LINK INTERRUPTED")
        self.assertIn("temporarily unavailable", controller.error)

    def test_refresh_response_cannot_mismatch_selector_and_dashboard_identity(self):
        class Service:
            def load(self, probe_id, **_kwargs):
                return {
                    "focus": {"probeId": 9, "name": "Explorer"},
                    "probeOptions": (
                        {"id": 7, "name": "Hub"},
                        {"id": 9, "name": "Explorer"},
                    ),
                    "connection": "connected",
                }

        class ImmediatePool:
            @staticmethod
            def start(worker):
                worker.run()

        controller = MissionControlController(Service(), ImmediatePool())
        controller._start_refresh(7)

        self.assertEqual(controller.focusedProbeId, 9)
        self.assertEqual(controller.dashboard["focus"]["probeId"], 9)
        self.assertIn("API returned probe 9", controller.error)

    def test_automatic_tick_dispatches_replanning_off_the_ui_thread(self):
        started = []

        class DeferredPool:
            @staticmethod
            def start(worker):
                started.append(worker)

        class SignalStub:
            def connect(self, _callback):
                pass

        class Worker:
            def __init__(self, probe_ids):
                self.probe_ids = tuple(probe_ids)
                self.signals = type(
                    "Signals",
                    (),
                    {"succeeded": SignalStub(), "failed": SignalStub()},
                )()

        automatic_policy = type(
            "Policy",
            (),
            {"mode": "automatic", "live_execution_enabled": True},
        )()
        controller = MissionControlController(None, DeferredPool())
        controller._focused_probe_id = 7
        with patch("src.ui.controller.ExecutionPolicyStore.load", return_value=automatic_policy), patch(
            "src.ui.controller._FleetAutomationWorker", Worker
        ):
            controller._dispatch_fleet_automation()

        self.assertEqual(len(started), 1)
        self.assertEqual(started[0].probe_ids, (7,))
        self.assertIs(controller._fleet_automation_worker, started[0])

    def test_fleet_worker_reuses_one_service_and_recent_fleet_index(self):
        instances = []

        class Service:
            def __init__(self):
                instances.append(self)
                self.loads = []

            def load(self, probe_id, **kwargs):
                self.loads.append((probe_id, kwargs))

            def run_automation_cycle(self, _fingerprint, _risk):
                return {"status": "idle"}

        automatic_policy = type(
            "Policy", (), {"mode": "automatic", "live_execution_enabled": True},
        )()
        worker = _FleetAutomationWorker((7, 9, 11), service_factory=Service)
        with patch("src.ui.controller.ExecutionPolicyStore.load", return_value=automatic_policy):
            worker.run()

        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].loads, [
            (7, {"include_archival": False, "prefer_cached_fleet": False}),
            (9, {"include_archival": False, "prefer_cached_fleet": True}),
            (11, {"include_archival": False, "prefer_cached_fleet": True}),
        ])

    def test_busy_periodic_tick_is_queued_instead_of_discarded(self):
        controller = MissionControlController()
        controller._focused_probe_id = 7
        controller._refreshing = True

        controller._automation_tick()

        self.assertTrue(controller._automation_tick_pending)

    def test_periodic_deadline_refreshes_before_dispatching_cycle(self):
        controller = MissionControlController()
        controller._focused_probe_id = 7
        refreshes = []
        controller._start_refresh = lambda probe_id, **kwargs: refreshes.append(
            (probe_id, kwargs)
        )

        controller._automation_tick()

        self.assertEqual(refreshes, [(7, {"prefer_cached_fleet": True})])
        self.assertTrue(controller._automation_after_refresh)

    def test_finished_refresh_dispatches_cycle_without_moving_heartbeat_deadline(self):
        class Credentials:
            @staticmethod
            def get():
                return "configured"

            @staticmethod
            def source():
                return "test"

        controller = MissionControlController(credential_store=Credentials())
        callbacks = []
        controller._automation_after_refresh = True
        with patch(
            "src.ui.controller.QTimer.singleShot",
            side_effect=lambda _delay, callback: callbacks.append(callback),
        ):
            controller._finish_refresh()
        self.assertEqual(callbacks, [controller._dispatch_fleet_automation])

        callbacks.clear()
        with patch.object(controller._automation_timer, "isActive", return_value=True), \
             patch.object(controller._automation_timer, "start") as start:
            controller._finish_refresh()
        start.assert_not_called()

    def test_automation_heartbeat_is_repeating_so_refreshes_cannot_starve_cycles(self):
        controller = MissionControlController()

        self.assertFalse(controller._automation_timer.isSingleShot())

    def test_finished_refresh_runs_queued_automation_tick(self):
        controller = MissionControlController()
        controller._automation_tick_pending = True
        callbacks = []

        with patch(
            "src.ui.controller.QTimer.singleShot",
            side_effect=lambda _delay, callback: callbacks.append(callback),
        ):
            controller._finish_refresh()

        self.assertEqual(callbacks, [controller._automation_tick])

    def test_scheduled_cycle_completion_always_refreshes_focused_probe(self):
        controller = MissionControlController()
        controller._focused_probe_id = 7
        controller._fleet_automation_worker = object()
        refreshes = []
        controller._start_refresh = lambda probe_id, **kwargs: refreshes.append(
            (probe_id, kwargs)
        )

        controller._accept_fleet_automation(({
            "probeId": 7,
            "result": {"status": "idle", "message": "No order ready"},
        },))

        self.assertEqual(refreshes, [(7, {"prefer_cached_fleet": True})])
        self.assertIsNone(controller._fleet_automation_worker)

    def test_observe_only_rejects_manual_game_commands(self):
        controller = MissionControlController()
        controller._focused_probe_id = 7
        policy = type("Policy", (), {"mode": ExecutionMode.OBSERVE})()

        with patch("src.ui.controller.ExecutionPolicyStore.load", return_value=policy):
            allowed = controller._require_manual_control()

        self.assertFalse(allowed)
        self.assertIn("OBSERVE ONLY", controller.error)

    def test_approval_and_automatic_modes_allow_manual_game_commands(self):
        controller = MissionControlController()
        controller._focused_probe_id = 7
        for mode in (ExecutionMode.APPROVE, ExecutionMode.AUTOMATIC):
            policy = type("Policy", (), {"mode": mode})()
            with patch("src.ui.controller.ExecutionPolicyStore.load", return_value=policy):
                self.assertTrue(controller._require_manual_control())

    def test_manual_craft_conflict_waits_for_explicit_one_order_override(self):
        calls = []

        class Service:
            @staticmethod
            def manual_craft(recipe_id, manny_id, override_reservations=False):
                calls.append((recipe_id, manny_id, override_reservations))
                if not override_reservations:
                    raise ManualCraftReservationConflict("Reserved resources")

        controller = MissionControlController(service=Service())
        controller._focused_probe_id = 7
        controller._require_manual_control = lambda: True
        controller._start_refresh = lambda probe_id: calls.append(("refresh", probe_id))

        controller.queueManualCraft("container", "manny-a")

        self.assertEqual(controller.error, "")
        self.assertEqual(controller.manualCraftOverride["recipeId"], "container")
        controller.overrideManualCraft()
        self.assertEqual(calls[1], ("container", "manny-a", True))
        self.assertEqual(calls[2], ("refresh", 7))
        self.assertEqual(controller.manualCraftOverride, {})

    def test_manual_craft_override_can_be_cancelled_without_dispatch(self):
        controller = MissionControlController()
        controller._manual_craft_override = {
            "probeId": 7, "recipeId": "container", "mannyId": "manny-a",
        }

        controller.cancelManualCraftOverride()

        self.assertEqual(controller.manualCraftOverride, {})

    def test_manual_craft_override_surfaces_game_validation_detail(self):
        response = requests.Response()
        response.status_code = 422
        response._content = (
            b'{"detail":{"error":{"code":"insufficient_resources",'
            b'"message":"Not enough inputs","missingResources":{"metals":0.4}}}}'
        )

        class Service:
            @staticmethod
            def manual_craft(*_args, **_kwargs):
                raise requests.HTTPError(response=response)

        controller = MissionControlController(service=Service())
        controller._focused_probe_id = 7
        controller._manual_craft_override = {
            "probeId": 7, "recipeId": "manny", "mannyId": "manny-a",
        }

        controller.overrideManualCraft()

        self.assertIn("insufficient_resources", controller.error)
        self.assertIn("Not enough inputs", controller.error)
        self.assertIn("metals: 0.4", controller.error)
        self.assertEqual(controller.errorContext, "command")

    def test_manual_automation_cycle_is_dispatched_off_the_ui_thread(self):
        started = []

        class DeferredPool:
            @staticmethod
            def start(worker):
                started.append(worker)

        controller = MissionControlController(None, DeferredPool())
        controller._focused_probe_id = 7
        controller.runAutomationCycle()

        self.assertEqual(len(started), 1)
        self.assertEqual(started[0].probe_id, 7)
        self.assertIs(controller._automation_cycle_worker, started[0])

    def test_manual_automation_cycle_requested_during_refresh_is_retained(self):
        controller = MissionControlController()
        controller._focused_probe_id = 7
        controller._refreshing = True

        controller.runAutomationCycle()

        self.assertTrue(controller._manual_automation_cycle_pending)

    def test_same_sector_transfer_coerces_target_probe_id_to_integer(self):
        class Client:
            def __init__(self):
                self.calls = []

            def request(self, method, path, **kwargs):
                self.calls.append((method, path, kwargs))
                return {"accepted": True}

        client = Client()
        with tempfile.TemporaryDirectory() as temporary:
            service = MissionControlDataService(
                client=client,
                data_engine=DataEngine(Path(temporary) / "transfer.sqlite3"),
            )
            service._selected_probe_id = 7

            service.inventory_manny_action(
                "transfer-deuterium-to-probe", "manny-a",
                {"targetProbeId": "42", "amount": 1.25},
            )

        self.assertEqual(client.calls[-1][2]["json"]["targetProbeId"], 42)

    def test_periodic_check_pauses_automation_for_too_old_api(self):
        controller = MissionControlController()
        controller._dashboard = {"connection": "connected"}
        controller._automation_timer.start()

        controller._accept_compatibility({"version": 102, "compatible": False})

        self.assertFalse(controller._api_compatible)
        self.assertFalse(controller._automation_timer.isActive())
        self.assertEqual(controller.dashboard["connectionLabel"], "API REVIEW REQUIRED")
        self.assertEqual(controller.dashboard["compatibility"]["serverVersion"], 102)
        self.assertIn("paused", controller.error)

    def test_periodic_check_warns_but_continues_for_newer_api(self):
        class Timer:
            stopped = False
            active = True

            def setInterval(self, _milliseconds):
                pass

            def isActive(self):
                return self.active

            def start(self):
                self.active = True

            def stop(self):
                self.stopped = True
                self.active = False

        controller = MissionControlController()
        controller._dashboard = {"connection": "connected"}
        timer = Timer()
        controller._automation_timer = timer

        controller._accept_compatibility({
            "version": 116, "compatible": True, "reviewed": False,
        })

        self.assertTrue(controller._api_compatible)
        self.assertFalse(timer.stopped)
        self.assertFalse(controller.dashboard["compatibility"]["reviewed"])
        self.assertIn("continuing", controller.dashboard["compatibility"]["warning"])
        self.assertEqual(
            controller.dashboard["connectionLabel"],
            "CONNECTED · API REVIEW PENDING",
        )

    def test_ready_automation_work_uses_fast_scheduler_cadence(self):
        controller = MissionControlController()

        controller._configure_automation_timer({
            "mode": "automatic",
            "liveExecutionEnabled": True,
            "queue": ({"disposition": "ready"},),
        })

        self.assertEqual(controller._automation_timer.interval(), 60_000)

    def test_idle_automation_retains_one_minute_scheduler_cadence(self):
        controller = MissionControlController()

        controller._configure_automation_timer({
            "mode": "automatic",
            "liveExecutionEnabled": True,
            "queue": ({"disposition": "blocked"},),
        })

        self.assertEqual(controller._automation_timer.interval(), 60_000)

    def test_partial_dashboard_runtime_cannot_stop_scheduler_heartbeat(self):
        class Credentials:
            @staticmethod
            def get():
                return "configured"

            @staticmethod
            def source():
                return "test"

        controller = MissionControlController(credential_store=Credentials())
        with patch.object(controller._automation_timer, "start") as start:
            controller._configure_automation_timer({})

        start.assert_called_once_with()
        self.assertEqual(controller._automation_timer.interval(), 60_000)

    def test_compatible_api_transition_rearms_scheduler_heartbeat(self):
        class Credentials:
            @staticmethod
            def get():
                return "configured"

            @staticmethod
            def source():
                return "test"

        controller = MissionControlController(credential_store=Credentials())
        controller._automation_timer.stop()

        with patch.object(controller._automation_timer, "start") as start:
            controller._accept_compatibility({"version": 106, "compatible": True})

        start.assert_called_once_with()

    def test_production_includes_active_manny_crafting_and_mining(self):
        probe = {
            "inventory": {
                "items": [
                    {
                        "id": "printer-1",
                        "type": "atomic_3d_printer",
                        "name": "Atomic printer",
                        "currentTask": None,
                    }
                ]
            }
        }
        mannies = {
            "mannies": [
                {
                    "id": "manny-a",
                    "name": "Z1-A",
                    "currentTask": "crafting",
                    "taskProgressPercent": 79.01,
                    "taskStartTime": "2026-07-31T20:41:12+00:00",
                    "taskEstimatedEndTime": "2026-08-01T00:41:12+00:00",
                    "task": {"recipe": "steel_plate", "recipeName": "Steel plate"},
                },
                {
                    "id": "manny-c",
                    "name": "Z1-C",
                    "currentTask": "mining",
                    "taskProgressPercent": 59.69,
                    "taskEstimatedEndTime": "2026-08-01T03:04:20+00:00",
                    "task": {
                        "resourceTypes": ["metals", "ice"],
                        "phase": "extracting",
                        "objectId": "asteroid-1",
                        "target": {"id": "asteroid-1", "name": "Ferric Haven"},
                    },
                },
            ]
        }

        work = MissionControlViewModelBuilder._production(
            probe,
            mannies,
            {"manny-a": "Build the next tanker component."},
        )

        self.assertEqual(len(work), 2)
        self.assertIn("STEEL PLATE", work[0]["displayText"])
        self.assertIn("MINING METALS, ICE", work[1]["displayText"])
        self.assertIn("Target: Ferric Haven", work[1]["detailText"])
        self.assertNotIn("Target: asteroid-1", work[1]["detailText"])
        self.assertIn("Estimated completion", work[0]["detailText"])
        self.assertIn(
            "Automation reason: Build the next tanker component.",
            work[0]["detailText"],
        )
        self.assertIn("Task origin: No matching Skunkworks", work[1]["detailText"])
        self.assertRegex(work[0]["eta"], r"2026-\d{2}-\d{2}  \d{2}:\d{2}:\d{2} .+ \(UTC[+-]\d{2}:\d{2}\)")
        self.assertGreater(work[0]["etaEpochMs"], 0)
        self.assertGreater(work[0]["startedAtEpochMs"], 0)
        self.assertIn("Started: 2026-", work[0]["detailText"])

    def test_atomic_printer_infers_recipe_from_assisting_manny(self):
        probe = {"inventory": {"items": [{
            "id": "printer-1",
            "type": "atomic_3d_printer",
            "name": "Atomic Printer",
            "currentTask": "atomic_printing",
            "taskProgressPercent": 83.3,
        }]}}
        mannies = {"mannies": [{
            "id": "manny-a",
            "name": "Manny A",
            "currentTask": "assisting_atomic_printer",
            "task": {"recipeId": "integrated_circuit"},
        }]}

        work = MissionControlViewModelBuilder._production(probe, mannies)

        printer = next(item for item in work if item["id"] == "printer-1")
        self.assertIn("INTEGRATED CIRCUIT", printer["displayText"])
        self.assertIn("Recipe: Integrated Circuit", printer["detailText"])

    def test_reserved_container_business_error_is_operator_readable(self):
        response = requests.Response()
        response.status_code = 409
        response._content = (
            b'{"detail":{"error":{"code":"storage_container_reserved",'
            b'"message":"reserved"}}}'
        )
        error = requests.HTTPError(response=response)

        message = MissionControlController._inventory_error_message(error)

        self.assertIn("STORAGE CONTAINER RESERVED", message)
        self.assertIn("active crafting task", message)
        self.assertIn("Reassign Crafting Reservations", message)

    def test_reservation_reassignment_failure_promises_no_partial_change(self):
        response = requests.Response()
        response.status_code = 409
        response._content = b'{"detail":{"error":{"code":"crafting_reservations_cannot_be_reassigned"}}}'
        message = MissionControlController._inventory_error_message(
            requests.HTTPError(response=response)
        )
        self.assertIn("CANNOT BE REASSIGNED", message)
        self.assertIn("Nothing was changed", message)

    def test_moving_probe_transfer_error_requires_no_polling_guidance(self):
        response = requests.Response()
        response.status_code = 409
        response._content = b'{"detail":{"error":{"code":"probe_already_moving"}}}'
        message = MissionControlController._inventory_error_message(
            requests.HTTPError(response=response)
        )
        self.assertIn("PROBE ALREADY MOVING", message)
        self.assertIn("source and destination", message)

    def test_production_includes_idle_mannies_and_order_readiness(self):
        work = MissionControlViewModelBuilder._production(
            {"inventory": {"items": []}},
            {"mannies": [
                {"id": "ready", "name": "Manny Ready", "currentTask": None, "canReceiveOrders": True},
                {"id": "busy", "name": "Manny Offline", "currentTask": None, "canReceiveOrders": False},
            ]},
        )

        self.assertEqual(len(work), 2)
        self.assertEqual(work[0]["taskType"], "idle")
        self.assertIn("IDLE · READY", work[0]["displayText"])
        self.assertIn("Can receive automation order: No", work[1]["detailText"])

    def test_overdue_mining_exposes_storage_return_deadlock(self):
        work = MissionControlViewModelBuilder._production(
            {"inventory": {"freeCapacity": 0.02, "items": []}},
            {"mannies": [{
                "id": "miner",
                "name": "Miner",
                "currentTask": "mining",
                "taskProgressPercent": 100,
                "taskEstimatedEndTime": "2020-01-01T00:00:00+00:00",
                "task": {"targetAmount": 0.248, "depositedAmount": 0},
            }]},
        )

        self.assertTrue(work[0]["storageBlockRisk"])
        self.assertAlmostEqual(work[0]["returnCapacityRequired"], 0.298)
        self.assertIn("Insufficient probe storage", work[0]["detailText"])

    def test_atomic_printer_names_the_recipe_it_is_crafting(self):
        work = MissionControlViewModelBuilder._production(
            {"inventory": {"items": [{
                "id": "printer-1",
                "type": "atomic_3d_printer",
                "name": "Atomic printer",
                "currentTask": "atomic_printing",
                "taskProgressPercent": 42,
                "task": {"recipeId": "integrated_circuit"},
            }]}},
            {"mannies": []},
        )

        self.assertEqual(len(work), 1)
        self.assertIn("CRAFTING INTEGRATED CIRCUIT", work[0]["displayText"])
        self.assertIn("Recipe: Integrated Circuit", work[0]["detailText"])

    def test_production_reason_summarizes_actual_order_and_one_purpose(self):
        reason = MissionControlViewModelBuilder._concise_automation_reason({
            "type": "manny_mine",
            "payload": {
                "resources": ["carbon_compounds"],
                "targetAmount": 0.55,
            },
            "reason": (
                "Need 76.480 additional carbon compounds. This mining order unlocks "
                "production target: manny; the 20 carbon compounds reserve target."
            ),
        })

        self.assertEqual(
            reason,
            "Mine 0.55 ECE Organic Compound. Supports production target: manny.",
        )
        self.assertNotIn("76.480", reason)
        self.assertNotIn("reserve target", reason)

    def test_crafting_reason_names_tanker_assembly_purpose(self):
        reason = MissionControlViewModelBuilder._concise_automation_reason({
            "type": "manny_craft",
            "payload": {"recipe": "scut_relay"},
            "reason": "Tanker component 2/8: scut relay — 1 required. Priority 1 tanker goal reserves this work.",
        })

        self.assertEqual(
            reason,
            "Craft one Scut Relay. Required for Tanker Assembly. Dispatched by Skunkworks.",
        )

    def test_sector_details_include_exact_planet_habitability_and_composition(self):
        detail = MissionControlViewModelBuilder._sector_detail_text({
            "knowledgeLevel": "detailed",
            "objects": [{
                "type": "solar_system",
                "bookmarkTargets": [{
                    "type": "planet", "category": "terrestrial",
                    "habitabilityScore": 0.5, "mass": 1.2,
                    "radius": 0.9, "intelligentLife": False,
                }],
            }],
        })

        self.assertIn("composition/category: Terrestrial", detail)
        self.assertIn("habitability: 0.500000", detail)
        self.assertIn("mass 1.2 Earth masses", detail)

    def test_navigation_current_sector_exposes_same_planet_details_as_neighbors(self):
        base = build_operations()
        base.world.sector["snapshot"] = {"sector": {
            "knowledgeLevel": "detailed", "confidence": 1,
            "objects": [{
                "type": "solar_system", "bookmarkTargets": [{
                    "type": "planet", "category": "oceanic",
                    "habitabilityScore": 0.75,
                }],
            }],
        }}

        navigation = MissionControlViewModelBuilder(base).navigation_view()

        self.assertTrue(navigation["current"]["isCurrent"])
        self.assertEqual(navigation["current"]["objectCount"], 1)
        self.assertIn("1 planets", navigation["current"]["scanSummary"])
        self.assertIn("composition/category: Oceanic", navigation["current"]["detailText"])

    def test_controller_persists_probe_role_and_updates_live_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "ui.sqlite3")
            service = type("Service", (), {"data_engine": engine})()
            controller = MissionControlController(service)
            controller._focused_probe_id = 9
            controller._dashboard = {
                "defaultProbeId": 9,
                "automation": {"probeRoles": {}},
            }

            controller.assignProbeRole(9, "deuterium_reserve")

            self.assertEqual(controller.dashboard["automation"]["probeRoles"]["9"], "deuterium_reserve")
            self.assertEqual(engine.fleet_roles("probe")[0]["role"], "deuterium_reserve")

    def test_controller_persists_probe_specific_role_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "ui.sqlite3")
            FleetRoleService(engine).assign("probe", 7, "deuterium_reserve")
            service = type("Service", (), {"data_engine": engine})()
            controller = MissionControlController(service)
            controller._dashboard = {"automation": {"probeRoleSettings": {}}}

            controller.saveProbeRoleSettings(
                7, {"targetProbeId": 8, "protectedDeuterium": 75},
            )

            row = dict(engine.fleet_roles("probe")[0])
            self.assertEqual(json.loads(row["metadata_json"])["targetProbeId"], 8)
            self.assertEqual(
                controller.dashboard["automation"]["probeRoleSettings"]["7"]["protectedDeuterium"],
                75,
            )

    def test_controller_rejects_probe_role_change_from_secondary_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "ui.sqlite3")
            service = type("Service", (), {"data_engine": engine})()
            controller = MissionControlController(service)
            controller._focused_probe_id = 2
            controller._dashboard = {
                "defaultProbeId": 1,
                "automation": {"probeRoles": {}},
            }

            controller.assignProbeRole(2, "miner")

            self.assertEqual(controller.dashboard["automation"]["probeRoles"], {})
            self.assertIn("main/default probe", controller.error)

    def test_saving_targets_preserves_owned_probe_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "ui.sqlite3")
            service = type(
                "Service",
                (),
                {
                    "data_engine": engine,
                    "automation_view": lambda self: {
                        "mode": "observe",
                        "liveExecutionEnabled": False,
                    },
                },
            )()
            controller = MissionControlController(service)
            controller._focused_probe_id = 1
            controller._dashboard = {
                "automation": {
                    "probeRoles": {"1": "hub", "2": "miner"},
                    "fleetStatus": [{"model": "generic"}],
                },
            }

            controller.saveAutomationSettings({"minimumFuelPercent": 35})

            automation = controller.dashboard["automation"]
            self.assertEqual(automation["probeRoles"], {"1": "hub", "2": "miner"})
            self.assertEqual(automation["fleetStatus"], [{"model": "generic"}])
            self.assertEqual(automation["minimumFuelPercent"], 35)

    def test_resource_summary_uses_current_probe_fuel_and_inventory_amounts(self):
        resources = MissionControlViewModelBuilder._resources({
            "fuel": {"deuterium": 82, "maxDeuterium": 100},
            "inventory": {
                "capacity": 26,
                "resourceStocks": [
                    {"type": "metals", "name": "Metals", "amount": 5.57},
                    {"type": "ice", "name": "Ice", "amount": 2.0595},
                    {
                        "type": "carbon_compounds",
                        "name": "Carbon compounds",
                        "amount": 1.0605,
                    },
                ],
            },
        })

        self.assertEqual(
            [item["reading"] for item in resources],
            ["82%  ·  82 / 100", "5.57 ECE", "2.06 ECE", "1.06 ECE"],
        )
        self.assertEqual(resources[0]["value"], 0.82)

    def test_resource_ledger_covers_probe_deposits_and_visible_containers(self):
        world = build_operations().world
        world.probe["inventory"]["resourceStocks"][0]["containers"] = [{
            "container": {"id": "probe-core", "kind": "probe", "label": "Probe core"},
            "amount": 2,
        }]
        world.sector["snapshot"] = {"sector": {"objects": [{
            "id": "floating-1", "type": "detached_container", "name": "Cache",
            "mode": "drifting", "capacity": 1,
        }]}}

        ledger = MissionControlViewModelBuilder._resource_ledger(world)

        self.assertTrue(any(row["scope"] == "probe_storage" for row in ledger["rows"]))
        self.assertTrue(any(row["scope"] == "natural_deposit" for row in ledger["rows"]))
        natural = [row for row in ledger["rows"] if row["scope"] == "natural_deposit"]
        self.assertEqual(len(natural), len(world.sector["resources"]))
        self.assertIn("Metals:", natural[0]["detail"])
        self.assertTrue(all(amount > 0 for amount in natural[0]["resources"].values()))
        detached = next(row for row in ledger["rows"] if row["scope"] == "detached_container")
        self.assertIn("Contents not exposed by API", detached["detail"])

    def test_inventory_management_includes_equipment_and_container_placement(self):
        world = build_operations().world
        world.probe["name"] = "Carrier"
        world.probe["inventory"]["containers"] = [{
            "id": "probe-core", "kind": "probe", "label": "Probe",
            "capacity": 1, "usedCapacity": 0.06, "rules": {},
        }]
        world.probe["inventory"]["items"] = [{
            "id": "engine-1", "type": "deuterium_engine", "name": "Deuterium engine",
            "containerSpace": 0.06,
            "container": {"id": "probe-core", "kind": "probe", "label": "Probe"},
        }]

        inventory = MissionControlViewModelBuilder._inventory_management(world)

        self.assertEqual(inventory["probeName"], "Carrier")
        self.assertEqual(inventory["items"][0]["type"], "deuterium_engine")
        self.assertEqual(inventory["items"][0]["containerLabel"], "Probe · Carrier")

    def test_inventory_management_exposes_v107_sector_operations(self):
        world = build_operations().world
        world.mannies["mannies"].append({
            "id": "manny-waiting", "name": "Waiting Manny",
            "currentTask": {"type": "waiting_for_space"},
            "canReceiveOrders": False,
        })
        world.sector["snapshot"] = {"sector": {"objects": [
            {"id": "system-1", "type": "solar_system", "bookmarkTargets": [
                {"id": "star-1", "type": "star", "name": "Primary"},
                {"id": "asteroid-1", "type": "asteroid", "name": "Iron Rock"},
            ]},
            {"id": "construct-1", "type": "dormant_construct", "name": "Dormant Frame"},
            {"id": "41", "type": "scut_relay", "name": "Relay 41", "status": "off"},
            {"id": "42", "type": "scut_relay", "name": "Relay 42", "status": "on", "isTransitBeacon": False},
            {"id": "43", "type": "scut_relay", "name": "Relay 43", "status": "on", "isTransitBeacon": True},
            {"id": "station-1", "type": "deuterium_refuel_station", "name": "Fuel Station"},
        ]}}

        inventory = MissionControlViewModelBuilder._inventory_management(world)

        self.assertEqual({item["id"] for item in inventory["bookmarkTargets"]}, {"star-1", "asteroid-1"})
        self.assertEqual({item["id"] for item in inventory["inspectableObjects"]}, {"asteroid-1", "construct-1"})
        self.assertEqual([item["id"] for item in inventory["inactiveScutRelays"]], ["41"])
        self.assertEqual([item["id"] for item in inventory["activeScutRelaysWithoutBeacon"]], ["42"])
        self.assertEqual([item["id"] for item in inventory["refuelStations"]], ["station-1"])
        self.assertEqual([item["id"] for item in inventory["waitingCargoMannies"]], ["manny-waiting"])

    def test_inventory_management_exposes_v112_motorized_asteroid_controls(self):
        world = build_operations().world
        world.hazard_context = {"improvements": {"improvements": [{
            "id": "anatiform_asteroid_sculpting", "available": True,
        }]}}
        trajectory = {
            "id": "atr_123", "asteroidId": "rock-moving",
            "mode": "sector_transfer", "status": "crossing_sector",
        }
        world.sector["snapshot"] = {"sector": {"objects": [{
            "id": "system-1", "type": "solar_system", "bookmarkTargets": [
                {"id": "star-1", "type": "star", "name": "Primary"},
                {"id": "rock-new", "type": "asteroid", "name": "New Rock"},
                {"id": "rock-empty", "type": "asteroid", "name": "Empty Motor", "motorized": True, "motorFuelStatus": "empty"},
                {"id": "rock-full", "type": "asteroid", "name": "Full Motor", "motorized": True, "motorFuelStatus": "full"},
                {"id": "rock-moving", "type": "asteroid", "name": "Moving Rock", "motorized": True, "motorFuelStatus": "empty", "trajectory": trajectory},
            ],
        }]}}

        inventory = MissionControlViewModelBuilder._inventory_management(world)

        self.assertEqual([item["id"] for item in inventory["motorizationTargets"]], ["rock-new"])
        self.assertEqual([item["id"] for item in inventory["refuelAsteroidTargets"]], ["rock-empty"])
        self.assertEqual([item["id"] for item in inventory["launchableAsteroids"]], ["rock-full"])
        self.assertEqual(inventory["asteroidTrajectories"], (trajectory,))
        self.assertTrue(inventory["anatiformSculptingAvailable"])
        self.assertEqual(
            [item["id"] for item in inventory["sculptableAsteroids"]],
            ["rock-new", "rock-empty", "rock-full", "rock-moving"],
        )
        self.assertEqual(
            {item["id"] for item in inventory["asteroidImpactTargets"]},
            {"star-1", "rock-new", "rock-empty", "rock-full", "rock-moving"},
        )

    def test_inventory_management_lists_only_empty_additional_assembly_containers(self):
        world = build_operations().world
        world.probe["inventory"]["containers"] = [
            {"id": "probe-core", "kind": "probe", "usedCapacity": 0},
            {"id": "empty-1", "kind": "container", "usedCapacity": 0},
            {"id": "used-1", "kind": "container", "usedCapacity": 0.01},
        ]

        inventory = MissionControlViewModelBuilder._inventory_management(world)

        self.assertEqual([item["id"] for item in inventory["emptyAssemblyContainers"]], ["empty-1"])

    def test_galaxy_view_exposes_discovered_nodes_and_neighbor_links(self):
        from src.models.galaxy import GalaxyMap

        base = build_operations()
        galaxy = GalaxyMap()
        galaxy.record_visit({"relativeCoordinates": {"x": 0, "y": 0, "z": 0}, "visitCount": 2})
        galaxy.record_visit({"relativeCoordinates": {"x": 1, "y": 1, "z": 0}, "visitCount": 1})
        base.world.galaxy = galaxy

        view = MissionControlViewModelBuilder(base).build()["galaxy"]

        self.assertEqual(view["sectorCount"], 2)
        self.assertEqual(view["focusCoordinates"], {"x": 0, "y": 0, "z": 0})
        self.assertEqual(view["focusProbeId"], base.world.probe["id"])
        self.assertEqual(len(view["edges"]), 1)
        self.assertEqual(view["nodes"][0]["mapState"], "current")
        self.assertEqual(view["nodes"][1]["mapState"], "visited")

    def test_all_nonvisited_scan_records_use_the_scanned_filter(self):
        from src.models.galaxy import GalaxyMap

        base = build_operations()
        galaxy = GalaxyMap()
        galaxy.record_observation({"sector": {
            "relativeCoordinates": {"x": 2, "y": 0, "z": 0},
            # Older or partial API records may omit knowledgeLevel entirely.
            "objects": [],
        }}, probe_id=base.world.probe["id"])
        base.world.galaxy = galaxy

        view = MissionControlViewModelBuilder(base)._galaxy_view(
            base.world,
            {"x": 0, "y": 0, "z": 0},
        )

        self.assertEqual(len(view["nodes"]), 1)
        self.assertEqual(view["nodes"][0]["mapState"], "scanned")
        self.assertEqual(view["unknownNeighborCount"], 0)

    def test_galaxy_view_exposes_focus_coordinates_without_matching_node(self):
        from src.models.galaxy import GalaxyMap

        base = build_operations()
        base.world.galaxy = GalaxyMap()

        view = MissionControlViewModelBuilder(base)._galaxy_view(
            base.world,
            {"x": -12, "y": 4, "z": 8},
        )

        self.assertEqual(view["nodes"], ())
        self.assertEqual(view["focusCoordinates"], {"x": -12, "y": 4, "z": 8})

    def test_build_uses_authoritative_sector_snapshot_coordinates_when_probe_omits_them(self):
        base = build_operations()
        base.world.probe["sector"] = None
        base.world.sector["snapshot"] = {
            "sector": {
                "relativeCoordinates": {"x": 1, "y": 1, "z": -2},
                "objects": [],
            }
        }

        view = MissionControlViewModelBuilder(base).build()

        self.assertEqual(view["focus"]["sector"], {"x": 1, "y": 1, "z": -2})
        self.assertEqual(view["galaxy"]["focusCoordinates"], {"x": 1, "y": 1, "z": -2})

    def test_galaxy_view_does_not_convert_unknown_focus_to_origin(self):
        base = build_operations()

        view = MissionControlViewModelBuilder(base)._galaxy_view(base.world, {})

        self.assertIsNone(view["focusCoordinates"])

    def test_galaxy_view_exposes_resource_hazard_salvage_filters_and_recent_route(self):
        from src.models.galaxy import GalaxyMap

        class VisitHistory:
            def visits(self, probe_id):
                self.probe_id = probe_id
                return [
                    {"sector_x": 1, "sector_y": 1, "sector_z": 0, "last_visited_at": "new"},
                    {"sector_x": 0, "sector_y": 0, "sector_z": 0, "last_visited_at": "old"},
                ]

        base = build_operations()
        galaxy = GalaxyMap()
        galaxy.record_observation({"sector": {
            "relativeCoordinates": {"x": 0, "y": 0, "z": 0},
            "knowledgeLevel": "detailed", "confidence": 1,
            "objects": [{
                "id": "mine", "type": "asteroid", "mannyMineable": True,
                "resourceAmounts": {"metals": 3.5, "ice": 0},
            }],
        }}, probe_id=base.world.probe["id"])
        galaxy.record_observation({"sector": {
            "relativeCoordinates": {"x": 1, "y": 1, "z": 0},
            "knowledgeLevel": "detailed", "confidence": 1,
            "objects": [
                {"id": "danger", "type": "black_hole"},
                {"id": "cache", "type": "detached_container"},
            ],
        }}, probe_id=base.world.probe["id"])
        base.world.galaxy = galaxy
        history = VisitHistory()

        builder = MissionControlViewModelBuilder(base, data_engine=history)
        view = builder._galaxy_view(base.world, builder._coordinates(base.world.probe))

        self.assertEqual(view["nodes"][0]["resourceTypes"], ["metals"])
        self.assertTrue(view["nodes"][1]["hasHazard"])
        self.assertTrue(view["nodes"][1]["hasDetachedContainers"])
        self.assertEqual(view["recentTrail"][0]["from"], "0:0:0")
        self.assertEqual(view["recentTrail"][0]["to"], "1:1:0")
        self.assertEqual(view["recentTrailNodes"], ("1:1:0", "0:0:0"))
        self.assertEqual(history.probe_id, base.world.probe["id"])

    def test_galaxy_view_exposes_active_scut_coverage_volumes(self):
        base = build_operations()
        base.world.hazard_context = {"scutNetworks": [{"network": {
            "name": "Home Grid",
            "relays": [{
                "id": 17, "status": "on", "coverageRadiusSectors": 2,
                "sector": {"relative": {"x": 4, "y": -1, "z": 3}},
            }],
        }}]}

        view = MissionControlViewModelBuilder(base)._galaxy_view(
            base.world, {"x": 0, "y": 0, "z": 0}
        )

        self.assertEqual(view["scutRanges"], ({
            "id": "17", "x": 4, "y": -1, "z": 3, "radius": 2,
            "networkName": "Home Grid",
        },))
        cells = {cell["id"]: cell for cell in view["scutCoverageCells"]}
        self.assertIn("6:-1:3", cells)  # Exact radius-two FCC boundary.
        self.assertNotIn("6:1:5", cells)  # Cube corner is three FCC hops away.
        boundary = {cell["id"] for cell in view["scutCoverageBoundary"]}
        self.assertIn("6:-1:3", boundary)
        self.assertNotIn("4:-1:3", boundary)  # Relay center is interior.

    def test_sector_view_exposes_black_hole_destruction_deadline(self):
        base = build_operations()
        base.world.sector["snapshot"] = {"sector": {
            "knowledgeLevel": "detailed", "confidence": 1,
            "objects": [{
                "id": "singularity", "type": "black_hole",
                "destructionAt": "2030-01-02T03:04:05+00:00",
            }],
        }}

        view = MissionControlViewModelBuilder(base)._sector_view(
            base.world, {"x": 0, "y": 0, "z": 0}
        )

        self.assertTrue(view["blackHoleDanger"])
        self.assertGreater(view["destructionEpochMs"], 0)

    def test_galaxy_resource_filter_unifies_game_and_api_compound_names(self):
        normalize = MissionControlViewModelBuilder._normalized_resource_type

        self.assertEqual(normalize("Organic compound"), "carbon_compounds")
        self.assertEqual(normalize("organic_compounds"), "carbon_compounds")
        self.assertEqual(normalize("Carbon compound"), "carbon_compounds")
        self.assertEqual(normalize("carbon_compounds"), "carbon_compounds")

    def test_empty_detailed_sector_is_explicit_in_view_model(self):
        base = build_operations()
        base.world.sector["snapshot"] = {
            "sector": {
                "relativeCoordinates": {"x": 0, "y": 0, "z": 0},
                "knowledgeLevel": "detailed",
                "confidence": 1,
                "objects": [],
            }
        }

        sector = MissionControlViewModelBuilder(base).build()["sector"]

        self.assertIn("reports no celestial", sector["emptyReason"])


if __name__ == "__main__":
    unittest.main()
