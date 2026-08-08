from types import SimpleNamespace
from unittest.mock import patch

from src.execution import Command, CommandType, ExecutionMode, ExecutionPolicy, PreparedCommand
from src.execution.runtime import ExecutionResult
from src.ui.controller import MissionControlDataService


def test_automatic_cycle_replans_after_each_successful_order():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.capabilities = SimpleNamespace()
    service.data_engine = SimpleNamespace()
    craft = PreparedCommand(Command(
        CommandType.MANNY_CRAFT, 7, {"recipe": "scut_relay"}, "craft", 1,
        target_id="manny-a",
    ), "ready")
    mine = PreparedCommand(Command(
        CommandType.MANNY_MINE, 7,
        {"objectId": "ice-1", "resources": ["deuterium"], "targetAmount": 0.55},
        "restore missing input", 1, target_id="manny-b",
    ), "ready")
    queues = iter(((craft,), (mine,), ()))
    service.automation_view = lambda probe_id=None: setattr(
        service, "_prepared_commands", next(queues)
    ) or {}
    refreshes = []
    service._refresh_operations = lambda probe_id: refreshes.append(probe_id)

    class Runtime:
        def __init__(self, **kwargs):
            pass

        def execute(self, prepared, **kwargs):
            return ExecutionResult("succeeded", prepared.command, response={"accepted": True})

    policy = ExecutionPolicy(
        mode=ExecutionMode.AUTOMATIC,
        live_execution_enabled=True,
        allowed_command_types=frozenset({CommandType.MANNY_CRAFT, CommandType.MANNY_MINE}),
        max_commands_per_cycle=10,
    )
    with patch("src.ui.controller.AutomationRuntime", Runtime):
        result = service._run_replanning_automatic_cycle(policy)

    assert result["status"] == "succeeded"
    assert len(result["results"]) == 2
    assert refreshes == [7, 7]
    assert "freshly replanned" in result["message"]
