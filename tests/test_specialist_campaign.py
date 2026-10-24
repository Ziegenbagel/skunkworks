"""Combat opt-in, bounded firing, cargo ownership and restart invariants."""
import json
from types import SimpleNamespace

import pytest

from tests.test_infrastructure_campaign import operations, P
from src.operations.specialist_campaign import SpecialistCampaignService, command_blockers, validate_settings
from src.execution.translator import TaskCommandTranslator
from src.execution.dispatcher import CapabilityDispatcher


def setup(role="missile_destroyer", items=(), here=P(2,0,0), local=(), attached=()):
    config = {"infrastructureEnabled":True, "combatAuthorized":True,
              "home":vars(P(0,0,0)), "hubProbeId":2, "targetSector":vars(P(2,0,0)),
              "missionId":"mission-1", "missileStock":2}
    ops = operations(items, here=here, local=local, role=role, settings=config, attached=attached)
    ops.world.sector.update(knowledgeLevel="detailed", sensorMode="normal")
    ops.world.probe["inventory"]["freeCapacity"] = 1
    ops.travel_safety.additional_container_count = lambda: len(attached)
    ops.travel_safety.container_break_threshold = lambda: 5
    values, accepted = {}, set()
    old_read = ops.data_engine.get_preference
    ops.data_engine.get_preference = lambda k,d="{}":values.get(k, old_read(k,d))
    ops.data_engine.set_preference = lambda k,v:values.update({k:v})
    ops.data_engine.action_was_successful = lambda fp:fp in accepted
    ops.data_engine.fleet_roles = lambda _: [{"asset_id":"1", "role":role,"metadata_json":json.dumps(config)}]
    return ops, config, values, accepted


def step(ops, config, role="missile_destroyer"):
    result = SpecialistCampaignService(ops).decide(role, config)
    config["infrastructureCampaign"] = result.state
    return result


def test_destroyer_dispatches_exact_public_target_and_waits_across_restart():
    ammo = [{"id":"missile-1","type":"missile"},{"id":"missile-2","type":"missile"}]
    ops, cfg, values, accepted = setup(items=ammo, local=[{"id":"opaque-ship","type":"others_ship"},{"id":"friendly","type":"probe"}])
    result = step(ops, cfg)
    command = TaskCommandTranslator(ops,1).translate(result.tasks[0])
    assert command.payload == {"missileItemId":"missile-1", "targetId":"opaque-ship"}
    assert command.fingerprint == result.state["launch"]["fingerprint"]
    assert not command_blockers(ops,command)
    calls = []
    CapabilityDispatcher(SimpleNamespace(probes=SimpleNamespace(launch_missile=lambda *args:calls.append(args)))).dispatch(command)
    assert calls == [(1,"worker","missile-1","opaque-ship")]
    accepted.add(command.fingerprint)
    assert step(ops,cfg).phase == "missile_pending"
    values["specialist_missile:"+command.fingerprint] = json.dumps({"missile":{"status":"launched","impactAt":"2000-01-01"}})
    assert not step(ops,cfg).tasks  # an expired ETA is not completion
    values["specialist_missile:"+command.fingerprint] = json.dumps({"missile":{"status":"resolved","result":"missed"}})
    ops.world.probe["inventory"]["items"].pop(0)
    next_result = step(ops,cfg)
    assert next_result.tasks[0].target == "missile-2"
    assert next_result.state["sequence"] == 1
    assert not command_blockers(ops,TaskCommandTranslator(ops,1).translate(next_result.tasks[0]))


def test_destroyer_stops_after_last_accepted_missile_then_refills_without_repeating():
    ops,cfg,values,accepted = setup(items=[{"id":"last","type":"missile"}],local=[{"id":"ship","type":"others_ship"}])
    shot = step(ops,cfg)
    command = TaskCommandTranslator(ops,1).translate(shot.tasks[0])
    assert not command_blockers(ops,command)
    accepted.add(command.fingerprint)
    values["specialist_missile:"+command.fingerprint] = json.dumps({"missile":{"status":"resolved","details":{"destroyed":True}}})
    ops.world.probe["inventory"]["items"] = []
    returning = step(ops,cfg)
    assert returning.destination == P(0,0,0)
    assert returning.state["supplyRequest"]["items"] == {"missile":2}
    ops.travel.current_sector = lambda: P(0,0,0)
    assert step(ops,cfg).phase == "restocking"
    ops.world.probe["inventory"]["items"] = [{"id":"new","type":"missile","quantity":2}]
    assert step(ops,cfg).phase == "ready"
    assert not step(ops,cfg).tasks
    cfg["missionId"] = "mission-2"
    assert step(ops,cfg).destination == P(2,0,0)


