import tempfile
import unittest
from pathlib import Path

from src.data import DataEngine
from src.operations.operations import Operations
from src.presentation import MissionControlViewModelBuilder
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

    def test_archive_is_separate_from_game_logbook(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "ui.sqlite3")
            engine.save_archive_report("brief-1", "Command Brief", "Local report")

            self.assertEqual(engine.archive_reports()[0]["title"], "Command Brief")
            self.assertEqual(engine.records("logbook_pages"), [])


if __name__ == "__main__":
    unittest.main()
