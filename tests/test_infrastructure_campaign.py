"""Behavioral tests for infrastructure sites, resupply, and command boundaries."""
import json
import time
from types import SimpleNamespace

from src.models.galaxy import GalaxyMap, SectorCoordinates as P
from src.operations.infrastructure import (RelayCampaignService, HubCampaignService,
    command_blockers, infrastructure_blockers, validate_settings)
from src.execution.commands import Command, CommandType as C
from src.execution.translator import TaskCommandTranslator
from src.execution.dispatcher import CapabilityDispatcher
from src.planner.task import Task
import pytest


def operations(items=(), *, here=P(0,0,0), local=(), stars=(P(2,0,0), P(-2,0,0)), role="relay_placement", settings=None, attached=()):
    probe = {"id":1, "status":"idle", "inventory":{"items":list(items)}, "sector":{"relative":vars(here)}}
    sector = {"objects":[{"type":"star", "id":"star"}, *local]}
    counts = {}
    for item in items:
        counts[item["type"]] = counts.get(item["type"], 0) + item.get("quantity", 1)
    record = {"asset_id":"1", "role":role, "metadata_json":json.dumps(settings or {})}
    return SimpleNamespace(
        world=SimpleNamespace(probe=probe, sector=sector, mannies={"mannies":[]},
            fleet={"probes":[{"id":2, "status":"idle", "sector":{"relative":vars(here)}}]},
            hazard_context={"scutNetworks":[{"network":{"relays":[{
                "id":1, "status":"on", "sector":{"relative":{"x":0,"y":0,"z":0}}, "coverageRadiusSectors":2}]}}]}),
        manufacturing=SimpleNamespace(available_inputs=lambda: ({}, counts)),
        travel=SimpleNamespace(current_sector=lambda: here, route_to=lambda target: (target,)),
        travel_safety=SimpleNamespace(scut_route_covered=lambda origin, hops: True),
        galaxy=SimpleNamespace(known_sectors=lambda: [SimpleNamespace(coordinates=p, observed={"objects":[{"type":"star"}]}) for p in stars]),
        mining=SimpleNamespace(idle_mannies=lambda: [{"id":"worker"}]),
        containers=SimpleNamespace(attached=lambda: attached, detached=lambda: (),
            free_capacity=lambda c: c.get("freeCapacity", 1)),
        data_engine=SimpleNamespace(fleet_roles=lambda _: [record], action_was_successful=lambda _: False,
            get_preference=lambda *_: json.dumps({"at":time.time(),"sector":vars(here),"containerCount":1,"safeLimit":4,"freeCapacity":5})),
    )


def settings(**extra):
    return {"infrastructureEnabled":True, "home":{"x":0,"y":0,"z":0},
            "expansionMode":"auto", "beaconMode":"final", "relayStock":2, **extra}


def kit(relays=2, beacons=1):
    return [{"id":f"r{i}", "type":"scut_relay"} for i in range(relays)] + [
        {"id":f"c{i}", "type":"integrated_circuit"} for i in range(relays)] + [
        {"id":f"b{i}", "type":"scut_transit_beacon"} for i in range(beacons)]


def test_auto_scores_live_fcc_coverage_and_direction_excludes_wrong_side():
    ops = operations(kit())
    automatic = RelayCampaignService(ops).decide(settings())
    assert automatic.destination in {P(2,0,0), P(-2,0,0)}
    directional = RelayCampaignService(ops).decide(settings(expansionMode="direction", direction={"x":-10,"y":0,"z":0}))
    assert directional.destination == P(-2,0,0)
    ops.travel_safety.scut_route_covered = lambda *_: False
    assert RelayCampaignService(ops).decide(settings()).phase == "waiting_for_sites"


def test_signal_uses_alert_direction_without_inventing_source_distance():
    alert = {"type":"anomaly_detected", "sector":{"relative":{"x":20,"y":-10,"z":6}},
             "message":"The signal originates from the approximative direction -50 25 -15 relative to the current position. Distance unknown."}
    result = RelayCampaignService.signal_direction([alert])
    assert result == {"origin":{"x":20,"y":-10,"z":6}, "vector":{"x":-50,"y":25,"z":-15}}
    assert RelayCampaignService(operations(kit())).decide(settings(expansionMode="signal")).phase == "signal_missing"


@pytest.mark.parametrize("mode,relays,expected", [("final",2,False),("final",1,True),("every",2,True),("none",1,False)])
def test_beacon_choice_is_fixed_for_each_selected_site(mode,relays,expected):
    result = RelayCampaignService(operations(kit(relays))).decide(settings(beaconMode=mode))
    assert result.state["placeBeacon"] is expected


