import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.data import DataEngine


class DataEngineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.engine = DataEngine(
            Path(self.temporary.name) / "history.sqlite3"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_schema_is_migrated(self):
        self.assertEqual(self.engine.schema_version(), 2)

    def test_remembers_selected_probe(self):
        self.engine.remember_probe(762)

        self.assertEqual(
            self.engine.remembered_probe_id(),
            762,
        )

    def test_records_probe_sector_and_resources(self):
        world = SimpleNamespace(
            probe={
                "id": 762,
                "name": "Beta",
                "model": "generic",
                "status": "idle",
                "sector": {
                    "relative": {"x": 2, "y": 0, "z": 0}
                },
            },
            sector={
                "snapshot": {
                    "sector": {
                        "relativeCoordinates": {
                            "x": 2,
                            "y": 0,
                            "z": 0,
                        },
                        "knowledgeLevel": "detailed",
                        "confidence": 1,
                    },
                },
                "resources": [
                    {
                        "id": "asteroid-1",
                        "classification": "persistent",
                        "resources": {"metals": 12.5},
                        "composition": {"metals": 1},
                    },
                ],
            },
        )

        self.engine.record_world(
            world,
            observed_at="2026-07-30T00:00:00+00:00",
        )

        self.assertEqual(
            len(self.engine.probe_history(762)),
            1,
        )
        resources = self.engine.resource_history(
            "metals",
            762,
        )
        self.assertEqual(resources[0]["amount"], 12.5)

    def test_visit_sync_is_idempotent(self):
        payload = {
            "visitedSectors": [
                {
                    "relativeCoordinates": {
                        "x": 2,
                        "y": 0,
                        "z": 0,
                    },
                    "firstVisitedAt": "first",
                    "lastVisitedAt": "latest",
                    "visitCount": 4,
                },
            ],
        }

        self.engine.sync_visits(payload, probe_id=762)
        self.engine.sync_visits(payload, probe_id=762)

        visits = self.engine.visits(762)
        self.assertEqual(len(visits), 1)
        self.assertEqual(visits[0]["visit_count"], 4)

        galaxy = self.engine.galaxy_map()
        self.assertEqual(len(galaxy.sectors()), 1)

    def test_event_records_are_updated_not_duplicated(self):
        self.engine.record_records(
            "messages",
            [{"id": 4, "status": "unread"}],
            probe_id=762,
            observed_at="first",
        )
        self.engine.record_records(
            "messages",
            [{"id": 4, "status": "read"}],
            probe_id=762,
            observed_at="second",
        )

        records = self.engine.records(
            "messages",
            probe_id=762,
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(
            json.loads(records[0]["payload_json"])["status"],
            "read",
        )

    def test_action_journal_supports_idempotency_checks(self):
        command = {
            "type": "move_probe",
            "probeId": 762,
            "payload": {"target": {"x": 1, "y": 1, "z": 0}},
        }
        self.engine.record_action(
            "fingerprint",
            command,
            "dry_run",
        )

        self.assertFalse(
            self.engine.action_was_successful("fingerprint")
        )

        self.engine.record_action(
            "fingerprint",
            command,
            "succeeded",
        )
        self.assertTrue(
            self.engine.action_was_successful("fingerprint")
        )
        self.assertEqual(
            len(self.engine.action_history(762)),
            2,
        )


if __name__ == "__main__":
    unittest.main()