def test_destroyer_revalidates_authorization_target_and_sensor_absence():
    ops,cfg,_,_ = setup(items=[{"id":"m","type":"missile"}],local=[{"id":"ship","observedClass":"ship"}])
    result=step(ops,cfg); command=TaskCommandTranslator(ops,1).translate(result.tasks[0])
    cfg["combatAuthorized"] = False
    assert command_blockers(ops,command)
    cfg["combatAuthorized"] = True
    ops.world.sector["objects"] = []
    ops.world.sector["sensorMode"] = "degraded"
    assert step(ops,cfg).phase == "sensor_hold"
    assert command_blockers(ops,command)
    ops.world.sector["sensorMode"] = "normal"
    result=step(ops,cfg)
    assert result.destination == P(0,0,0)
    assert not result.state.get("destroyed")


def test_salvage_ignores_claimed_containers_and_respects_safe_limit():
    box={"id":"detached-container-box","type":"detached_container","salvageable":True,"mode":"drifting"}
    ops,cfg,_,_=setup("salvage",local=[box])
    own=ops.data_engine.fleet_roles
    ops.data_engine.fleet_roles=lambda x:own(x)+[{"asset_id":"3","role":"miner","metadata_json":json.dumps({"ordinaryContainerCampaign":{"containerId":"box"}})}]
    assert not step(ops,cfg,"salvage").tasks
    ops.data_engine.fleet_roles=own
    ops.travel_safety.additional_container_count=lambda:4
    assert step(ops,cfg,"salvage").phase == "capacity_hold"
    ops.travel_safety.additional_container_count=lambda:0
    result=step(ops,cfg,"salvage")
    command=TaskCommandTranslator(ops,1).translate(result.tasks[0])
    assert command.fingerprint == result.state["pickup"]["fingerprint"]
    assert not command_blockers(ops,command)
    ops.world.sector["objects"] = []
    assert command_blockers(ops,command)


def test_salvage_returns_recovered_container_to_hub_without_shipping_original_storage():
    boxes=[{"id":"own","usedCapacity":0}]
    ops,cfg,values,accepted=setup("salvage",attached=boxes,
        local=[{"id":"detached-container-found","type":"detached_container","salvageable":True}])
    picked=step(ops,cfg,"salvage")
    accepted.add(picked.state["pickup"]["fingerprint"])
    assert step(ops,cfg,"salvage").phase == "recovering"
    boxes.append({"id":"found","usedCapacity":.5})
    assert step(ops,cfg,"salvage").destination == P(0,0,0)
    ops.travel.current_sector=lambda:P(0,0,0)
    import time
    values["hub_receiving:2"]=json.dumps({"at":time.time(),"sector":vars(P(0,0,0)),"status":"idle","freeCapacity":4})
    delivery=step(ops,cfg,"salvage")
    command=TaskCommandTranslator(ops,1).translate(delivery.tasks[0])
    assert command.payload == {"containerId":"found","mode":"attach_to_probe","objectId":"2"}
    assert not command_blockers(ops,command)
    boxes.pop()
    ops.world.sector["objects"]=[]
    assert not step(ops,cfg,"salvage").tasks
    assert cfg["infrastructureCampaign"]["baselineContainers"] == ["own"]


def test_salvage_loose_items_pack_before_delivery_and_preserve_identity():
    boxes=[{"id":"own","usedCapacity":0,"freeCapacity":1}]
    ops,cfg,values,accepted=setup("salvage",attached=boxes,
        local=[{"id":"drop","type":"drifting_item","salvageable":True}])
    pick=step(ops,cfg,"salvage");accepted.add(pick.state["pickup"]["fingerprint"])
    item={"id":"recovered","type":"steel_bar","containerSpace":.02,"container":{"id":"probe-core"}}
    ops.world.probe["inventory"]["items"]=[item]
    step(ops,cfg,"salvage")
    ops.travel.current_sector=lambda:P(0,0,0)
    import time
    values["hub_receiving:2"]=json.dumps({"at":time.time(),"sector":vars(P(0,0,0)),"status":"idle","freeCapacity":4})
    pack=step(ops,cfg,"salvage")
    command=TaskCommandTranslator(ops,1).translate(pack.tasks[0])
    assert pack.tasks[0].action == "Load Hub Output"
    assert not command_blockers(ops,command)
    item["container"]={"id":"own"};boxes[0]["usedCapacity"]=.02
    assert step(ops,cfg,"salvage").tasks[0].action == "Deliver Salvage Container"


