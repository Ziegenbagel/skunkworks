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


def test_failed_craft_mines_reported_dependency_and_continues_cycle():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.capabilities = SimpleNamespace()
    service.data_engine = SimpleNamespace()
    craft = PreparedCommand(Command(
        CommandType.MANNY_CRAFT, 7, {"recipe": "manny"}, "craft", 1,
        target_id="manny-a",
    ), "ready")
    mine = PreparedCommand(Command(
        CommandType.MANNY_MINE, 7,
        {"objectId": "ice-1", "resources": ["deuterium"], "targetAmount": 0.55},
        "mine rejected dependency", 1, target_id="manny-b",
    ), "ready")
    queues = iter(((craft,), (craft,), ()))
    service.automation_view = lambda probe_id=None: setattr(
        service, "_prepared_commands", next(queues)
    ) or {}
    service._refresh_operations = lambda probe_id: None
    service._prepare_dependency_mining = lambda resource, policy: mine

    class Runtime:
        def __init__(self, **kwargs):
            pass

        def execute(self, prepared, **kwargs):
            if prepared.command.type == CommandType.MANNY_CRAFT:
                return ExecutionResult("failed", prepared.command, response={
                    "detail": {"error": {"code": "insufficient_deuterium"}}
                })
            return ExecutionResult("succeeded", prepared.command, response={"accepted": True})

    policy = ExecutionPolicy(
        mode=ExecutionMode.AUTOMATIC,
        live_execution_enabled=True,
        allowed_command_types=frozenset({CommandType.MANNY_CRAFT, CommandType.MANNY_MINE}),
        max_commands_per_cycle=10,
    )
    with patch("src.ui.controller.AutomationRuntime", Runtime):
        result = service._run_replanning_automatic_cycle(policy)

    assert len(result["results"]) == 2
    assert result["results"][0]["status"] == "failed"
    assert result["results"][1]["status"] == "succeeded"
    assert service._missing_resource_from_failure(
        ExecutionResult("failed", craft.command, response={
            "detail": {"error": {"code": "insufficient_deuterium"}}
        })
    ) == "deuterium"


def test_failed_recipe_is_not_retried_on_another_manny_before_mining_fallback():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.capabilities = SimpleNamespace()
    service.data_engine = SimpleNamespace()
    craft_a = PreparedCommand(Command(
        CommandType.MANNY_CRAFT, 7, {"recipe": "scut_relay"}, "craft", 1,
        target_id="manny-a",
    ), "ready")
    craft_b = PreparedCommand(Command(
        CommandType.MANNY_CRAFT, 7, {"recipe": "scut_relay"}, "craft", 1,
        target_id="manny-b",
    ), "ready")
    mine = PreparedCommand(Command(
        CommandType.MANNY_MINE, 7,
        {"objectId": "metal-1", "resources": ["metals"], "targetAmount": 0.25},
        "use remaining idle manny", 2, target_id="manny-b",
    ), "ready")
    queues = iter(((craft_a,), (craft_b,), ()))
    service.automation_view = lambda probe_id=None: setattr(
        service, "_prepared_commands", next(queues)
    ) or {}
    service._refresh_operations = lambda probe_id: None
    fallbacks = iter((mine, None))
    service._prepare_next_cycle_mining = lambda policy, attempted: next(fallbacks)

    class Runtime:
        def __init__(self, **kwargs):
            pass

        def execute(self, prepared, **kwargs):
            status = "failed" if prepared.command.type == CommandType.MANNY_CRAFT else "succeeded"
            return ExecutionResult(status, prepared.command)

    policy = ExecutionPolicy(
        mode=ExecutionMode.AUTOMATIC,
        live_execution_enabled=True,
        allowed_command_types=frozenset({CommandType.MANNY_CRAFT, CommandType.MANNY_MINE}),
        max_commands_per_cycle=10,
    )
    with patch("src.ui.controller.AutomationRuntime", Runtime):
        result = service._run_replanning_automatic_cycle(policy)

    assert [item["status"] for item in result["results"]] == ["failed", "succeeded"]
