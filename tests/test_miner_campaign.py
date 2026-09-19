from types import SimpleNamespace
import json

from src.operations.miner_campaign import MinerCampaignService
from src.models.galaxy import SectorCoordinates
from src.planner.desired_state import DesiredState, TravelGoal
from src.execution import CommandPreparer, CommandType, ExecutionMode, ExecutionPolicy
from src.planner.task import Task
from tests.test_planner_missions import build_operations
from src.ui.controller import MissionControlDataService


def operations(*, idle=5, resources=None, fuel=20, maximum=100, capacity=4,
               attached=None, detached=None, active_mannies=None):
    mannies = [{"id": f"manny-{index}", "currentTask": None, "canReceiveOrders": True}
               for index in range(idle)]
    all_mannies = list(active_mannies or ()) + mannies
    targets = resources or []
    return SimpleNamespace(
        mining=SimpleNamespace(
            idle_mannies=lambda: mannies,
            active_commitments=lambda: {},
            best_target=lambda resource: next(
                (item for item in targets if item["resource_type"] == resource), None),
        ),
        inventory=SimpleNamespace(mining_return_capacity=lambda _active: capacity),
        containers=SimpleNamespace(
            attached=lambda: tuple(attached or ()),
            detached=lambda: tuple(detached or ()),
            free_capacity=lambda item: float(
                item.get("freeCapacity", item.get("capacity", 0)) or 0
            ) - (0 if "freeCapacity" in item else float(
                item.get("usedCapacity", item.get("used", 0)) or 0
            )),
        ),
        mannies=SimpleNamespace(
            all=lambda: tuple(all_mannies),
            _task_type=lambda manny: (
                (manny.get("currentTask") or {}).get("type")
                if isinstance(manny.get("currentTask"), dict)
                else manny.get("currentTask")
            ),
        ),
        world=SimpleNamespace(probe={
            "id": 1, "model": "deuterium_tanker", "status": "idle",
            "fuel": {"deuterium": fuel, "maxDeuterium": maximum},
            "sector": {"relative": {"x": 1, "y": 2, "z": 3}},
        }, mannies={"mannies": all_mannies}),
    )


def test_deuterium_miner_uses_all_needed_mannies_while_tank_has_capacity():
    target = {"id": "asteroid-1", "resource_type": "deuterium", "available_amount": 500}
    decision = MinerCampaignService(operations(resources=[target])).decide({
        "miningEnabled": True, "resourceMode": "deuterium", "maximumMiningMannies": 4,
    }, maximum_mining_order_amount=0.25)
    assert decision.phase == "mining"
    assert len(decision.tasks) == 4
    assert [task.quantity for task in decision.tasks] == [80, 55, 30, 5]


def test_ordinary_resource_miner_deploys_empty_container_before_mining():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    decision = MinerCampaignService(operations(
        idle=1, resources=[target],
        attached=[{"id": "box-1", "kind": "container", "usedCapacity": 0}],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"],
    })
    assert len(decision.tasks) == 1
    assert decision.tasks[0].action == "Deploy Miner Container"
    assert decision.tasks[0].target == "box-1"
    assert decision.tasks[0].metadata["objectId"] == "asteroid-1"
    assert decision.campaign_state["phase"] == "deploy_container"


def test_ordinary_miner_reselects_live_empty_container_after_saved_one_disappears():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    miner_operations = operations(
        resources=[target],
        attached=[
            {"id": f"live-box-{index}", "kind": "container", "usedCapacity": 0}
            for index in range(4)
        ],
    )
    miner_operations.manufacturing = SimpleNamespace(
        recipes=SimpleNamespace(get=lambda recipe: (
            {"id": recipe, "craftableBy": ["manny"]}
            if recipe == "additional_container" else None
        )),
        active_production_count=lambda _recipe: 0,
    )

    decision = MinerCampaignService(miner_operations).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "minimumEmptyContainers": 10,
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "old-asteroid",
            "containerId": "missing-box", "phase": "deploy_container",
        },
    })

    assert decision.phase == "deploy_container"
    assert decision.tasks[0].action == "Deploy Miner Container"
    assert decision.tasks[0].target == "live-box-0"
    assert decision.campaign_state == {
        "resourceType": "metals", "asteroidId": "asteroid-1",
        "containerId": "live-box-0", "phase": "deploy_container",
    }
    assert "Deploying an empty container" in decision.summary
    assert "reserve replenishment" in decision.summary