def test_specialist_validation_requires_explicit_combat_and_valid_home():
    with pytest.raises(ValueError):
        validate_settings("missile_destroyer",{"infrastructureEnabled":True,"home":vars(P(0,0,0)),"hubProbeId":2})


def test_hub_collects_destroyer_refills_only_for_the_selected_hub():
    from src.operations.infrastructure import HubCampaignService
    ops=operations(role="hub",attached=[{"id":"box","usedCapacity":0}])
    row={"asset_id":"3","role":"missile_destroyer","settings":{
        "infrastructureEnabled":True,"hubProbeId":1,"home":vars(P(0,0,0)),
        "infrastructureCampaign":{"supplyRequest":{"id":"refill","items":{"missile":10}}}}}
    result=HubCampaignService(ops).decide({"infrastructureEnabled":True},[row])
    assert result.production["missile"] == 10
    row["settings"]["hubProbeId"]=2
    assert not HubCampaignService(ops).decide({"infrastructureEnabled":True},[row]).packages


def test_missile_response_is_durable_before_success_and_blocks_replay(tmp_path):
    from src.data import DataEngine
    from src.execution.runtime import AutomationRuntime
    from src.execution.policy import ExecutionPolicy
    ops,cfg,values,_=setup(items=[{"id":"m","type":"missile"}],local=[{"id":"ship","type":"others_ship"}])
    result=step(ops,cfg); command=TaskCommandTranslator(ops,1).translate(result.tasks[0])
    engine=DataEngine(tmp_path / "flight.sqlite")
    response={"missile":{"id":"public-flight","status":"preparing"}}
    runtime=AutomationRuntime(capabilities=None,data_engine=engine,policy=ExecutionPolicy(),
        dispatcher=SimpleNamespace(dispatch=lambda _:response),refresh=lambda _:None)
    assert runtime._dispatch_with_retry(command).status == "succeeded"
    assert json.loads(engine.get_preference("specialist_launch:"+command.fingerprint,"{}")) == response
    assert engine.action_was_successful(command.fingerprint)
    # Even if journal confirmation was interrupted after saving the response,
    # the accepted public missile identity must prevent a second launch.
    values["specialist_launch:"+command.fingerprint]=json.dumps(response)
    assert step(ops,cfg).phase == "missile_pending"


def test_legacy_builder_support_is_retired_without_reassigning_live_assets():
    from src.operations.logistics import FleetRoleService
    row={"asset_id":"7","role":"builder_support","metadata_json":"{}"}
    service=FleetRoleService(SimpleNamespace(fleet_roles=lambda _:[row]))
    assert service.all("probe")[0]["role"] == "unassigned"
    assert row["role"] == "builder_support"
    assert "builder_support" not in service.VALID_ROLES
    assert {"salvage","missile_destroyer"} <= service.VALID_ROLES


