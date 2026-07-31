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
            self.assertIn("resources", view)
            self.assertIn("alerts", view)
            self.assertIn("missions", view)
            self.assertIn("production", view)
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


if __name__ == "__main__":
    unittest.main()