def test_ordinary_miner_keeps_missing_container_pointer_while_task_is_active():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    active = [{
        "id": "working-manny", "canReceiveOrders": False,
        "currentTask": {
            "type": "detach_container",
            "payload": {"containerId": "in-flight-box"},
        },
    }]
    decision = MinerCampaignService(operations(
        idle=1, resources=[target], active_mannies=active,
        attached=[{"id": "other-box", "kind": "container", "usedCapacity": 0}],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"],
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "asteroid-1",
            "containerId": "in-flight-box", "phase": "deploy_container",
        },
    })

    assert decision.tasks == ()
    assert decision.campaign_state["containerId"] == "in-flight-box"
    assert "deployment to complete" in decision.summary


def test_ordinary_resource_miner_sends_four_quarter_ece_orders_to_deployed_container():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    decision = MinerCampaignService(operations(
        idle=6, resources=[target],
        detached=[{
            "id": "box-1", "type": "detached_container",
            "mode": "hidden_on_asteroid", "targetObjectId": "asteroid-1",
            "capacity": 1, "usedCapacity": 0,
        }],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "asteroid-1",
            "containerId": "box-1", "phase": "deploy_container",
        },
    })

    assert decision.phase == "mine_container"
    assert len(decision.tasks) == 4
    assert all(task.action == "Mine Resource" for task in decision.tasks)
    assert all(task.quantity == 0.25 for task in decision.tasks)
    assert all(task.maximum_order_amount == 0.25 for task in decision.tasks)
    assert all(task.metadata["targetContainerId"] == "box-1"
               for task in decision.tasks)


def test_deployed_container_wrapper_id_advances_campaign_and_routes_live_id():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    decision = MinerCampaignService(operations(
        idle=4, resources=[target],
        detached=[{
            "id": "detached-container-box-1", "containerId": "box-1",
            "type": "detached_container", "mode": "hidden_on_asteroid",
            "targetObjectId": "asteroid-1", "capacity": 1,
            "usedCapacity": 0,
        }],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "asteroid-1",
            "containerId": "box-1", "phase": "deploy_container",
        },
    })

    assert decision.phase == "mine_container"
    assert len(decision.tasks) == 4
    assert all(task.action == "Mine Resource" for task in decision.tasks)
    assert all(task.metadata["targetContainerId"] == "detached-container-box-1"
               for task in decision.tasks)


def test_active_container_miner_does_not_block_remaining_worker_slots():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    active = [{
        "id": "working-manny", "canReceiveOrders": False,
        "currentTask": {
            "type": "mining",
            "payload": {
                "objectId": "asteroid-1",
                "targetContainerId": "detached-container-box-1",
            },
        },
    }]
    decision = MinerCampaignService(operations(
        idle=6, resources=[target], active_mannies=active,
        detached=[{
            "id": "detached-container-box-1", "containerId": "box-1",
            "type": "detached_container", "mode": "hidden_on_asteroid",
            "targetObjectId": "asteroid-1", "capacity": 1,
            "usedCapacity": 0,
        }],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "asteroid-1",
            "containerId": "box-1", "phase": "mine_container",
        },
    })

    assert decision.phase == "mine_container"
    assert len(decision.tasks) == 3
    assert all(
        task.metadata["targetContainerId"] == "detached-container-box-1"
        for task in decision.tasks
    )
    assert "1 already active" in decision.summary


def test_accepted_quarter_fills_recover_container_without_capacity_telemetry():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    live_id = "detached-container-box-1"
    decision = MinerCampaignService(operations(
        idle=4, resources=[target],
        detached=[{
            "id": live_id, "containerId": "box-1",
            "type": "detached_container", "mode": "hidden_on_asteroid",
            "targetObjectId": "asteroid-1", "capacity": 1,
        }],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "asteroid-1",
            "containerId": "box-1", "phase": "mine_container",
        },
    }, accepted_container_fills={live_id: 1.0})

    assert decision.phase == "recover_container"
    assert len(decision.tasks) == 1
    assert decision.tasks[0].action == "Recover Miner Container"
    assert decision.tasks[0].target == live_id


def test_accepted_partial_fills_only_schedule_uncovered_slots():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    live_id = "detached-container-box-1"
    decision = MinerCampaignService(operations(
        idle=4, resources=[target],
        detached=[{
            "id": live_id, "containerId": "box-1",
            "type": "detached_container", "mode": "hidden_on_asteroid",
            "targetObjectId": "asteroid-1", "capacity": 1,
        }],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "asteroid-1",
            "containerId": "box-1", "phase": "mine_container",
        },
    }, accepted_container_fills={live_id: 0.5})

    assert decision.phase == "mine_container"
    assert len(decision.tasks) == 2
    assert all(task.metadata["targetContainerId"] == live_id
               for task in decision.tasks)