def test_relay_campaign_deploys_activates_and_waits_for_live_beacon_completion():
    target = P(2,0,0)
    state = {"target":vars(target), "placeBeacon":True, "cycle":0}
    config = settings(infrastructureCampaign=state)
    result = RelayCampaignService(operations(kit(1),here=target)).decide(config)
    assert result.tasks[0].action == "Deploy SCUT Relay"
    config["infrastructureCampaign"] = result.state
    remaining = [i for i in kit(1) if i["type"] != "scut_relay"]
    def at_site(local=()):
        ops = operations(remaining,here=target,local=local)
        ops.data_engine.action_was_successful = lambda fingerprint: fingerprint == config["infrastructureCampaign"].get("deployFingerprint")
        return ops
    result = RelayCampaignService(at_site()).decide(config)
    assert result.phase == "deploying" and not result.tasks
    relay = {"id":9,"type":"scut_relay","status":"off"}
    result = RelayCampaignService(at_site([relay])).decide(config)
    assert result.tasks[0].action == "Activate SCUT Relay"
    config["infrastructureCampaign"] = result.state
    relay = {**relay,"status":"on"}
    result = RelayCampaignService(at_site([relay])).decide(config)
    assert result.tasks[0].action == "Install SCUT Beacon"
    relay["isTransitBeacon"] = True
    result = RelayCampaignService(at_site([relay])).decide(config)
    assert result.phase == "site_complete" and not result.tasks
    assert result.state["completedSites"] == [vars(target)]


def test_empty_stock_returns_home_then_requests_missing_kit_and_resumes():
    config = settings()
    result = RelayCampaignService(operations(here=P(2,0,0))).decide(config)
    assert result.destination == P(0,0,0)
    config["infrastructureCampaign"] = result.state
    result = RelayCampaignService(operations()).decide(config)
    assert result.phase == "restocking"
    assert result.state["supplyRequest"]["items"] == {"scut_relay":2,"integrated_circuit":2,"scut_transit_beacon":1}
    config["infrastructureCampaign"] = result.state
    result = RelayCampaignService(operations(kit())).decide(config)
    assert result.phase == "restocked" and "supplyRequest" not in result.state


def test_hub_loads_output_and_handoff_uses_live_container_not_manny_transfer():
    request = {"id":"batch-1","targetProbeId":2,"items":{"scut_relay":1}}
    config = {"infrastructureEnabled":True,"outputRequest":request}
    container = {"id":"box","kind":"container","capacity":1,"usedCapacity":0,"freeCapacity":1}
    ops = operations(kit(1),role="hub",settings=config,attached=[container])
    result = HubCampaignService(ops).decide(config)
    assert result.tasks[0].action == "Load Hub Output"
    config["infrastructureCampaign"] = result.state
    ops.world.probe["inventory"]["items"][0]["container"] = {"id":"box"}
    result = HubCampaignService(ops).decide(config)
    assert result.tasks[0].action == "Deliver Hub Container"
    assert result.tasks[0].metadata["mode"] == "attach_to_probe"
    command = TaskCommandTranslator(ops,1).translate(result.tasks[0])
    assert command.payload == {"containerId":"box","mode":"attach_to_probe","objectId":"2"}
    assert command.fingerprint == result.state["delivery"]["dispatchFingerprint"]
    config["infrastructureCampaign"] = result.state
    ops.containers.attached = lambda: ()
    assert HubCampaignService(ops).decide(config).phase == "container_missing"
    ops.data_engine.action_was_successful = lambda _: True
    result = HubCampaignService(ops).decide(config)
    assert result.phase == "delivered" and result.state["completedRequests"] == ["batch-1"]


def test_hub_refuses_container_with_unrelated_cargo():
    config = {"infrastructureEnabled":True, "infrastructureCampaign":{"delivery":{
        "id":"batch", "targetProbeId":2,"items":{"scut_relay":1},"containerId":"box"}}}
    items = [{"id":"r","type":"scut_relay","container":{"id":"box"}},
             {"id":"extra","type":"steel_bar","container":{"id":"box"}}]
    result = HubCampaignService(operations(items,role="hub",attached=[{"id":"box"}])).decide(config)
    assert result.phase == "cargo_conflict" and not result.tasks


def test_hub_accepts_home_restock_request_and_does_not_mine_resources():
    config = {"infrastructureEnabled":True}
    rows = [{"role":"relay_placement","asset_id":"2", "settings":settings(infrastructureCampaign={
        "supplyRequest":{"id":"supply-1", "items":{"scut_relay":2}}})}]
    result = HubCampaignService(operations(role="hub")).decide(config,rows)
    assert result.production["scut_relay"] == 2
    assert not any(t.action == "Mine Resource" for t in result.tasks)


