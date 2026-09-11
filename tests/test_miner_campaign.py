from types import SimpleNamespace
import json

from src.operations.miner_campaign import MinerCampaignService
from src.models.galaxy import SectorCoordinates
from src.planner.desired_state import DesiredState, TravelGoal
from src.execution import CommandPreparer, CommandType, ExecutionMode, ExecutionPolicy
from src.planner.task import Task
from tests.test_planner_missions import build_operations
from src.ui.controller import MissionControlDataService


def operations(*, idle=5, resources=None, fuel=20, maximum=100, capacity=4):
    mannies = [{"id": f"manny-{index}", "currentTask": None, "canReceiveOrders": True}
               for index in range(idle)]
    targets = resources or []
    return SimpleNamespace(
        mining=SimpleNamespace(
            idle_mannies=lambda: mannies,
            active_commitments=lambda: {},
            best_target=lambda resource: next(
                (item for item in targets if item["resource_type"] == resource), None),
        ),
        inventory=SimpleNamespace(mining_return_capacity=lambda _active: capacity),
        world=SimpleNamespace(probe={"fuel": {"deuterium": fuel, "maxDeuterium": maximum},
                                    "sector": {"relative": {"x": 1, "y": 2, "z": 3}}}),
    )


def test_deuterium_miner_uses_all_needed_mannies_while_tank_has_capacity():
    target = {"id": "asteroid-1", "resource_type": "deuterium", "available_amount": 500}
    decision = MinerCampaignService(operations(resources=[target])).decide({
        "miningEnabled": True, "resourceMode": "deuterium", "maximumMiningMannies": 4,
    }, maximum_mining_order_amount=0.25)
    assert decision.phase == "mining"
    assert len(decision.tasks) == 4
    assert [task.quantity for task in decision.tasks] == [80, 55, 30, 5]


def test_ordinary_resource_miner_can_use_its_only_idle_manny():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    decision = MinerCampaignService(operations(idle=1, resources=[target])).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"],
    })
    assert len(decision.tasks) == 1
    assert decision.tasks[0].resource_type == "metals"


def test_all_resources_selects_fuel_and_enabled_ordinary_resources():
    targets = [
        {"id": "d", "resource_type": "deuterium", "available_amount": 500},
        {"id": "m", "resource_type": "metals", "available_amount": 10},
    ]
    decision = MinerCampaignService(operations(resources=targets)).decide({
        "miningEnabled": True, "resourceMode": "all",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
    })
    assert decision.managed_resources == ("deuterium", "metals")
    assert {task.resource_type for task in decision.tasks} == {"deuterium", "metals"}


def test_full_deuterium_miner_transfers_to_selected_same_sector_probe():
    target = {
        "id": 9, "sector": {"relative": {"x": 1, "y": 2, "z": 3}},
        "fuel": {"deuterium": 20, "maxDeuterium": 100},
    }
    decision = MinerCampaignService(operations(fuel=100)).decide({
        "miningEnabled": True, "resourceMode": "deuterium",
        "deuteriumTransportProbeId": 9,
    }, target_probe=target)
    assert len(decision.tasks) == 1
    assert decision.tasks[0].action == "Transfer Deuterium"
    assert decision.tasks[0].quantity == 80
    assert decision.tasks[0].category == "miner_logistics"
    assert decision.reserve_transfer_manny is True


def test_full_miner_reserved_manny_is_used_by_transfer_not_other_work():
    miner_operations = build_operations()
    miner_operations.world.mannies["mannies"] = [
        {
            "id": f"manny-{index}", "currentTask": None,
            "canReceiveOrders": True, "location": {"type": "probe"},
        }
        for index in range(2)
    ]
    tasks = (
        Task(
            action="Repair Probe", category="safety", quantity=10, priority=1,
            reason="Unrelated Manny work must not consume the transfer reserve.",
        ),
        Task(
            action="Transfer Deuterium", category="miner_logistics", target="9",
            quantity=80, priority=1, workflow_authorized=True,
            reason="Transfer full Miner fuel.", metadata={"minerCampaign": True},
        ),
    )
    prepared = CommandPreparer(
        miner_operations, 1,
        ExecutionPolicy(
            mode=ExecutionMode.AUTOMATIC, live_execution_enabled=True,
            allowed_command_types=frozenset({
                CommandType.MANNY_TRANSFER_DEUTERIUM, CommandType.MANNY_REPAIR,
            }),
            max_commands_per_cycle=10,
        ),
        reserved_manny_ids=("manny-0",),
    ).prepare(tasks)

    commands = {item.command.type: item.command for item in prepared}
    assert commands[CommandType.MANNY_TRANSFER_DEUTERIUM].target_id == "manny-0"
    assert commands[CommandType.MANNY_TRANSFER_DEUTERIUM].metadata["minerCampaign"] is True
    assert commands[CommandType.MANNY_REPAIR].target_id == "manny-1"