def test_ten_mannies_run_two_parallel_container_campaigns():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    decision = MinerCampaignService(operations(
        idle=10, resources=[target],
        detached=[
            {
                "id": f"detached-container-box-{index}",
                "containerId": f"box-{index}",
                "type": "detached_container", "mode": "hidden_on_asteroid",
                "targetObjectId": "asteroid-1", "capacity": 1,
                "usedCapacity": 0,
            }
            for index in (1, 2)
        ],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
        "ordinaryContainerCampaign": {"campaigns": [
            {
                "resourceType": "metals", "asteroidId": "asteroid-1",
                "containerId": f"box-{index}", "phase": "mine_container",
            }
            for index in (1, 2)
        ]},
    })

    mining = [task for task in decision.tasks if task.action == "Mine Resource"]
    assert decision.phase == "parallel_container_campaigns"
    assert len(mining) == 8
    assert {
        task.metadata["targetContainerId"] for task in mining
    } == {"detached-container-box-1", "detached-container-box-2"}
    assert len(decision.campaign_state["campaigns"]) == 2
    assert decision.reserve_ordinary_mannies == 8


def test_parallel_campaigns_reserve_only_complete_groups():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    active = [
        {
            "id": f"working-{container}-{index}", "canReceiveOrders": False,
            "currentTask": {
                "type": "mining",
                "payload": {
                    "objectId": "asteroid-1",
                    "targetContainerId": f"detached-container-{container}",
                },
            },
        }
        for container in ("box-1", "box-2") for index in range(4)
    ]
    decision = MinerCampaignService(operations(
        idle=2, resources=[target], active_mannies=active,
        detached=[
            {
                "id": f"detached-container-{container}",
                "containerId": container, "type": "detached_container",
                "mode": "hidden_on_asteroid", "targetObjectId": "asteroid-1",
                "capacity": 1, "usedCapacity": 0,
            }
            for container in ("box-1", "box-2")
        ],
    )).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
        "ordinaryContainerCampaign": {"campaigns": [
            {
                "resourceType": "metals", "asteroidId": "asteroid-1",
                "containerId": container, "phase": "mine_container",
            }
            for container in ("box-1", "box-2")
        ]},
    })

    assert decision.tasks == ()
    assert decision.reserve_ordinary_mannies == 0
    assert "2 parallel container campaigns" in decision.summary


def test_deploy_phase_adopts_different_live_container_anchored_by_game():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    miner_operations = operations(
        idle=4, resources=[target],
        attached=[{"id": "requested-box", "kind": "container", "usedCapacity": 0}],
        detached=[{
            "id": "detached-container-actual-box", "containerId": "actual-box",
            "type": "detached_container", "mode": "hidden_on_asteroid",
            "targetObjectId": "asteroid-1", "capacity": 1,
            "freeCapacity": 1, "usedCapacity": 0,
        }],
    )

    decision = MinerCampaignService(miner_operations).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "asteroid-1",
            "containerId": "requested-box", "phase": "deploy_container",
        },
    })

    assert decision.phase == "mine_container"
    assert len(decision.tasks) == 4
    assert all(task.action == "Mine Resource" for task in decision.tasks)
    assert all(
        task.metadata["targetContainerId"] == "detached-container-actual-box"
        for task in decision.tasks
    )
    assert decision.campaign_state["containerId"] == "actual-box"


def test_full_ordinary_container_is_recovered_then_released_to_drift():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 9}
    settings = {
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"],
        "ordinaryContainerCampaign": {
            "resourceType": "metals", "asteroidId": "asteroid-1",
            "containerId": "box-1", "phase": "mine_container",
        },
    }
    recovery = MinerCampaignService(operations(
        resources=[target], detached=[{
            "id": "box-1", "type": "detached_container",
            "mode": "hidden_on_asteroid", "targetObjectId": "asteroid-1",
            "capacity": 1, "usedCapacity": 1,
        }],
    )).decide(settings)
    assert recovery.phase == "recover_container"
    assert recovery.tasks[0].action == "Recover Miner Container"
    assert recovery.tasks[0].metadata["source"] == "asteroid"

    release_settings = {
        **settings,
        "ordinaryContainerCampaign": {
            **recovery.campaign_state, "phase": "recover_container",
        },
    }
    release = MinerCampaignService(operations(
        resources=[target], attached=[{
            "id": "box-1", "kind": "container", "capacity": 1,
            "usedCapacity": 1,
        }],
    )).decide(release_settings)
    assert release.phase == "release_container"
    assert release.tasks[0].action == "Release Miner Container"
    assert release.tasks[0].metadata["mode"] == "drifting"

    complete_settings = {
        **settings,
        "ordinaryContainerCampaign": release.campaign_state,
    }
    complete = MinerCampaignService(operations(
        resources=[target], detached=[{
            "id": "box-1", "type": "drifting_container",
            "mode": "drifting", "capacity": 1,
            "contents": {"metals": 1},
        }],
    )).decide(complete_settings)
    assert complete.phase == "container_ready_for_transport"
    assert complete.tasks == ()
    assert complete.campaign_state == {}


