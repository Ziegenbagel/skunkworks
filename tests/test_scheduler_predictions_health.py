import unittest
from datetime import UTC, datetime, timedelta

from src.application.scheduler import RefreshScheduler
from src.operations.health import OperationalHealthService
from src.operations.predictions import PredictionService
from tests.test_planner_missions import build_operations


class SchedulerPredictionHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 31, tzinfo=UTC)

    def test_scheduler_honors_hint_and_prioritizes_focus(self):
        scheduler = RefreshScheduler(focused_probe_id=1, now=lambda: self.now)
        focus = scheduler.schedule("probe", probe_id=1, next_useful_refresh_delay_ms=1000)
        background = scheduler.schedule("probe", probe_id=2, next_useful_refresh_delay_ms=1000)

        self.assertEqual(focus.due_at, self.now + timedelta(seconds=1))
        self.assertGreater(focus.priority, background.priority)
        self.assertEqual(scheduler.due(self.now + timedelta(seconds=1))[0], focus)

    def test_mutation_invalidates_related_domains_immediately(self):
        scheduler = RefreshScheduler(focused_probe_id=1, now=lambda: self.now)

        requests = scheduler.invalidate_after_mutation(1)

        self.assertEqual(len(requests), 3)
        self.assertTrue(all(request.reason == "mutation" for request in requests))

    def test_predictions_expose_basis_confidence_and_drift(self):
        service = PredictionService(build_operations(), now=lambda: self.now)
        prediction = service.resource_exhaustion("metals", 20, 5)
        drift = service.drift(service.fleet_metrics()[1], 40)

        self.assertEqual(prediction.value, self.now + timedelta(hours=4))
        self.assertEqual(prediction.assumptions, ("mining rate remains constant",))
        self.assertEqual(drift.absolute_error, 10)

    def test_health_surfaces_stale_fuel_and_inventory_bottlenecks(self):
        operations = build_operations(fuel=10, free_capacity=0.5)
        operations.world.snapshot["fresh"] = False
        health = OperationalHealthService(operations).assess()

        codes = {finding.code for finding in health.findings}
        self.assertEqual(health.state, "degraded")
        self.assertIn("stale_snapshot", codes)
        self.assertIn("low_fuel", codes)
        self.assertIn("inventory_saturation", codes)


if __name__ == "__main__":
    unittest.main()
