import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.data import DataEngine
from src.data.engine import SCHEMA_VERSION


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

    def test_identical_worker_snapshots_do_not_duplicate_large_sector_history(self):
        world = SimpleNamespace(
            probe={
                "id": 762, "name": "Beta", "model": "generic", "status": "idle",
                "sector": {"relative": {"x": 2, "y": 0, "z": 0}},
            },
            sector={
                "snapshot": {"sector": {
                    "relativeCoordinates": {"x": 2, "y": 0, "z": 0},
                    "knowledgeLevel": "detailed", "confidence": 1,
                    "objects": [{"id": "asteroid-1", "type": "asteroid"}],
                }},
                "resources": [{
                    "id": "asteroid-1", "classification": "persistent",
                    "resources": {"metals": 12.5}, "composition": {"metals": 1},
                }],
            },
        )
        self.engine.record_world(world, observed_at="2026-07-30T00:00:00+00:00")
        # A separate worker uses a separate DataEngine instance.
        second = DataEngine(self.engine.path)
        second.record_world(world, observed_at="2026-07-30T00:01:00+00:00")

        with self.engine._connect() as connection:
            sectors = connection.execute("SELECT COUNT(*) FROM sector_observations").fetchone()[0]
        self.assertEqual(sectors, 1)
        self.assertEqual(len(self.engine.resource_history("metals", 762)), 1)

    def test_identical_probe_state_is_not_recorded_once_per_refresh(self):
        world = SimpleNamespace(
            probe={
                "id": 762, "name": "Beta", "model": "generic", "status": "idle",
                "sector": {"relative": {"x": 2, "y": 0, "z": 0}},
            },
            sector={"snapshot": None, "resources": []},
        )

        self.engine.record_world(world, observed_at="2026-07-30T00:00:00+00:00")
        DataEngine(self.engine.path).record_world(
            world, observed_at="2026-07-30T00:01:00+00:00",
        )

        self.assertEqual(len(self.engine.probe_history(762)), 1)
        payload = json.loads(self.engine.probe_history(762)[0]["payload_json"])
        self.assertEqual(payload["sector"]["relative"]["x"], 2)

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

    def test_recent_successful_actions_is_bounded_and_newest_first(self):
        command = {
            "type": "manny_craft", "probeId": 762,
            "payload": {"recipe": "manny"},
        }
        self.engine.record_action("old", command, "succeeded", observed_at="2026-01-01")
        self.engine.record_action("failed", command, "failed", observed_at="2026-01-02")
        self.engine.record_action("new", command, "succeeded", observed_at="2026-01-03")

        rows = self.engine.recent_successful_actions(762, limit=1)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fingerprint"], "new")

    def test_compaction_downsamples_old_telemetry_without_touching_actions(self):
        command = {"type": "move_probe", "probeId": 762, "payload": {}}
        self.engine.record_action("keep", command, "succeeded", observed_at="2020-01-01")
        for minute in range(3):
            world = SimpleNamespace(
                probe={
                    "id": 762, "name": "Beta", "model": "generic", "status": "idle",
                    "sector": {"relative": {"x": minute, "y": 0, "z": 0}},
                },
                sector={"snapshot": None, "resources": []},
            )
            self.engine.record_world(
                world, observed_at=f"2020-01-01T00:0{minute}:00+00:00",
            )

        result = self.engine.compact_history(30)

        self.assertEqual(result["probeRowsRemoved"], 2)
        self.assertEqual(len(self.engine.probe_history(762)), 1)
        self.assertEqual(len(self.engine.action_history(762)), 1)

    def test_compaction_keeps_only_latest_complete_sector_payload_per_location(self):
        coordinates = {"x": 2, "y": 0, "z": 0}
        for observed_at, confidence in (
            ("2026-08-20T00:00:00+00:00", 0.2),
            ("2026-08-21T00:00:00+00:00", 0.9),
        ):
            self.engine.record_sector_observation(762, {
                "sector": {
                    "relativeCoordinates": coordinates,
                    "knowledgeLevel": "detailed",
                    "confidence": confidence,
                    "objects": [],
                },
            }, observed_at=observed_at)

        result = self.engine.compact_history(30)

        self.assertEqual(result["sectorRowsRemoved"], 1)
        sectors = self.engine.galaxy_map(max_age_seconds=0).sectors()
        self.assertEqual(len(sectors), 1)
        self.assertEqual(sectors[0].observed["sector"]["confidence"], 0.9)

    def test_automatic_maintenance_runs_at_most_once_per_week(self):
        self.engine.set_preference(
            "last_history_compaction_at", "2020-01-01T00:00:00+00:00",
        )

        result = self.engine.run_due_maintenance()
        second = self.engine.run_due_maintenance()

        self.assertIsInstance(result, dict)
        self.assertIsNone(second)

    def test_database_report_exposes_reclaimable_space_and_row_counts(self):
        self.engine.set_preference("operator", "ready")

        report = self.engine.database_report()

        self.assertEqual(report["schemaVersion"], SCHEMA_VERSION)
        self.assertGreater(report["allocatedBytes"], 0)
        self.assertGreaterEqual(report["totalFileBytes"], report["files"]["database"])
        self.assertEqual(report["rowCounts"]["preferences"], 2)
        self.assertGreaterEqual(report["reclaimableBytes"], 0)

    def test_integrity_report_checks_database_and_foreign_keys(self):
        report = self.engine.integrity_report()

        self.assertTrue(report["ok"])
        self.assertEqual(report["quickCheck"], ("ok",))
        self.assertEqual(report["foreignKeyErrors"], ())

    def test_online_backup_is_verified_and_preserves_committed_data(self):
        self.engine.set_preference("operator", "ready")
        backup_path = Path(self.temporary.name) / "backups" / "release.sqlite3"

        result = self.engine.backup(backup_path)
        restored = DataEngine(backup_path)

        self.assertTrue(result["verified"])
        self.assertGreater(result["bytes"], 0)
        self.assertEqual(restored.get_preference("operator"), "ready")
        self.assertTrue(restored.integrity_report()["ok"])
        with self.assertRaises(FileExistsError):
            self.engine.backup(backup_path)
        with self.assertRaises(ValueError):
            self.engine.backup(self.engine.path)

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
