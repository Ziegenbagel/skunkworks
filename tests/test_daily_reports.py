import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from src.data import DataEngine
from src.reporting import DailyProbeReportService


class DailyProbeReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.engine = DataEngine(Path(self.temporary.name) / "history.sqlite3")
        self.now = datetime(2026, 8, 9, 18, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
        self.reporter = DailyProbeReportService(self.engine, now=lambda: self.now)

    def tearDown(self):
        self.temporary.cleanup()

    def test_explorer_report_lists_each_asteroid_and_sector_totals(self):
        world = SimpleNamespace(
            probe={
                "id": 762, "name": "Explorer One", "model": "generic", "status": "idle",
                "sector": {"relative": {"x": 2, "y": 1, "z": -3}},
            },
            sector={
                "snapshot": {"sector": {
                    "relativeCoordinates": {"x": 2, "y": 1, "z": -3},
                    "knowledgeLevel": "detailed", "confidence": 100,
                }},
                "resources": [
                    {"id": "rock-a", "classification": "asteroid", "resources": {"metals": 12.5, "ice": 3.0}},
                    {"id": "rock-b", "classification": "asteroid", "resources": {"metals": 7.5}},
                ],
            },
        )
        self.engine.record_world(world, observed_at="2026-08-09T20:00:00+00:00")

        content = self.reporter.build(
            {"id": 762, "name": "Explorer One"},
            "explorer",
            datetime(2026, 8, 8, 17, 0, tzinfo=self.now.tzinfo),
            datetime(2026, 8, 9, 17, 0, tzinfo=self.now.tzinfo),
        )

        self.assertIn("Sector 2:1:-3", content)
        self.assertIn("Asteroid rock-a", content)
        self.assertIn("Asteroid rock-b", content)
        self.assertIn("metals: 20.000 ECE", content)
        self.assertIn("ice: 3.000 ECE", content)

    def test_generation_is_once_per_probe_and_report_day(self):
        created = []

        def create_page(probe_id, payload):
            created.append((probe_id, payload))
            return {"page": {"id": 91}}

        first = self.reporter.generate_due(
            ({"id": 762, "name": "Explorer One"},),
            {"762": "explorer"},
            create_page,
        )
        second = self.reporter.generate_due(
            ({"id": 762, "name": "Explorer One"},),
            {"762": "explorer"},
            create_page,
        )

        self.assertEqual(len(first["created"]), 1)
        self.assertEqual(second["created"], [])
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0][1]["title"], "Skunkworks Daily Report · 2026-08-09")
        self.assertEqual(len(self.engine.archive_reports()), 1)

    def test_daily_page_remains_new_until_opened(self):
        page = {"id": 4, "title": "Skunkworks Daily Report · 2026-08-09"}
        annotated = self.reporter.annotate_page(page, 762)
        self.assertTrue(annotated["isNewDailyReport"])

        self.reporter.mark_read(762, page["title"])

        annotated = self.reporter.annotate_page(page, 762)
        self.assertFalse(annotated["isNewDailyReport"])


if __name__ == "__main__":
    unittest.main()