def test_preflight_rejects_stale_relay_item_and_disabled_role():
    ops = operations(settings={})
    command = Command(C.DEPLOY_SCUT_RELAY,1,{"itemId":"missing"},"test",1,
                      metadata={"relayCampaign":True,"expectedSector":{"x":2,"y":0,"z":0}})
    assert set(command_blockers(ops,command)) >= {"relay_item_unavailable","infrastructure_role_disabled","infrastructure_wrong_sector"}


def test_infrastructure_mutations_have_stable_identity_across_workers():
    ops = operations()
    task = Task(action="Activate SCUT Relay", target="9", reason="test", metadata={"relayCampaign":True}, idempotency_scope="site-1")
    first = TaskCommandTranslator(ops,1).translate(task)
    ops.mining.idle_mannies = lambda: [{"id":"other"}]
    second = TaskCommandTranslator(ops,1).translate(task)
    assert first.fingerprint == second.fingerprint
    calls = []
    dispatcher = CapabilityDispatcher(SimpleNamespace(mannies=SimpleNamespace(start_task=lambda *args: calls.append(args))))
    dispatcher.dispatch(second)
    assert calls == [(1,"other","turn-on-relay",{"relayId":9})]


def test_settings_reject_invalid_direction_and_forbidden_output():
    with pytest.raises(ValueError):
        validate_settings("relay_placement",settings(expansionMode="direction",direction={"x":0,"y":0,"z":0}))
    with pytest.raises(ValueError):
        validate_settings("hub",{"infrastructureEnabled":True,"outputRequest":{"id":"a","targetProbeId":2,"items":{"manny":1}}})


def test_hub_does_not_deliver_above_receiver_safe_container_limit():
    config = {"infrastructureEnabled":True,"outputRequest":{"id":"batch","targetProbeId":2,"items":{"scut_relay":1}}}
    ops = operations(kit(1),role="hub")
    ops.data_engine.get_preference = lambda *_: json.dumps({"at":time.time(),"sector":{"x":0,"y":0,"z":0},"containerCount":4,"safeLimit":4,"freeCapacity":5})
    result = HubCampaignService(ops).decide(config)
    assert result.phase == "receiver_container_limit" and not result.tasks


def test_receiver_unloads_then_returns_only_confirmed_empty_container(tmp_path):
    from src.data import DataEngine
    from src.operations.hub_receiving import HubReceivingService, stage_receipt, receipt_blockers, receipts
    engine = DataEngine(tmp_path / "receiving.sqlite")
    ops = operations([{"id":"relay","type":"scut_relay","containerSpace":.1,"container":{"id":"supply"}}],
                     attached=[{"id":"supply","usedCapacity":.1,"freeCapacity":.9}])
    ops.data_engine = engine
    ops.travel_safety.additional_container_count = lambda: len(ops.containers.attached())
    ops.travel_safety.container_break_threshold = lambda: 5
    ops.world.probe["inventory"]["containers"] = [{"id":"core","kind":"core","freeCapacity":1}, *ops.containers.attached()]
    stage_receipt(engine,2,1,"supply","batch-1",{"x":0,"y":0,"z":0},"accepted-handoff")
    service = HubReceivingService(ops)
    result = service.reconcile()
    assert result.phase == "unloading_supply"
    assert result.tasks[0].metadata["toContainerId"] == "core"
    command = TaskCommandTranslator(ops,1).translate(result.tasks[0])
    assert not command_blockers(ops,command)
    assert not receipt_blockers(ops,command)
    move = Command(C.MOVE_PROBE,1,{"target":{"x":2,"y":0,"z":0}},"travel",2)
    assert receipt_blockers(ops,move) == ("hub_container_return_pending",)
    ops.world.probe["inventory"]["items"][0]["container"] = {"id":"core"}
    assert service.reconcile().phase == "receipt_empty_wait"
    ops.containers.attached = lambda: [{"id":"supply","usedCapacity":0,"freeCapacity":1}]
    result = service.reconcile()
    assert result.tasks[0].action == "Return Hub Container"
    command = TaskCommandTranslator(ops,1).translate(result.tasks[0])
    assert command.payload == {"containerId":"supply","mode":"drifting"}
    assert not receipt_blockers(ops,command)
    saved = receipts(engine,1)[0]
    assert saved.metadata["returnFingerprint"] == command.fingerprint
    ops.world.probe["inventory"]["items"][0]["container"] = {"id":"supply"}
    assert receipt_blockers(ops,command) == ("hub_return_container_not_empty",)
    ops.world.probe["inventory"]["items"][0]["container"] = {"id":"core"}
    ops.containers.attached = lambda: []
    engine.action_was_successful = lambda _: True
    assert service.reconcile().phase == "receipt_complete"
    assert not receipts(engine,1)
    assert not receipt_blockers(ops,move)


