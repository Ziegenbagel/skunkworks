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
                    },
                },
            ]
        }

        work = MissionControlViewModelBuilder._production(probe, mannies)

        self.assertEqual(len(work), 2)
        self.assertIn("STEEL PLATE", work[0]["displayText"])
        self.assertIn("MINING METALS, ICE", work[1]["displayText"])
        self.assertIn("Estimated completion", work[0]["detailText"])

    def test_controller_persists_probe_role_and_updates_live_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "ui.sqlite3")
            service = type("Service", (), {"data_engine": engine})()
            controller = MissionControlController(service)
            controller._dashboard = {"automation": {"probeRoles": {}}}

            controller.assignProbeRole(9, "deuterium_reserve")

            self.assertEqual(controller.dashboard["automation"]["probeRoles"]["9"], "deuterium_reserve")
            self.assertEqual(engine.fleet_roles("probe")[0]["role"], "deuterium_reserve")

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