@pytest.mark.parametrize("role", ["salvage","missile_destroyer"])
def test_specialist_roles_do_not_inherit_bulk_production_or_mining(tmp_path, role):
    from unittest.mock import patch
    from dataclasses import replace
    from src.data import DataEngine
    from src.planner.desired_state import DesiredState, ResourceGoal, ProductionGoal
    from src.planner.desired_state_store import DesiredStateStore
    from src.ui.controller import MissionControlDataService
    from src.operations.infrastructure import InfrastructureDecision
    from tests.test_planner_missions import build_operations
    from src.execution.commands import CommandType as C
    ops=build_operations(metals=0); ops.world.fleet={"probes":[]}
    engine=ops.data_engine=DataEngine(tmp_path / "specialist.sqlite")
    cfg={"infrastructureEnabled":True,"combatAuthorized":True,"home":vars(P(0,0,0)),"hubProbeId":2,"missileStock":2}
    engine.assign_fleet_role("probe",1,role,metadata=cfg)
    desired=replace(DesiredState.unconfigured(),resources=(ResourceGoal("metals",100),),production=(ProductionGoal("storage_container",10),))
    DesiredStateStore(engine).save(desired,1)
    service=MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine=engine;service.recipes=ops.manufacturing.recipes
    service._apply_probe_role_goals=lambda desired,*_:desired
    service._reconcile_completed_autonomous_travel=lambda _ops,_id,desired:desired
    service._reconcile_transport_operation=lambda _ops,_id,desired:(desired,[],None)
    service._reserve_tanker_delivery_tasks=lambda *_:[]
    service._reconcile_explorer_campaign=lambda _ops,_id,desired:(desired,[],{})
    service._reconcile_miner_campaign=lambda _ops,_id,desired:(desired,[],{})
    service._dependency_mining_idle_grace_elapsed=lambda _:True
    with patch("src.operations.hub_receiving.HubReceivingService.reconcile",return_value=InfrastructureDecision("","")):
        service.automation_view(ops,1)
    assert not any(p.command.type in {C.MANNY_MINE,C.MANNY_CRAFT,C.ATOMIC_PRINTER_CRAFT} for p in service._prepared_commands)
    assert DesiredStateStore(engine).load(1).resources == desired.resources
    assert DesiredStateStore(engine).load(1).production == desired.production


def test_destroyer_intercepts_before_offense_and_does_not_duplicate_after_restart():
    threat={"id":"incoming","type":"missile","targetsCurrentProbe":True,"status":"moving"}
    ops,cfg,values,accepted=setup(items=[{"id":"a","type":"missile"},{"id":"b","type":"missile"}],
                                 local=[threat,{"id":"ship","type":"others_ship"}])
    result=step(ops,cfg)
    assert result.phase == "intercepting"
    command=TaskCommandTranslator(ops,1).translate(result.tasks[0])
    assert command.payload == {"missileItemId":"a","targetId":"incoming"}
    assert not command_blockers(ops,command)
    values["specialist_launch:"+command.fingerprint]=json.dumps({"missile":{"id":"interceptor","status":"preparing"}})
    assert step(ops,cfg).phase == "defending"
    cfg["missionId"]="new-mission"
    assert not step(ops,cfg).tasks
    threat["targetsCurrentProbe"]=False
    assert command_blockers(ops,command)


def test_destroyer_defends_during_offensive_flight_and_prioritizes_earliest_threat():
    ops,cfg,values,accepted=setup(items=[{"id":"a","type":"missile"},{"id":"b","type":"missile"}],local=[{"id":"ship","type":"others_ship"}])
    shot=step(ops,cfg)
    accepted.add(shot.state["launch"]["fingerprint"])
    ops.world.sector["objects"] += [
        {"id":"later","type":"missile","targetsCurrentProbe":True,"impactAt":"2030-01-01T01:00:00Z"},
        {"id":"earlier","type":"missile","targetsCurrentProbe":True,"impactAt":"2030-01-01T00:00:00Z"}]
    defense=step(ops,cfg)
    assert defense.tasks[0].target == "b"
    assert defense.tasks[0].metadata["targetId"] == "earlier"
    assert defense.state["launch"] == shot.state["launch"]
    assert not command_blockers(ops,TaskCommandTranslator(ops,1).translate(defense.tasks[0]))


def test_destroyer_does_not_intercept_other_targets_or_without_consent():
    threat={"id":"incoming","type":"missile","targetsCurrentProbe":False}
    ops,cfg,_,_=setup(items=[{"id":"a","type":"missile"}],local=[threat])
    assert step(ops,cfg).phase != "intercepting"
    threat["targetsCurrentProbe"]=True
    cfg["combatAuthorized"]=False
    assert not step(ops,cfg).tasks
    cfg["combatAuthorized"]=True
    ops.world.probe["inventory"]["items"]=[]
    assert step(ops,cfg).phase == "defense_hold"