def test_receiver_never_discards_stock_when_permanent_storage_is_full(tmp_path):
    from src.data import DataEngine
    from src.operations.hub_receiving import HubReceivingService, stage_receipt
    engine = DataEngine(tmp_path / "full.sqlite")
    ops = operations([{"id":"relay","type":"scut_relay","containerSpace":.1,"container":{"id":"supply"}}],
                     attached=[{"id":"supply","usedCapacity":.1,"freeCapacity":.9}])
    ops.data_engine = engine
    ops.travel_safety.additional_container_count = lambda: 1
    ops.travel_safety.container_break_threshold = lambda: 5
    ops.world.probe["inventory"]["containers"] = [{"id":"core","kind":"core","freeCapacity":0}, *ops.containers.attached()]
    stage_receipt(engine,2,1,"supply","batch-1",{"x":0,"y":0,"z":0},"accepted-handoff")
    result = HubReceivingService(ops).reconcile()
    assert result.phase == "receipt_capacity_hold" and not result.tasks


def test_partial_hub_batch_keeps_remaining_items_after_accepted_handoff():
    request = {"id":"batch-1","targetProbeId":2,"items":{"scut_relay":2}}
    config = {"infrastructureEnabled":True,"infrastructureCampaign":{"delivery":{**request,"containerId":"box"}}}
    items = [{"id":"r1","type":"scut_relay","containerSpace":.75,"container":{"id":"box"}}]
    ops = operations(items,role="hub",attached=[{"id":"box","usedCapacity":.75,"freeCapacity":.25}])
    result = HubCampaignService(ops).decide(config)
    assert result.tasks[0].action == "Deliver Hub Container"
    config["infrastructureCampaign"] = result.state
    ops.containers.attached = lambda: []
    ops.data_engine.action_was_successful = lambda _: True
    result = HubCampaignService(ops).decide(config)
    assert result.state["delivery"]["items"] == {"scut_relay":1}
    assert result.state["delivery"]["shipment"] == 1


def test_hub_recovers_returned_packaging_even_with_general_receiving_disabled(tmp_path):
    from dataclasses import replace
    from src.data import DataEngine
    from src.operations.hub_receiving import stage_receipt
    from src.operations.mission import OperationStore, OperationState
    engine = DataEngine(tmp_path / "returns.sqlite")
    stage_receipt(engine,1,2,"box","batch-1",{"x":0,"y":0,"z":0},"handoff")
    store = OperationStore(engine)
    receipt = store.all()[0]
    store.save(replace(receipt,state=OperationState.COMPLETED))
    ops = operations(role="hub")
    ops.data_engine = engine
    ops.containers.detached = lambda: [{"id":"detached-container-box","containerId":"box","mode":"drifting"}]
    result = HubCampaignService(ops).decide({"infrastructureEnabled":True,"receiveContainers":False})
    assert result.phase == "recovering_return"
    assert result.tasks[0].target == "detached-container-box"
    assert result.tasks[0].idempotency_scope == receipt.id+":recover"


def test_receiver_cancels_unsent_receipt_if_hub_is_disabled(tmp_path):
    from src.data import DataEngine
    from src.operations.hub_receiving import HubReceivingService, stage_receipt, receipts
    engine = DataEngine(tmp_path / "cancel.sqlite")
    engine.assign_fleet_role("probe",2,"hub",metadata={"infrastructureEnabled":False})
    ops = operations()
    ops.data_engine = engine
    ops.travel_safety.additional_container_count = lambda: 0
    ops.travel_safety.container_break_threshold = lambda: 5
    stage_receipt(engine,2,1,"box","batch",{"x":0,"y":0,"z":0},"unaccepted")
    assert HubReceivingService(ops).reconcile().phase == "receipt_cancelled"
    assert not receipts(engine,1)


def test_hub_builds_surplus_intermediate_instead_of_spending_delivery_kit():
    ops = operations([{"id":"c","type":"integrated_circuit"}],role="hub")
    ops.manufacturing.production_plan = lambda recipe,**_: {"consumed_inventory_items":{"integrated_circuit":1} if recipe == "scut_relay" else {}}
    assert HubCampaignService(ops).production_targets({"scut_relay":1,"integrated_circuit":1}) == {"scut_relay":1,"integrated_circuit":2}
