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
        self.assertEqual(self.engine.schema_version(), 4)

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
        cached = self.engine.galaxy_map()
        self.engine.sync_visits(payload, probe_id=762)

        self.assertIs(self.engine.galaxy_map(), cached)

        visits = self.engine.visits(762)
        self.assertEqual(len(visits), 1)
        self.assertEqual(visits[0]["visit_count"], 4)

        galaxy = self.engine.galaxy_map()
        self.assertEqual(len(galaxy.sectors()), 1)

    def test_probe_arrival_invalidates_galaxy_map_but_same_sector_does_not(self):
        def record(x, observed_at):
            self.engine.record_world(SimpleNamespace(
                probe={
                    "id": 762,
                    "name": "Beta",
                    "model": "generic",
                    "status": "idle",
                    "sector": {"relative": {"x": x, "y": 0, "z": 0}},
                },
                sector={"snapshot": None, "resources": []},
            ), observed_at=observed_at)

        record(1, "2026-08-14T10:00:00+00:00")
        cached = self.engine.galaxy_map()
        record(1, "2026-08-14T10:01:00+00:00")
        self.assertIs(self.engine.galaxy_map(), cached)

        record(2, "2026-08-14T10:02:00+00:00")
        self.assertIsNot(self.engine.galaxy_map(), cached)

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

    def test_deleted_alert_is_removed_from_the_local_snapshot(self):
        self.engine.record_records(
            "alerts",
            [{"id": "alert-4", "message": "Resolved"}],
            probe_id=762,
            observed_at="first",
        )

        self.engine.delete_record("alerts", "alert-4", probe_id=762)

        self.assertEqual(self.engine.records("alerts", probe_id=762), [])

    def test_explicit_map_scan_is_persisted_as_sector_detail(self):
        self.engine.record_sector_observation(762, {
            "sector": {
                "relativeCoordinates": {"x": 1, "y": 1, "z": 0},
                "knowledgeLevel": "neighbor_scan",
                "confidence": 0.82,
                "objects": [{"id": "star-1", "type": "star"}],
            }
        })

        record = self.engine.galaxy_map().sectors()[0]

        self.assertEqual(record.coordinates.x, 1)
        self.assertEqual(record.observed["sector"]["objects"][0]["type"], "star")

    def test_galaxy_map_reuses_cache_until_explicit_scan_invalidates_it(self):
        first = self.engine.galaxy_map()
        self.assertIs(self.engine.galaxy_map(), first)

        self.engine.record_sector_observation(762, {
            "sector": {
                "relativeCoordinates": {"x": 4, "y": 2, "z": 2},
                "knowledgeLevel": "neighbor_scan",
                "confidence": 0.8,
                "objects": [],
            }
        })

        refreshed = self.engine.galaxy_map()
        self.assertIsNot(refreshed, first)
        self.assertEqual(len(refreshed.sectors()), 1)

    def test_galaxy_map_cold_build_uses_latest_observation_per_sector(self):
        coordinates = {"x": 2, "y": 2, "z": 4}
        for observed_at, confidence in (
            ("2026-08-13T10:00:00+00:00", 0.2),
            ("2026-08-13T11:00:00+00:00", 0.9),
        ):
            self.engine.record_sector_observation(762, {
                "sector": {
                    "relativeCoordinates": coordinates,
                    "knowledgeLevel": "neighbor_scan",
                    "confidence": confidence,
                    "objects": [],
                }
            }, observed_at=observed_at)

        record = self.engine.galaxy_map(max_age_seconds=0).sectors()[0]

        self.assertEqual(record.observed["sector"]["confidence"], 0.9)

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

    def test_probe_route_retains_ordered_revisits(self):
        def world(x, observed_at):
            value = SimpleNamespace(
                probe={"id": 762, "name": "Beta", "model": "generic", "status": "idle",
                       "sector": {"relative": {"x": x, "y": 0, "z": 0}}},
                sector={"snapshot": None, "resources": []},
            )
            self.engine.record_world(value, observed_at=observed_at)

        world(0, "2026-01-01T00:00:00+00:00")
        world(1, "2026-01-01T00:01:00+00:00")
        world(0, "2026-01-01T00:02:00+00:00")

        self.assertEqual(
            [item["point"] for item in self.engine.probe_route(762)],
            [(0, 0, 0), (1, 0, 0), (0, 0, 0)],
        )


if __name__ == "__main__":
    unittest.main()