def test_specialist_status_reports_planner_and_execution_holds():
    from src.ui.controller import MissionControlDataService
    from src.planner.task import Task
    from src.execution.commands import Command, CommandType
    from src.execution.preparer import PreparedCommand
    ops,_,_,_=setup()
    view={"phase":"traveling","summary":"Traveling to combat sector.","enabled":True}
    task=Task(action="Prepare Probe Travel",reason="",category="travel",constraints=("owned_mannies_not_aboard",))
    status=MissionControlDataService._specialist_execution_status(view,[task],[],ops)
    assert status["phase"] == "execution_hold"
    assert "owned mannies not aboard" in status["summary"]
    command=Command(CommandType.MOVE_PROBE,1,{},"",1)
    warning=SimpleNamespace(message="9 containers; safe maximum 4.",acknowledgement_recommended=True)
    for disposition, text in [("awaiting_risk_acknowledgement","9 containers"),("dry_run","live execution disabled"),("awaiting_approval","approval is required")]:
        result=MissionControlDataService._specialist_execution_status(view,[],[PreparedCommand(command,disposition,warnings=(warning,))],ops)
        assert result["phase"] == "execution_hold"
        assert text in result["summary"]
    result=MissionControlDataService._specialist_execution_status(view,[],[PreparedCommand(command,"ready")],ops)
    assert result["phase"] == "ready_to_execute"
    assert "awaiting accepted execution" in result["summary"]
    assert view["phase"] == "traveling"


@pytest.mark.parametrize("role", ["salvage","missile_destroyer"])
def test_specialist_roles_preserve_selected_upgrade_work(tmp_path, role):
    from unittest.mock import patch
    from dataclasses import replace
    from src.data import DataEngine
    from src.planner.desired_state import DesiredState, ResourceGoal, ProductionGoal, UpgradeGoal
    from src.planner.desired_state_store import DesiredStateStore
    from src.ui.controller import MissionControlDataService
    from src.operations.infrastructure import InfrastructureDecision
    from tests.test_planner_missions import build_operations
    from src.execution.commands import CommandType as C
    ops=build_operations(metals=0); ops.world.fleet={"probes":[]}
    engine=ops.data_engine=DataEngine(tmp_path / "specialist.sqlite")
    cfg={"infrastructureEnabled":True,"combatAuthorized":True,"home":vars(P(0,0,0)),"hubProbeId":2,"missileStock":2}
    engine.assign_fleet_role("probe",1,role,metadata=cfg)
    ops.world.hazard_context = {"improvements":{"improvements":[{
        "id":"compression", "name":"Compression", "available":True, "done":False,
        "installableOnProbe":True, "ingredients":[{"kind":"item","type":"storage_container","quantity":2}]}]}}
    desired=replace(DesiredState.unconfigured(),upgrade=UpgradeGoal("compression","selected-upgrade"),resources=(ResourceGoal("metals",100),),production=(ProductionGoal("storage_container",10),))
    DesiredStateStore(engine).save(desired,1)
    service=MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine=engine;service.recipes=ops.manufacturing.recipes
    service._apply_probe_role_goals=lambda desired,*_:desired
    service._reconcile_completed_autonomous_travel=lambda _ops,_id,desired:desired
    service._reconcile_transport_operation=lambda _ops,_id,desired:(desired,[],None)
    service._reserve_tanker_delivery_tasks=lambda *_:[]
    service._reconcile_explorer_campaign=lambda _ops,_id,desired:(desired,[],{})
    service._reconcile_miner_campaign=lambda _ops,_id,desired:(desired,[],{})
    service._dependency_mining_idle_grace_elapsed=lambda _:True
    with patch("src.operations.hub_receiving.HubReceivingService.reconcile",return_value=InfrastructureDecision("","")):
        service.automation_view(ops,1)
    assert any(p.command.type == C.MANNY_MINE for p in service._prepared_commands)
    assert all(p.command.metadata.get("upgradeScope") == "selected-upgrade"
               for p in service._prepared_commands if p.command.type in {C.MANNY_MINE,C.MANNY_CRAFT,C.ATOMIC_PRINTER_CRAFT})
    ops.world.probe["inventory"]["resourceStocks"][0]["amount"] = 10
    with patch("src.operations.hub_receiving.HubReceivingService.reconcile",return_value=InfrastructureDecision("","")):
        service.automation_view(ops,1)
    assert any(p.command.type == C.MANNY_CRAFT for p in service._prepared_commands)
    ops.world.probe["inventory"]["items"] = [{"id":"parts","type":"storage_container","quantity":2}]
    with patch("src.operations.hub_receiving.HubReceivingService.reconcile",return_value=InfrastructureDecision("","")):
        service.automation_view(ops,1)
    assert any(p.command.type == C.MANNY_UPGRADE for p in service._prepared_commands)
    assert DesiredStateStore(engine).load(1).resources == desired.resources
    assert DesiredStateStore(engine).load(1).production == desired.production
