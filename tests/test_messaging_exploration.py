import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.data import DataEngine
from src.models.galaxy import SectorCoordinates
from src.operations import EventService, MessagingService, MissionService, OperationFactory
from src.operations.exploration import ExplorationService
from tests.test_planner_missions import build_operations


class MessagingExplorationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.engine = DataEngine(Path(self.temporary.name) / "events.sqlite3")

    def tearDown(self):
        self.temporary.cleanup()

    def test_inbox_and_coordinate_extraction_are_read_only(self):
        self.engine.record_records(
            "messages",
            [{"id": 1, "subject": "Investigate 2, 0, 0", "isRead": False}],
            probe_id=7,
        )
        service = MessagingService(self.engine)

        self.assertEqual(len(service.inbox(7, unread_only=True)), 1)
        self.assertEqual(
            service.extract_coordinates(service.inbox(7)[0]),
            (SectorCoordinates(2, 0, 0),),
        )
        with self.assertRaises(RuntimeError):
            service.send(7, {"body": "No implicit sending"})

    def test_mission_abandonment_requires_confirmation(self):
        capabilities = SimpleNamespace(
            missions=SimpleNamespace(abandon=lambda mission_id: {"id": mission_id})
        )
        service = MissionService(self.engine, capabilities)

        with self.assertRaises(PermissionError):
            service.abandon(3)
        self.assertEqual(service.abandon(3, confirmed=True), {"id": 3})

    def test_unified_event_timeline_orders_domains(self):
        self.engine.record_records("alerts", [{"id": 2}], observed_at="2026-01-02")
        self.engine.record_records("missions", [{"id": 1}], observed_at="2026-01-01")
        service = EventService(self.engine)
        service.classify("missions", 1, acknowledged=True, priority="urgent")

        timeline = service.timeline()

        self.assertEqual([event["domain"] for event in timeline], ["missions", "alerts"])
        self.assertTrue(timeline[0]["acknowledged"])

    def test_oracle_contacts_replace_prior_fix_and_use_query_sector_as_origin(self):
        self.engine.record_records("sent_messages", [
            {"id": "query-old", "createdAt": "2026-09-12T10:00:00Z", "recipient": {"type": "planet", "id": "oracle-planet"}, "sector": {"relative": {"x": 0, "y": 0, "z": 0}}, "body": "Alice"},
            {"id": "query-new", "createdAt": "2026-09-13T10:00:00Z", "recipient": {"type": "planet", "id": "oracle-planet"}, "sector": {"relative": {"x": 10, "y": 0, "z": 0}}, "body": "Alice"},
        ])
        self.engine.record_records("messages", [
            {"id": "reply-old", "createdAt": "2026-09-12T10:01:00Z", "sender": {"type": "planet", "id": "oracle-planet"}, "body": "Approximate normalized direction vector 1, 0, 0. FCC distance 4."},
            {"id": "reply-new", "createdAt": "2026-09-13T10:01:00Z", "sender": {"type": "planet", "id": "oracle-planet"}, "body": "Approximate normalized direction vector 0, 1, 0. FCC distance 6."},
        ], probe_id=7)

        contacts = MessagingService(self.engine).oracle_contacts()

        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["playerName"], "Alice")
        self.assertEqual(contacts[0]["origin"], {"x": 10, "y": 0, "z": 0})
        self.assertEqual(contacts[0]["replyMessageId"], "reply-new")
        self.assertTrue(contacts[0]["approximate"])

    def test_oracle_contacts_ignore_uncorrelated_planet_narrative(self):
        self.engine.record_records("messages", [{
            "id": "story", "createdAt": "2026-09-13T10:01:00Z",
            "sender": {"type": "planet", "id": "another-planet"},
            "body": "The direction vector is 1, 0, 0 and distance is 6.",
        }], probe_id=7)

        self.assertEqual(MessagingService(self.engine).oracle_contacts(), ())

    def test_all_exploration_templates_exist(self):
        names = (
            "frontier_exploration", "destination_explorer", "resource_search",
            "investigation", "rescue_and_recovery",
        )
        self.assertTrue(all(OperationFactory.create(name).steps for name in names))

    def test_route_scoring_rewards_discovery_and_penalizes_hazards(self):
        service = ExplorationService(build_operations())
        a = SectorCoordinates(1, 1, 0)
        b = SectorCoordinates(2, 0, 0)
        safe = service.score_route((a, b), fuel_sectors=(b,))
        risky = service.score_route((a, b), hazards={a: ("collision",)})

        self.assertGreater(safe.score, risky.score)
        self.assertEqual(len(service.search_corridor(b, radius=1)), 13)

    def test_interruption_preserves_original_operation_for_resume(self):
        service = ExplorationService(build_operations())
        original = OperationFactory.create("frontier_exploration", probe_id=1).activate()

        paused, investigation = service.interrupt(
            original, {"id": "alert-2"}, requires_investigation=True
        )

        self.assertEqual(paused.state.value, "paused")
        self.assertEqual(investigation.metadata["interruptsOperationId"], original.id)
        self.assertEqual(service.resume(paused).state.value, "active")


if __name__ == "__main__":
    unittest.main()
