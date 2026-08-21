import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.data import DataEngine
from src.execution import (
    AutomationRuntime,
    CapabilityDispatcher,
    Command,
    CommandType,
    ExecutionMode,
    ExecutionPolicy,
    PreparedCommand,
)
from src.execution.runtime import ExecutionResult
from tests.test_planner_missions import build_operations


class RecordingMannies:
    def __init__(self):
        self.calls = []

    def start_task(self, probe_id, manny_id, task, payload):
        self.calls.append((probe_id, manny_id, task, payload))
        return {"accepted": True}


class AutomationRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.engine = DataEngine(Path(self.temporary.name) / "runtime.sqlite3")
        self.mannies = RecordingMannies()
        capabilities = SimpleNamespace(
            mannies=self.mannies,
            probes=SimpleNamespace(),
        )
        self.policy = ExecutionPolicy(
            mode=ExecutionMode.APPROVE,
            live_execution_enabled=True,
            allowed_command_types=frozenset({CommandType.MANNY_CRAFT}),
        )
        self.command = Command(
            CommandType.MANNY_CRAFT,
            1,
            {"recipe": "storage_container"},
            "test",
            1,
            target_id=101,
        )
        self.prepared = PreparedCommand(self.command, "awaiting_approval")
        self.replans = []
        self.runtime = AutomationRuntime(
            capabilities=capabilities,
            data_engine=self.engine,
            policy=self.policy,
            dispatcher=CapabilityDispatcher(capabilities),
            refresh=lambda probe_id: build_operations(),
            replan=lambda probe_id, result: self.replans.append(result.status),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_approval_is_required_before_dispatch(self):
        result = self.runtime.execute(self.prepared)

        self.assertEqual(result.status, "awaiting_approval")
        self.assertEqual(self.mannies.calls, [])

    def test_approved_command_refreshes_dispatches_journals_and_replans(self):
        result = self.runtime.execute(self.prepared, approved=True)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(
            self.mannies.calls,
            [(1, 101, "craft", {"recipe": "storage_container"})],
        )
        self.assertEqual(
            [row["status"] for row in self.engine.action_history(1)],
            ["proposed", "approved", "started", "succeeded"],
        )
        self.assertEqual(self.replans, ["succeeded"])

    def test_completed_repeatable_command_can_run_again_after_fresh_preflight(self):
        first = self.runtime.execute(self.prepared, approved=True)
        second = self.runtime.execute(self.prepared, approved=True)

        self.assertEqual(first.status, "succeeded")
        self.assertEqual(second.status, "succeeded")
        self.assertEqual(len(self.mannies.calls), 2)

    def test_emergency_stop_cancels_without_dispatch(self):
        self.runtime.emergency_stop()

        result = self.runtime.execute(self.prepared, approved=True)

        self.assertEqual(result.status, "cancelled")
        self.assertEqual(result.blockers, ("emergency_stop",))
        self.assertEqual(self.mannies.calls, [])

    def test_fresh_preflight_catches_changed_probe_state(self):
        self.runtime.refresh = lambda probe_id: build_operations(status="cruising")

        result = self.runtime.execute(self.prepared, approved=True)

        self.assertEqual(result.status, "cancelled")
        self.assertIn("probe_unavailable", result.blockers)
        self.assertEqual(self.mannies.calls, [])

    def test_arrived_probe_is_stationary_and_can_dispatch_onboard_work(self):
        self.runtime.refresh = lambda probe_id: build_operations(status="arrived")

        result = self.runtime.execute(self.prepared, approved=True)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(
            self.mannies.calls,
            [(1, 101, "craft", {"recipe": "storage_container"})],
        )

    def test_cancelled_result_message_explains_fresh_preflight_blocker(self):
        from src.ui.controller import MissionControlDataService

        result = ExecutionResult(
            "cancelled", self.command, blockers=("manny_unavailable",)
        )

        self.assertEqual(
            MissionControlDataService._execution_message(result),
            "Cancelled · manny unavailable",
        )

    def test_execution_lease_prevents_parallel_probe_commands(self):
        self.assertTrue(
            self.engine.acquire_execution_lease(
                1, "first", "owner", "2999-01-01T00:00:00+00:00"
            )
        )
        self.assertFalse(
            self.engine.acquire_execution_lease(
                1, "second", "other", "2999-01-01T00:00:00+00:00"
            )
        )


if __name__ == "__main__":
    unittest.main()
