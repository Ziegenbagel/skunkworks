import tempfile
import unittest
from pathlib import Path

from src.data import DataEngine
from src.operations.operations import Operations
from src.presentation import MissionControlViewModelBuilder
from src.ui.controller import MissionControlController
from tests.test_planner_missions import build_operations


class UiPreparationTests(unittest.TestCase):
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

    def test_periodic_check_pauses_automation_for_unreviewed_api(self):
        controller = MissionControlController()
        controller._dashboard = {"connection": "connected"}
        controller._automation_timer.start()

        controller._accept_compatibility({"version": 107, "compatible": False})

        self.assertFalse(controller._api_compatible)
        self.assertFalse(controller._automation_timer.isActive())
        self.assertEqual(controller.dashboard["connectionLabel"], "API REVIEW REQUIRED")
        self.assertEqual(controller.dashboard["compatibility"]["serverVersion"], 107)
        self.assertIn("paused", controller.error)

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

        work = MissionControlViewModelBuilder._production(probe, mannies)

        self.assertEqual(len(work), 2)
        self.assertIn("STEEL PLATE", work[0]["displayText"])
        self.assertIn("MINING METALS, ICE", work[1]["displayText"])
        self.assertIn("Target: Ferric Haven", work[1]["detailText"])
        self.assertNotIn("Target: asteroid-1", work[1]["detailText"])
        self.assertIn("Estimated completion", work[0]["detailText"])
        self.assertRegex(work[0]["eta"], r"2026-\d{2}-\d{2}  \d{2}:\d{2}:\d{2} .+ \(UTC[+-]\d{2}:\d{2}\)")
        self.assertGreater(work[0]["etaEpochMs"], 0)

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

    def test_galaxy_view_exposes_discovered_nodes_and_neighbor_links(self):
        from src.models.galaxy import GalaxyMap

        base = build_operations()
        galaxy = GalaxyMap()
        galaxy.record_visit({"relativeCoordinates": {"x": 0, "y": 0, "z": 0}, "visitCount": 2})
        galaxy.record_visit({"relativeCoordinates": {"x": 1, "y": 1, "z": 0}, "visitCount": 1})
        base.world.galaxy = galaxy

        view = MissionControlViewModelBuilder(base).build()["galaxy"]

        self.assertEqual(view["sectorCount"], 2)
        self.assertEqual(len(view["edges"]), 1)
        self.assertEqual(view["nodes"][0]["mapState"], "current")
        self.assertEqual(view["nodes"][1]["mapState"], "visited")

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
