from types import SimpleNamespace
from unittest.mock import patch

from src.execution import Command, CommandType, ExecutionMode, ExecutionPolicy, PreparedCommand
from src.execution.runtime import ExecutionResult
from src.planner.task import Task
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
    service.automation_view = lambda probe_id=None, **kwargs: setattr(
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


def test_failed_craft_tries_next_recipe_before_mining_dependency():
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
    alternate = PreparedCommand(Command(
        CommandType.MANNY_CRAFT, 7, {"recipe": "additional_container"},
        "craft available container", 2, target_id="manny-b",
    ), "ready")
    queues = iter(((craft,), (craft, alternate), (mine,), ()))
    exclusions = []
    service.automation_view = lambda probe_id=None, **kwargs: exclusions.append(
        frozenset(kwargs.get("excluded_fabrication", ()))
    ) or setattr(
        service, "_prepared_commands", next(queues)
    ) or {}
    service._refresh_operations = lambda probe_id: None
    service._prepare_next_cycle_mining = lambda policy, failed: None
    executed = []

    class Runtime:
        def __init__(self, **kwargs):
            pass

        def execute(self, prepared, **kwargs):
            executed.append((prepared.command.type, prepared.command.payload))
            if prepared.command.payload.get("recipe") == "manny":
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

    assert len(result["results"]) == 3
    assert result["results"][0]["status"] == "failed"
    assert result["results"][1]["status"] == "succeeded"
    assert executed[1][1]["recipe"] == "additional_container"
    assert executed[2][0] == CommandType.MANNY_MINE
    assert exclusions[0] == frozenset()
    assert exclusions[1] == frozenset({"manny"})
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
    service.automation_view = lambda probe_id=None, **kwargs: setattr(
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


def test_successful_recipe_can_use_second_idle_manny_in_same_cycle():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.capabilities = SimpleNamespace()
    service.data_engine = SimpleNamespace()
    service._refresh_operations = lambda probe_id: None
    craft_a = PreparedCommand(Command(
        CommandType.MANNY_CRAFT, 7, {"recipe": "steel_plate"}, "craft plate", 1,
        target_id="manny-a",
    ), "ready")
    craft_b = PreparedCommand(Command(
        CommandType.MANNY_CRAFT, 7, {"recipe": "steel_plate"}, "craft plate", 1,
        target_id="manny-b",
    ), "ready")
    queues = iter(((craft_a,), (craft_b,), ()))
    service.automation_view = lambda probe_id=None, **kwargs: setattr(
        service, "_prepared_commands", next(queues)
    ) or {}
    service._prepare_next_cycle_mining = lambda policy, failed: None
    executed = []

    class Runtime:
        def __init__(self, **kwargs):
            pass

        def execute(self, prepared, **kwargs):
            executed.append(prepared.command.target_id)
            return ExecutionResult(
                "succeeded", prepared.command, response={"accepted": True}
            )

    policy = ExecutionPolicy(
        mode=ExecutionMode.AUTOMATIC,
        live_execution_enabled=True,
        allowed_command_types=frozenset({CommandType.MANNY_CRAFT}),
        max_commands_per_cycle=10,
    )
    with patch("src.ui.controller.AutomationRuntime", Runtime):
        result = service._run_replanning_automatic_cycle(policy)

    assert result["status"] == "succeeded"
    assert executed == ["manny-a", "manny-b"]


def test_mining_only_fallback_preserves_capacity_for_material_ready_recipe():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.data_engine = SimpleNamespace()
    service._operations = SimpleNamespace(
        mining=SimpleNamespace(idle_mannies=lambda: [object(), object()])
    )
    tasks = (
        Task(
            action="Prepare Manufacturing",
            reason="Container inputs available",
            category="manufacturing",
            target="additional_container",
            constraints=("fabricator_unavailable",),
            priority=2,
        ),
        Task(
            action="Mine Resource",
            reason="Reserve metals",
            category="mining",
            target="asteroid-1",
            resource_type="metals",
            priority=3,
        ),
    )

    with (
        patch("src.ui.controller.DesiredStateStore.load", return_value=SimpleNamespace()),
        patch("src.ui.controller.Planner") as planner,
        patch("src.ui.controller.CommandPreparer") as preparer,
    ):
        planner.return_value.tasks.return_value = tasks
        preparer.return_value.prepare.return_value = (PreparedCommand(Command(
            CommandType.MANNY_CRAFT, 7, {"recipe": "additional_container"},
            "Container inputs available", 2, target_id="manny-a",
        ), "ready"),)
        result = service._prepare_next_cycle_mining(ExecutionPolicy(), set())

    assert result is None
    assert preparer.call_count == 1


def test_dependency_mining_lookahead_waits_for_continuous_idle_grace():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.data_engine = SimpleNamespace()
    service._operations = SimpleNamespace(
        mining=SimpleNamespace(idle_mannies=lambda: [object()])
    )
    service._dependency_mining_idle_since = {7: 100.0}

    with (
        patch("src.ui.controller.time.monotonic", return_value=219.9),
        patch("src.ui.controller.DesiredStateStore.load", return_value=SimpleNamespace()),
        patch("src.ui.controller.Planner") as planner,
        patch("src.ui.controller.CommandPreparer") as preparer,
    ):
        planner.return_value.tasks.return_value = ()
        preparer.return_value.prepare.return_value = ()
        service._prepare_next_cycle_mining(ExecutionPolicy(), set())
        assert planner.call_args.kwargs["dependency_mining_lookahead"] is False

    with (
        patch("src.ui.controller.time.monotonic", return_value=220.0),
        patch("src.ui.controller.DesiredStateStore.load", return_value=SimpleNamespace()),
        patch("src.ui.controller.Planner") as planner,
        patch("src.ui.controller.CommandPreparer") as preparer,
    ):
        planner.return_value.tasks.return_value = ()
        preparer.return_value.prepare.return_value = ()
        service._prepare_next_cycle_mining(ExecutionPolicy(), set())
        assert planner.call_args.kwargs["dependency_mining_lookahead"] is True


def test_dependency_mining_idle_grace_resets_when_no_manny_is_idle():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._dependency_mining_idle_since = {7: 100.0}
    operations = SimpleNamespace(
        mining=SimpleNamespace(idle_mannies=lambda: [])
    )

    service._observe_dependency_mining_idle(7, operations)

    assert 7 not in service._dependency_mining_idle_since


def test_dependency_mining_idle_grace_survives_new_service_workers():
    MissionControlDataService._shared_dependency_mining_idle_since.clear()
    first = MissionControlDataService.__new__(MissionControlDataService)
    first._dependency_mining_idle_since = (
        MissionControlDataService._shared_dependency_mining_idle_since
    )
    second = MissionControlDataService.__new__(MissionControlDataService)
    second._dependency_mining_idle_since = (
        MissionControlDataService._shared_dependency_mining_idle_since
    )
    operations = SimpleNamespace(
        mining=SimpleNamespace(idle_mannies=lambda: [object()])
    )

    with patch("src.ui.controller.time.monotonic", return_value=100.0):
        first._observe_dependency_mining_idle(7, operations)
    with patch("src.ui.controller.time.monotonic", return_value=220.0):
        assert second._dependency_mining_idle_grace_elapsed(7) is True

    MissionControlDataService._shared_dependency_mining_idle_since.clear()


def test_unavailable_fabrication_does_not_hide_immediate_background_mining():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.data_engine = SimpleNamespace(emergency_stop_active=lambda: False)
    service._dependency_mining_idle_since = {7: 100.0}
    operations = SimpleNamespace()
    waiting = Task(
        action="Prepare Manufacturing", reason="await metal",
        category="manufacturing", target="manny", priority=1,
    )
    background_command = Command(
        CommandType.MANNY_MINE, 7,
        {"objectId": "ice", "resources": ["ice"], "targetAmount": 0.25},
        "reserve ice", 3, target_id="manny-a",
        metadata={"backgroundWork": True},
    )

    with (
        patch("src.ui.controller.time.monotonic", return_value=150.0),
        patch("src.ui.controller.ExecutionPolicyStore.load", return_value=ExecutionPolicy()),
        patch("src.ui.controller.DesiredStateStore.load", return_value=SimpleNamespace()),
        patch.object(service, "_reconcile_completed_autonomous_travel", side_effect=lambda _o, _p, d: d),
        patch.object(service, "_reconcile_transport_operation", return_value=(SimpleNamespace(), [], None)),
        patch.object(service, "_reserve_tanker_delivery_tasks", return_value=[]),
        patch("src.ui.controller.Planner") as planner,
        patch("src.ui.controller.CommandPreparer") as preparer,
    ):
        planner.return_value.tasks.return_value = [waiting]
        preparer.return_value.prepare.return_value = (
            PreparedCommand(background_command, "ready"),
        )
        view = service.automation_view(operations, 7)

    assert len(view["queue"]) == 1
    assert view["queue"][0]["metadata"]["backgroundWork"] is True


def test_authoritative_queue_enables_dependency_lookahead_after_idle_grace():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.data_engine = SimpleNamespace(emergency_stop_active=lambda: False)
    service._dependency_mining_idle_since = {7: 100.0}

    with (
        patch("src.ui.controller.time.monotonic", return_value=220.0),
        patch("src.ui.controller.ExecutionPolicyStore.load", return_value=ExecutionPolicy()),
        patch("src.ui.controller.DesiredStateStore.load", return_value=SimpleNamespace()),
        patch.object(service, "_reconcile_completed_autonomous_travel", side_effect=lambda _o, _p, d: d),
        patch.object(service, "_reconcile_transport_operation", return_value=(SimpleNamespace(), [], None)),
        patch.object(service, "_reserve_tanker_delivery_tasks", return_value=[]),
        patch("src.ui.controller.Planner") as planner,
        patch("src.ui.controller.CommandPreparer") as preparer,
    ):
        planner.return_value.tasks.return_value = []
        preparer.return_value.prepare.return_value = ()
        service.automation_view(SimpleNamespace(), 7)

    assert planner.call_args.kwargs["dependency_mining_lookahead"] is True


def test_cycle_mining_allocation_freezes_fair_share_and_caps_total_need():
    allocations = {}

    def proposal(amount):
        return PreparedCommand(Command(
            CommandType.MANNY_MINE,
            7,
            {"objectId": "ice-1", "resources": ["deuterium"], "targetAmount": amount},
            "fill bounded fuel deficit",
            1,
            target_id="manny-a",
            metadata={"requestedNeed": 0.4, "orderAmount": amount},
        ), "ready")

    first = MissionControlDataService._bound_cycle_mining_allocation(
        proposal(0.1), allocations,
    )
    allocations["deuterium"]["committed"] += first.command.payload["targetAmount"]
    accepted = [first.command.payload["targetAmount"]]
    # Simulate stale replans that divide the unchanged 0.4 deficit among fewer
    # idle Mannys and therefore propose progressively larger individual jobs.
    for amount in (0.133, 0.2, 0.4, 0.4):
        bounded = MissionControlDataService._bound_cycle_mining_allocation(
            proposal(amount), allocations,
        )
        if bounded is None:
            break
        delivered = bounded.command.payload["targetAmount"]
        accepted.append(delivered)
        allocations["deuterium"]["committed"] += delivered

    assert accepted == [0.1, 0.1, 0.1, 0.1]
    assert sum(accepted) == 0.4


def test_automatic_risk_acknowledgement_executes_the_selected_command():
    service = MissionControlDataService.__new__(MissionControlDataService)
    service._selected_probe_id = 7
    service.capabilities = SimpleNamespace()
    service.data_engine = SimpleNamespace()
    service._refresh_operations = lambda probe_id: None
    move = PreparedCommand(Command(
        CommandType.MOVE_PROBE,
        7,
        {"target": {"x": 1, "y": 0, "z": 0}},
        "next safe segmented hop",
        5,
    ), "awaiting_risk_acknowledgement", warnings=(SimpleNamespace(
        acknowledgement_recommended=True,
    ),))
    service.automation_view = lambda probe_id=None: setattr(
        service, "_prepared_commands", (move,)
    ) or {}
    executions = []

    class Runtime:
        def __init__(self, **kwargs):
            pass

        def execute(self, prepared, **kwargs):
            executions.append((prepared.command.fingerprint, kwargs))
            return ExecutionResult(
                "succeeded", prepared.command, response={"accepted": True}
            )

    policy = ExecutionPolicy(
        mode=ExecutionMode.AUTOMATIC,
        live_execution_enabled=True,
        allowed_command_types=frozenset({CommandType.MOVE_PROBE}),
    )
    with (
        patch("src.ui.controller.ExecutionPolicyStore.load", return_value=policy),
        patch("src.ui.controller.AutomationRuntime", Runtime),
    ):
        result = service.run_automation_cycle(
            move.command.fingerprint,
            risk_acknowledged=True,
        )

    assert result["status"] == "succeeded"
    assert executions == [(
        move.command.fingerprint,
        {"risk_acknowledged": True},
    )]