def test_all_resources_selects_fuel_and_enabled_ordinary_resources():
    targets = [
        {"id": "d", "resource_type": "deuterium", "available_amount": 500},
        {"id": "m", "resource_type": "metals", "available_amount": 10},
    ]
    decision = MinerCampaignService(operations(
        resources=targets,
        attached=[{"id": "box-1", "kind": "container", "usedCapacity": 0}],
    )).decide({
        "miningEnabled": True, "resourceMode": "all",
        "ordinaryResources": ["metals"], "maximumMiningMannies": 4,
    })
    assert decision.managed_resources == ("deuterium", "metals")
    assert any(task.resource_type == "deuterium" for task in decision.tasks)
    assert any(task.action == "Deploy Miner Container" for task in decision.tasks)


def test_full_deuterium_miner_transfers_to_selected_same_sector_probe():
    target = {
        "id": 9, "status": "idle",
        "sector": {"relative": {"x": 1, "y": 2, "z": 3}},
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


def test_ordinary_miner_crafts_its_configured_empty_container_reserve():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    miner_operations = operations(resources=[target])
    miner_operations.manufacturing = SimpleNamespace(
        recipes=SimpleNamespace(get=lambda recipe: (
            {"id": recipe, "craftableBy": ["manny"]}
            if recipe == "additional_container" else None
        )),
        active_production_count=lambda _recipe: 0,
    )

    decision = MinerCampaignService(miner_operations).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "minimumEmptyContainers": 3,
    })

    assert len(decision.tasks) == 1
    task = decision.tasks[0]
    assert task.action == "Craft Item"
    assert task.target == "additional_container"
    assert task.quantity == 3
    assert task.workflow_authorized is True
    assert task.metadata["emptyContainerReserve"] is True


def test_active_container_crafting_counts_toward_miner_reserve():
    target = {"id": "asteroid-1", "resource_type": "metals", "available_amount": 10}
    miner_operations = operations(
        resources=[target],
        attached=[{"id": "empty-1", "kind": "container", "usedCapacity": 0}],
    )
    miner_operations.manufacturing = SimpleNamespace(
        recipes=SimpleNamespace(get=lambda recipe: (
            {"id": recipe, "craftableBy": ["manny"]}
            if recipe == "additional_container" else None
        )),
        active_production_count=lambda _recipe: 1,
    )

    decision = MinerCampaignService(miner_operations).decide({
        "miningEnabled": True, "resourceMode": "resources",
        "ordinaryResources": ["metals"], "minimumEmptyContainers": 2,
    })

    assert not any(task.metadata.get("emptyContainerReserve")
                   for task in decision.tasks)


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
        "status": "idle",
        "sector": {"relative": {"x": 1, "y": 2, "z": 3}},
        "fuel": {"deuterium": 0, "maxDeuterium": 100},
    }]}

    _desired, tasks, _view = service._reconcile_miner_campaign(
        miner_operations, 7, DesiredState(),
    )

    assert len(tasks) == 1
    assert tasks[0].action == "Transfer Deuterium"
    assert tasks[0].target == "9"


def test_controller_uses_live_receiver_after_cached_fleet_sector_lags():
    engine = SimpleNamespace(fleet_roles=lambda _kind: ({
        "asset_id": "805.0", "role": "miner",
        "metadata_json": json.dumps({
            "miningEnabled": True, "resourceMode": "deuterium",
            "deuteriumTransportProbeId": "9.0",
        }),
    },))
    service = MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine = engine
    service.client = SimpleNamespace(get_probe=lambda _probe_id: {"probe": {
        "id": 9, "status": "idle",
        "sector": {"relative": {"x": 1, "y": 2, "z": 3}},
        "fuel": {"deuterium": 20, "maxDeuterium": 100},
    }})
    miner_operations = operations(idle=2, fuel=100)
    miner_operations.world.probe["id"] = 805
    miner_operations.world.fleet = {"probes": [{
        "id": 9, "status": "idle",
        "sector": {"relative": {"x": 8, "y": 8, "z": 8}},
        "fuel": {"deuterium": 20, "maxDeuterium": 100},
    }]}

    _desired, tasks, view = service._reconcile_miner_campaign(
        miner_operations, "805.0", DesiredState(),
    )

    assert view["reserveTransferManny"] is True
    assert len(tasks) == 1
    assert tasks[0].action == "Transfer Deuterium"
    assert tasks[0].target == "9"
    assert tasks[0].quantity == 80