def test_full_deuterium_miner_sends_nine_of_ten_mannies_to_waiting_mining():
    resource = {
        "id": "deuterium-asteroid", "resource_type": "deuterium",
        "available_amount": 6498,
    }
    decision = MinerCampaignService(
        operations(idle=10, resources=[resource], fuel=400, maximum=400)
    ).decide({
        "miningEnabled": True, "resourceMode": "deuterium",
        "deuteriumTransportProbeId": 9,
    }, target_probe={
        "id": 9, "sector": {"relative": {"x": 9, "y": 8, "z": -1}},
        "fuel": {"deuterium": 0, "maxDeuterium": 400},
    }, maximum_mining_order_amount=0.25)

    assert len(decision.tasks) == 9
    assert all(task.action == "Mine Resource" for task in decision.tasks)
    assert all(task.maximum_order_amount == 0.25 for task in decision.tasks)
    assert "One Manny is reserved" in decision.summary


def test_deuterium_miner_can_use_all_ten_mannies_before_tank_is_full():
    resource = {
        "id": "deuterium-asteroid", "resource_type": "deuterium",
        "available_amount": 6498,
    }
    decision = MinerCampaignService(
        operations(idle=10, resources=[resource], fuel=0, maximum=400)
    ).decide({
        "miningEnabled": True, "resourceMode": "deuterium",
    }, maximum_mining_order_amount=0.25)

    assert len(decision.tasks) == 10
    assert all(task.action == "Mine Resource" for task in decision.tasks)


def test_full_tank_reports_rendezvous_instead_of_missing_resource():
    target = {
        "id": 9, "sector": {"relative": {"x": 2, "y": 2, "z": -2}},
        "fuel": {"deuterium": 20, "maxDeuterium": 100},
    }
    decision = MinerCampaignService(operations(fuel=100)).decide({
        "miningEnabled": True, "resourceMode": "deuterium",
        "deuteriumTransportProbeId": 9,
    }, target_probe=target)

    assert decision.phase == "tank_full_awaiting_rendezvous"
    assert "full at 100/100 ECE" in decision.summary
    assert "rendezvous" in decision.summary


def test_unconfigured_ordinary_resources_default_to_unchecked_and_unmanaged():
    decision = MinerCampaignService(operations()).decide({
        "miningEnabled": True, "resourceMode": "resources",
    })

    assert decision.managed_resources == ()
    assert decision.tasks == ()


def test_enabled_miner_suppresses_ordinary_travel_without_mutating_saved_goal():
    desired = DesiredState(travel=TravelGoal(SectorCoordinates(4, 5, 5)))
    engine = SimpleNamespace(fleet_roles=lambda _kind: ({
        "asset_id": "7", "role": "miner",
        "metadata_json": json.dumps({"miningEnabled": True}),
    },))
    service = MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine = engine
    miner_operations = operations(idle=1)
    miner_operations.world.fleet = {"probes": []}

    projected, _tasks, view = service._reconcile_miner_campaign(
        miner_operations, 7, desired,
    )

    assert projected.travel is None
    assert desired.travel.target == SectorCoordinates(4, 5, 5)
    assert view["travelLocked"] is True


def test_controller_accepts_available_receiver_without_exact_transport_role():
    engine = SimpleNamespace(fleet_roles=lambda _kind: ({
        "asset_id": "7", "role": "miner",
        "metadata_json": json.dumps({
            "miningEnabled": True, "resourceMode": "deuterium",
            "deuteriumTransportProbeId": 9,
        }),
    },))
    service = MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine = engine
    miner_operations = operations(idle=2, fuel=100)
    miner_operations.world.fleet = {"probes": [{
        "id": 9, "role": "unassigned",
        "sector": {"relative": {"x": 1, "y": 2, "z": 3}},
        "fuel": {"deuterium": 0, "maxDeuterium": 100},
    }]}

    _desired, tasks, _view = service._reconcile_miner_campaign(
        miner_operations, 7, DesiredState(),
    )

    assert len(tasks) == 1
    assert tasks[0].action == "Transfer Deuterium"
    assert tasks[0].target == "9"
