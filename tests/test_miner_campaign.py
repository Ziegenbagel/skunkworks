from types import SimpleNamespace
import json

from src.operations.miner_campaign import MinerCampaignService
from src.models.galaxy import SectorCoordinates
from src.planner.desired_state import DesiredState, TravelGoal
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


def test_miner_reserves_one_manny_and_caps_workers_at_four():
    target = {"id": "asteroid-1", "resource_type": "deuterium", "available_amount": 500}
    decision = MinerCampaignService(operations(resources=[target])).decide({
        "miningEnabled": True, "resourceMode": "deuterium", "maximumMiningMannies": 4,
    })
    assert decision.phase == "mining"
    assert len(decision.tasks) == 2
    assert [task.quantity for task in decision.tasks] == [80, 25]


def test_miner_never_claims_last_idle_manny():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    decision = MinerCampaignService(operations(idle=1, resources=[target])).decide({
        "miningEnabled": True, "resourceMode": "resources",
    })
    assert decision.tasks == ()
    assert decision.phase == "logistics_reserve"


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
