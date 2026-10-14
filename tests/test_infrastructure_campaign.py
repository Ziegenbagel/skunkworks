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


@pytest.mark.parametrize("kind", ["steel_bar", "manny", "metals"])
def test_hub_automatically_clears_unrelated_cargo_without_shipping_or_discarding_it(kind):
    config = {"infrastructureEnabled":True, "infrastructureCampaign":{"delivery":{
        "id":"package", "targetProbeId":2, "containerId":"box", "items":{"scut_relay":1}}}}
    wanted = {"id":"relay","type":"scut_relay","containerSpace":.1,"container":{"id":"box"}}
    extra = {"id":"extra","type":kind,"containerSpace":.2,"container":{"id":"box"}}
    boxes = [{"id":"box","usedCapacity":.3,"freeCapacity":.7}, {"id":"core","kind":"core","freeCapacity":.3}]
    ops = operations([wanted] + ([] if kind == "metals" else [extra]), role="hub",attached=boxes,settings=config)
    ops.world.probe["inventory"]["containers"] = boxes
    if kind == "metals":
        ops.world.probe["inventory"]["resourceStocks"] = [{"type":"metals","containers":[{"amount":.2,"container":{"id":"box"}}]}]
    result = HubCampaignService(ops).decide(config)
    assert result.phase == "clearing_container"
    task = result.tasks[0]
    if kind == "manny":
        ops.mining.idle_mannies = lambda: [{"id":"extra"},{"id":"worker"}]
    command = TaskCommandTranslator(ops,1).translate(task)
    expected = {"kind":"resource","resourceType":"metals","amount":.2,"fromContainerId":"box"} if kind == "metals" else (
        {"kind":"manny","targetMannyId":"extra"} if kind == "manny" else {"kind":"item","itemId":"extra"})
    assert command.payload == {**expected,"toContainerId":"core"}
    calls = []
    CapabilityDispatcher(SimpleNamespace(storage=SimpleNamespace(move=lambda *args:calls.append(args)))).dispatch(command)
    assert calls == [(1,{**command.payload,"actorMannyId":"worker"})]
    config["infrastructureCampaign"] = result.state
    ops.data_engine.fleet_roles = lambda _: [{"asset_id":"1","role":"hub","metadata_json":json.dumps(config)}]
    assert not command_blockers(ops,command)
    assert TaskCommandTranslator(ops,1).translate(HubCampaignService(ops).decide(config).tasks[0]).fingerprint == command.fingerprint
    boxes[1]["freeCapacity"] = 0
    assert "hub_cleanup_changed" in command_blockers(ops,command)
    assert not HubCampaignService(ops).decide(config).tasks
    boxes[1]["freeCapacity"] = .3
    if kind == "metals":
        ops.world.probe["inventory"]["resourceStocks"] = []
    else:
        extra["container"] = {"id":"core"}
    assert HubCampaignService(ops).decide(config).tasks[0].action == "Deliver Hub Container"


def test_hub_cleanup_never_uses_another_packages_container_or_moves_busy_cargo():
    config = {"infrastructureEnabled":True,"infrastructureCampaign":{"packageQueue":[
        {"id":"one","targetProbeId":2,"containerId":"box","items":{"scut_relay":1}},
        {"id":"two","targetProbeId":3,"containerId":"other","items":{"scut_relay":1}}]}}
    extra = {"id":"manny","type":"manny","containerSpace":.1,"container":{"id":"box"}}
    boxes = [{"id":"box","usedCapacity":.1},{"id":"other","usedCapacity":0,"freeCapacity":1}]
    ops = operations([extra],role="hub",attached=boxes)
    ops.world.probe["inventory"]["containers"] = boxes
    assert not any(t.action == "Clear Hub Container" for t in HubCampaignService(ops).decide(config).tasks)
    boxes.append({"id":"core","freeCapacity":1})
    ops.world.mannies["mannies"] = [{"id":"manny","currentTask":"crafting"}]
    assert not any(t.action == "Clear Hub Container" for t in HubCampaignService(ops).decide(config).tasks)


def test_hub_packs_before_receiver_arrives_and_shows_loaded_stock():
    ops = operations([{"id":"relay", "type":"scut_relay", "containerSpace":.1}], role="hub",
                     attached=[{"id":"box", "usedCapacity":0}])
    ops.data_engine.get_preference = lambda *_: "{}"
    config = {"infrastructureEnabled":True, "outputRequests":[{"id":"p", "targetProbeId":2, "items":{"scut_relay":1}}]}
    result = HubCampaignService(ops).decide(config)
    assert result.tasks[0].action == "Load Hub Output"
    assert result.packages[0]["availableItems"] == {"scut_relay":1}
    assert result.packages[0]["receiverBlocker"] == "receiver_refresh"
    config["infrastructureCampaign"] = result.state
    ops.world.probe["inventory"]["items"][0]["container"] = {"id":"box"}
    packed = HubCampaignService(ops).decide(config)
    assert not packed.tasks
    assert packed.summary.startswith("Shipment packed.")
    assert packed.packages[0]["loadedItems"] == {"scut_relay":1}
    assert packed.packages[0]["missingItems"] == {"scut_relay":0}


def test_hub_fresh_receiver_location_overrides_stale_fleet_and_upgrade_limit():
    from src.operations.hub_receiving import publish_live_readiness
    ops = operations([{"id":"relay", "type":"scut_relay", "containerSpace":.1, "container":{"id":"box"}}],
                     role="hub", attached=[{"id":"box", "usedCapacity":.1}])
    values = {}
    ops.data_engine.set_preference = lambda k,v:values.update({k:v})
    ops.data_engine.get_preference = lambda k,d:values.get(k,d)
    ops.world.fleet["probes"][0].update(status="moving", sector={"relative":vars(P(10,0,0))})
    receiver = {"id":2,"status":"idle","model":"generic","sector":{"relative":vars(P(0,0,0))},
                "inventory":{"containers":[{"id":str(i),"kind":"container","capacity":1,"usedCapacity":0} for i in range(5)]}}
    publish_live_readiness(ops.data_engine,receiver,{"improvements":{"improvements":[{"id":"reinforced_couplings","done":True}]}})
    config = {"infrastructureEnabled":True,"infrastructureCampaign":{"delivery":{
        "id":"p","targetProbeId":2,"items":{"scut_relay":1},"containerId":"box"}}}
    result = HubCampaignService(ops).decide(config)
    assert result.tasks[0].action == "Deliver Hub Container"
    assert "5/9" in result.packages[0]["receiverSummary"]
    ops.data_engine.fleet_roles = lambda _: [{"asset_id":"1","role":"hub","metadata_json":json.dumps(config)}]
    command = TaskCommandTranslator(ops,1).translate(result.tasks[0])
    assert not command_blockers(ops, command)


def test_hub_package_progress_does_not_double_count_shared_stock_or_active_crafts():
    ops = operations(kit(1,0),role="hub")
    ops.manufacturing.active_production_count = lambda kind: 1 if kind == "scut_relay" else 0
    config = {"infrastructureEnabled":True,"outputRequests":[
        {"id":str(i),"targetProbeId":i,"items":{"scut_relay":2}} for i in (2,3)]}
    result = HubCampaignService(ops).decide(config)
    assert sum(p["availableItems"]["scut_relay"] for p in result.packages) == 1
    assert sum(p["craftingItems"]["scut_relay"] for p in result.packages) == 1
    assert sum(p["missingItems"]["scut_relay"] for p in result.packages) == 2


def test_hub_targeted_refresh_fetches_receivers_own_upgrade_context(tmp_path):
    from src.data import DataEngine
    from src.ui.controller import MissionControlDataService
    from src.planner.desired_state import DesiredState
    ops = operations([{"id":"relay","type":"scut_relay","containerSpace":.1,"container":{"id":"box"}}],
                     role="hub", attached=[{"id":"box","usedCapacity":.1}])
    engine = ops.data_engine = DataEngine(tmp_path / "receiving.sqlite3")
    engine.assign_fleet_role("probe",1,"hub", metadata={"infrastructureEnabled":True,
        "infrastructureCampaign":{"delivery":{"id":"p","targetProbeId":2,"containerId":"box","items":{"scut_relay":1}}}})
    target = {"id":2,"status":"idle","sector":{"relative":vars(P(0,0,0))},"inventory":{"containers":[
        {"id":str(i),"kind":"container","capacity":1,"usedCapacity":0} for i in range(5)]}}
    calls = []
    service = MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine = engine
    service.recipes = SimpleNamespace(all=lambda: [])
    service.client = SimpleNamespace(get_probe=lambda i: calls.append(("probe",i)) or target)
    service.capabilities = SimpleNamespace(probes=SimpleNamespace(
        improvements=lambda i: calls.append(("improvements",i)) or {"improvements":[{"id":"reinforced_couplings","done":True}]},
        damage_warnings=lambda i: calls.append(("warnings",i)) or {}))
    _, tasks, view = service._reconcile_infrastructure_campaign(ops,1,DesiredState.unconfigured())
    assert calls == [("probe",2),("improvements",2),("warnings",2)]
    assert tasks[0].action == "Deliver Hub Container"
    assert "5/9" in view["packages"][0]["receiverSummary"]


@pytest.mark.parametrize("demand", ["reserve", "craft", "package"])
def test_enabled_hub_preserves_local_mining_for_resource_and_crafting_goals(tmp_path, demand):
    from unittest.mock import patch
    from dataclasses import replace
    from src.data import DataEngine
    from src.planner.desired_state import DesiredState, ResourceGoal, ProductionGoal
    from src.planner.desired_state_store import DesiredStateStore
    from src.ui.controller import MissionControlDataService
    from src.operations.infrastructure import InfrastructureDecision
    from tests.test_planner_missions import build_operations

    ops = build_operations(metals=0)
    ops.world.fleet = {"probes":[]}
    engine = ops.data_engine = DataEngine(tmp_path / "hub.sqlite3")
    config = {"infrastructureEnabled":True}
    desired = DesiredState.unconfigured()
    if demand == "reserve":
        desired = replace(desired, resources=(ResourceGoal("metals", 2),))
    elif demand == "craft":
        desired = replace(desired, production=(ProductionGoal("storage_container", 1),))
    else:
        config["outputRequests"] = [{"id":"package", "targetProbeId":2, "items":{"storage_container":1}}]
    engine.assign_fleet_role("probe", 1, "hub", metadata=config)
    DesiredStateStore(engine).save(desired, 1)
    service = MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine = engine
    service.recipes = ops.manufacturing.recipes
    service._apply_probe_role_goals = lambda desired, *_: desired
    service._reconcile_completed_autonomous_travel = lambda _ops, _id, desired: desired
    service._reconcile_transport_operation = lambda _ops, _id, desired: (desired, [], None)
    service._reserve_tanker_delivery_tasks = lambda *_: []
    service._reconcile_explorer_campaign = lambda _ops, _id, desired: (desired, [], {})
    service._reconcile_miner_campaign = lambda _ops, _id, desired: (desired, [], {})
    service._dependency_mining_idle_grace_elapsed = lambda _: True
    with patch("src.operations.hub_receiving.HubReceivingService.reconcile", return_value=InfrastructureDecision("", "")):
        view = service.automation_view(ops, 1)
    assert any(t["action"] == "Mine Resource" for t in view["planning"])
    mining = [p for p in service._prepared_commands if p.command.type == C.MANNY_MINE]
    assert mining
    assert mining[0].command.payload["resources"] == ["metals"]
    assert "targetContainerId" not in mining[0].command.payload
    ops.world.sector["resources"] = []
    with patch("src.operations.hub_receiving.HubReceivingService.reconcile", return_value=InfrastructureDecision("", "")):
        service.automation_view(ops, 1)
    assert not any(p.command.type == C.MANNY_MINE for p in service._prepared_commands)


def test_hub_collects_two_refills_and_decimal_manual_receiver_while_waiting():
    ops = operations(role="hub")
    ops.world.fleet = {"probes": []}
    rows = [{"role":"relay_placement", "asset_id":str(i), "settings":settings(
        infrastructureCampaign={"supplyRequest":{"id":f"auto-{i}", "items":{"scut_relay":2, "integrated_circuit":2}}})}
        for i in (2,3)]
    config = {"infrastructureEnabled":True,
              "outputRequest":{"id":"manual", "targetProbeId":4.0, "items":{"scut_transit_beacon":3}}}
    result = HubCampaignService(ops).decide(config, rows)
    assert len(result.packages) == 3
    assert result.production == {"scut_relay":4, "integrated_circuit":4, "scut_transit_beacon":3, "additional_container":1}
    assert result.packages[-1]["targetProbeId"] == 4
    config["infrastructureCampaign"] = result.state
    assert len(HubCampaignService(ops).decide(config, rows).packages) == 3


def test_hub_append_preserves_packages_from_stale_editor_and_legacy():
    from src.operations.infrastructure import merge_hub_settings
    recipes = {"scut_relay":{}, "integrated_circuit":{}}
    legacy = {"outputRequest":{"id":"old", "targetProbeId":2, "items":{"scut_relay":1}}}
    payload = {"enqueuePackage":{"id":"new", "targetProbeId":3.0,
               "items":{"scut_relay":2.0, "integrated_circuit":2}}}
    first = merge_hub_settings(legacy, payload, recipes)
    second = merge_hub_settings(first, {"enqueuePackage":{"id":"third", "targetProbeId":4,
                               "items":{"scut_relay":1}}}, recipes)
    repeated = merge_hub_settings(second, payload, recipes)
    assert [p["id"] for p in repeated["outputRequests"]] == ["old", "new", "third"]
    assert repeated["outputRequests"][1]["targetProbeId"] == 3
    with pytest.raises(ValueError):
        merge_hub_settings(second, {"enqueuePackage":{"id":"bad", "targetProbeId":4,
                           "items":{"unknown":1}}}, recipes)


def test_hub_blocked_package_cannot_borrow_another_packages_container():
    item = {"id":"relay", "type":"scut_relay", "containerSpace":.5, "container":{"id":"reserved"}}
    ops = operations([item], role="hub", attached=[{"id":"reserved", "usedCapacity":.5}, {"id":"empty", "usedCapacity":0}])
    config = {"infrastructureEnabled":True, "infrastructureCampaign":{"packageQueue":[
        {"id":"waiting", "targetProbeId":99, "items":{"scut_relay":1}, "containerId":"reserved"},
        {"id":"ready", "targetProbeId":2, "items":{"scut_relay":1}}]}}
    result = HubCampaignService(ops).decide(config)
    assert not result.tasks
    assert result.state["packageQueue"][1]["containerId"] == "empty"
    ops.world.probe["inventory"]["items"].append({"id":"available", "type":"scut_relay", "containerSpace":.5})
    result = HubCampaignService(ops).decide({**config, "infrastructureCampaign":result.state})
    assert result.tasks[0].target == "available"
    assert result.tasks[0].metadata["toContainerId"] == "empty"


def test_hub_splits_mixed_package_and_counts_only_accepted_shipments():
    items = [{"id":"r1", "type":"scut_relay", "containerSpace":.75, "container":{"id":"box"}},
             {"id":"r2", "type":"scut_relay", "containerSpace":.75},
             {"id":"c1", "type":"integrated_circuit", "containerSpace":.5}]
    attached = [{"id":"box", "usedCapacity":.75, "freeCapacity":.25}]
    ops = operations(items, role="hub", attached=attached)
    config = {"infrastructureEnabled":True, "infrastructureCampaign":{"delivery":{
        "id":"mixed", "targetProbeId":2.0, "containerId":"box", "items":{"scut_relay":2,"integrated_circuit":1}}}}
    first = HubCampaignService(ops).decide(config)
    assert first.tasks[0].action == "Deliver Hub Container"
    config["infrastructureCampaign"] = first.state
    attached.clear()
    assert HubCampaignService(ops).decide(config).phase == "container_missing"
    ops.data_engine.action_was_successful = lambda _: True
    second = HubCampaignService(ops).decide(config)
    assert second.state["delivery"]["items"] == {"scut_relay":1, "integrated_circuit":1}
    assert second.state["delivery"]["shipment"] == 1
    assert not second.state["completedRequests"]
    # Resume after receiver return: two more differently sized shipments.
    for item, remaining in [(items[1], {"integrated_circuit":1}), (items[2], {})]:
        config["infrastructureCampaign"] = second.state
        attached.append({"id":"box", "usedCapacity":0, "freeCapacity":1})
        ops.world.probe["inventory"]["items"] = [i for i in items[1:] if i["type"] in second.state["delivery"]["items"]]
        loading = HubCampaignService(ops).decide(config)
        assert loading.tasks[0].action == "Load Hub Output"
        assert loading.tasks[0].target == item["id"]
        item["container"] = {"id":"box"}
        attached[0].update(usedCapacity=item["containerSpace"], freeCapacity=1-item["containerSpace"])
        config["infrastructureCampaign"] = loading.state
        handoff = HubCampaignService(ops).decide(config)
        assert handoff.tasks[0].action == "Deliver Hub Container"
        config["infrastructureCampaign"] = handoff.state
        attached.clear()
        second = HubCampaignService(ops).decide(config)
        assert (second.state.get("delivery") or {}).get("items", {}) == remaining
    assert second.state["completedRequests"] == ["mixed"]
    assert second.state["packageQueue"] == []


def test_returning_expansion_publishes_missing_kit_before_arrival():
    ops = operations([], here=P(2,0,0))
    result = RelayCampaignService(ops).decide(settings(infrastructureCampaign={"returning":True}))
    assert result.destination == P(0,0,0)
    assert result.state["supplyRequest"]["items"] == {"scut_relay":2,"integrated_circuit":2,"scut_transit_beacon":1}


def test_live_receiver_readiness_uses_fresh_inventory_and_safe_limit():
    from src.operations.hub_receiving import publish_live_readiness, readiness
    values = {}
    engine = SimpleNamespace(set_preference=lambda k,v:values.update({k:v}), get_preference=lambda k,d:values.get(k,d))
    publish_live_readiness(engine, {"id":2,"model":"generic", "sector":{"relative":vars(P(0,0,0))},
        "inventory":{"containers":[{"id":"own","kind":"container","capacity":1,"usedCapacity":.25}]}})
    result = readiness(engine,2)
    assert result["safeLimit"] == 4
    assert result["containerCount"] == 1
    assert result["freeCapacity"] == .75


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
            get_preference=lambda *_: json.dumps({"at":time.time(),"sector":vars(here),"containerCount":1,"safeLimit":4,"freeCapacity":5,"storageFreeCapacities":[5]})),
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


@pytest.mark.parametrize("beacon_available", [True, False])
def test_signal_refill_returns_to_frontier_before_selecting_another_site(beacon_available):
    from tests.test_planner_missions import build_operations
    frontier = P(3, 3, 0)
    config = settings(expansionMode="signal", infrastructureCampaign={
        "signalDirection":{"origin":vars(P(0,0,0)), "vector":{"x":1,"y":1,"z":0}},
        "completedSites":[vars(frontier)],
    })
    returning = RelayCampaignService(operations(here=frontier)).decide(config)
    assert returning.destination == P(0,0,0)
    assert returning.state["resumePosition"] == vars(frontier)
    # Round-trip the persisted campaign, as a restart during refill would.
    config["infrastructureCampaign"] = json.loads(json.dumps(returning.state))
    waiting = RelayCampaignService(operations()).decide(config)
    assert waiting.phase == "restocking" and waiting.destination is None
    config["infrastructureCampaign"] = waiting.state
    stocked = RelayCampaignService(operations(kit())).decide(config)
    assert stocked.phase == "restocked"
    config["infrastructureCampaign"] = stocked.state
    resumed = RelayCampaignService(operations(kit())).decide(config)
    assert resumed.phase == "resuming" and resumed.destination == frontier
    assert "target" not in resumed.state and not resumed.tasks

    live = build_operations()
    live.world.hazard_context = {"scutNetworks":[{"network":{"id":1,"relays":[
        {"status":"on", "isTransitBeacon":beacon_available, "coverageRadiusSectors":10,
         "sector":{"relative":vars(p)}} for p in (P(0,0,0), frontier)
    ]}}]}
    route = live.travel_safety.assess(resumed.destination, route_mode="segmented")
    assert route.recommended.name == ("direct" if beacon_available else "segmented")
    assert len(route.recommended.hops) == (1 if beacon_available else 3)
    config["infrastructureCampaign"] = resumed.state
    arrived = RelayCampaignService(operations(kit(), here=frontier, stars=())).decide(config)
    assert "resumePosition" not in arrived.state
    assert not arrived.tasks  # Never redeploy at the completed relay.


def test_signal_existing_home_refill_recovers_last_completed_position():
    config = settings(expansionMode="signal", infrastructureCampaign={
        "returning":True, "completedSites":[vars(P(2,0,0))],
        "signalDirection":{"origin":vars(P(0,0,0)), "vector":{"x":1,"y":0,"z":0}},
    })
    # Older saved campaigns may already be at home when this version starts.
    result = RelayCampaignService(operations()).decide(config)
    assert result.state.get("resumePosition") == vars(P(2,0,0))


def test_signal_refill_preserves_unfinished_relay_identity():
    frontier = P(2,0,0)
    config = settings(expansionMode="signal", infrastructureCampaign={
        "returning":True, "resumePosition":vars(frontier), "resumeTarget":vars(frontier),
        "relayId":"9", "placeBeacon":True,
        "signalDirection":{"origin":vars(P(0,0,0)), "vector":{"x":1,"y":0,"z":0}},
    })
    result = RelayCampaignService(operations(kit())).decide(config)
    config["infrastructureCampaign"] = result.state
    result = RelayCampaignService(operations(kit())).decide(config)
    assert result.phase == "resuming" and result.state["relayId"] == "9"
    config["infrastructureCampaign"] = result.state
    result = RelayCampaignService(operations(kit(), here=frontier,
        local=[{"id":9,"type":"scut_relay","status":"on"}])).decide(config)
    assert result.tasks[0].action == "Install SCUT Beacon"
    assert result.tasks[0].target == "9"


@pytest.mark.parametrize("beacon_mode", ["final", "every", "none"])
def test_refill_beacon_quantity_is_independent_and_circuits_cover_each_relay(beacon_mode):
    config = settings(relayStock=4, beaconMode=beacon_mode, refillBeacons=True,
                      beaconStock=7, infrastructureCampaign={"returning":True})
    result = RelayCampaignService(operations(kit(relays=1, beacons=2))).decide(config)
    assert result.state["supplyRequest"]["items"] == {
        "scut_relay":3, "integrated_circuit":3, "scut_transit_beacon":5,
    }
    config["infrastructureCampaign"] = result.state
    assert RelayCampaignService(operations(kit(relays=4, beacons=6))).decide(config).phase == "restocking"
    assert RelayCampaignService(operations(kit(relays=4, beacons=7))).decide(config).phase == "restocked"


def test_disabled_beacon_refills_do_not_order_beacons_or_loop_departure():
    config = settings(refillBeacons=False, beaconStock=7,
                      infrastructureCampaign={"returning":True})
    result = RelayCampaignService(operations()).decide(config)
    assert result.state["supplyRequest"]["items"] == {"scut_relay":2, "integrated_circuit":2}
    config["infrastructureCampaign"] = result.state
    result = RelayCampaignService(operations(kit(beacons=0))).decide(config)
    assert result.phase == "beacon_refill_disabled"
    assert result.destination is None and result.state["returning"]
    assert "supplyRequest" not in result.state


def test_no_beacon_placement_can_restock_without_beacons():
    config = settings(beaconMode="none", refillBeacons=False,
                      infrastructureCampaign={"returning":True})
    result = RelayCampaignService(operations(kit(beacons=0))).decide(config)
    assert result.phase == "restocked"


def test_disabling_beacon_placement_releases_an_unfinished_site():
    config = settings(beaconMode="none", refillBeacons=False,
                      infrastructureCampaign={"target":{"x":2,"y":0,"z":0},
                                              "relayId":"9", "placeBeacon":True})
    ops = operations(kit(beacons=0), here=P(2,0,0),
                     local=[{"id":9,"type":"scut_relay","status":"on"}])
    result = RelayCampaignService(ops).decide(config)
    assert result.phase == "site_complete" and not result.tasks


@pytest.mark.parametrize("quantity", [0, 21])
def test_beacon_refill_target_is_validated(quantity):
    with pytest.raises(ValueError, match="Beacon restock quantity"):
        validate_settings("relay_placement", settings(refillBeacons=True, beaconStock=quantity))


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


def test_settings_reject_invalid_direction_and_invalid_output_quantity():
    with pytest.raises(ValueError):
        validate_settings("relay_placement",settings(expansionMode="direction",direction={"x":0,"y":0,"z":0}))
    with pytest.raises(ValueError):
        validate_settings("hub",{"infrastructureEnabled":True,"outputRequest":{"id":"a","targetProbeId":2,"items":{"manny":0}}})


@pytest.mark.parametrize("count", [4, 6])
def test_hub_allows_temporary_delivery_at_or_above_travel_container_limit(count):
    config = {"infrastructureEnabled":True,"infrastructureCampaign":{"delivery":{"id":"batch","targetProbeId":2,"items":{"scut_relay":1}, "containerId":"box"}}}
    ops = operations([{"id":"relay", "type":"scut_relay", "container":{"id":"box"}}],role="hub", attached=[{"id":"box","usedCapacity":.1}])
    ops.data_engine.get_preference = lambda *_: json.dumps({"at":time.time(),"sector":{"x":0,"y":0,"z":0},"containerCount":count,"safeLimit":4,"freeCapacity":5,"storageFreeCapacities":[5]})
    result = HubCampaignService(ops).decide(config)
    assert result.tasks[0].action == "Deliver Hub Container"
    assert "Temporary delivery allowed" in result.packages[0]["receiverSummary"]


@pytest.mark.parametrize("slots", [[], [.1], [.3, .3]])
def test_temporary_delivery_requires_contents_to_fit_permanent_storage_slots(slots):
    config = {"infrastructureEnabled":True,"infrastructureCampaign":{"delivery":{
        "id":"batch","targetProbeId":2,"items":{"scut_relay":1},"containerId":"box"}}}
    ops = operations([{"id":"relay","type":"scut_relay","containerSpace":.5,"container":{"id":"box"}}],
                     role="hub",attached=[{"id":"box","usedCapacity":.5}])
    ops.data_engine.get_preference = lambda *_: json.dumps({"at":time.time(),"status":"idle","sector":vars(P(0,0,0)),
        "containerCount":6,"safeLimit":4,"freeCapacity":sum(slots),"storageFreeCapacities":slots})
    result = HubCampaignService(ops).decide(config)
    assert result.phase == "receiver_storage_full"
    assert not result.tasks


def test_expansion_preserves_request_at_container_limit_without_releasing_own_storage():
    ops = operations(kit(1, beacons=0))
    ops.travel_safety.additional_container_count = lambda: 3
    ops.travel_safety.container_break_threshold = lambda: 4
    config = settings(infrastructureCampaign={"returning":True})
    blocked = RelayCampaignService(ops).decide(config)
    assert blocked.phase == "restocking"
    assert not blocked.tasks and blocked.destination is None
    request = blocked.state["supplyRequest"]
    ops.travel_safety.additional_container_count = lambda: 2
    resumed = RelayCampaignService(ops).decide(settings(infrastructureCampaign=blocked.state))
    assert resumed.phase == "restocking"
    assert resumed.state["supplyRequest"] == request


def test_stocked_expansion_resumes_without_refill_or_empty_container_release():
    ops = operations(kit(), attached=[{"id":"empty", "usedCapacity":0}])
    ops.travel_safety.additional_container_count = lambda: 3
    ops.travel_safety.container_break_threshold = lambda: 4
    config = settings(infrastructureCampaign={"returning":True, "supplyRequest":{
        "id":"old-request", "items":{"scut_relay":2, "integrated_circuit":2, "scut_transit_beacon":1}}})
    result = RelayCampaignService(ops).decide(config)
    assert result.phase == "restocked"
    assert not result.tasks
    assert "supplyRequest" not in result.state
    next_step = RelayCampaignService(ops).decide(settings(infrastructureCampaign=result.state))
    assert next_step.phase == "travelling"


def test_legacy_resupply_slot_commands_still_require_empty_container_and_hub_recovers_returns():
    ops = operations(kit(1, beacons=0), attached=[{"id":"empty", "usedCapacity":0}])
    ops.travel_safety.additional_container_count = lambda: 3
    ops.travel_safety.container_break_threshold = lambda: 4
    config = settings(infrastructureCampaign={"returning":True})
    result = RelayCampaignService(ops).decide(config)
    assert result.phase == "restocking" and not result.tasks
    result.state.update(resupplySlotContainer="empty", resupplyReturns={"empty":result.state["supplyRequest"]["id"]})
    config["infrastructureCampaign"] = result.state
    ops.data_engine.fleet_roles = lambda _: [{"asset_id":"1", "role":"relay_placement", "metadata_json":json.dumps(config)}]
    task = Task(action="Return Hub Container", target="empty", reason="Legacy slot return", metadata={"resupplySlot":True,"expectedSector":vars(P(0,0,0)),"mode":"drifting"})
    command = TaskCommandTranslator(ops,1).translate(task)
    assert command.payload == {"containerId":"empty", "mode":"drifting"}
    assert not command_blockers(ops,command)
    assert not infrastructure_blockers(ops,command)
    ops.world.probe["inventory"]["items"].append({"id":"cargo", "type":"scut_relay", "container":{"id":"empty"}})
    assert "resupply_slot_container_unavailable" in command_blockers(ops,command)
    assert RelayCampaignService(ops).decide(config).phase == "restocking"
    hub = operations(role="hub")
    hub.containers.detached = lambda: [{"id":"detached-empty", "containerId":"empty", "mode":"drifting"}]
    returned = HubCampaignService(hub).decide({"infrastructureEnabled":True, "receiveContainers":False},
        [{"role":"relay_placement", "settings":config}])
    assert returned.phase == "recovering_return"
    assert returned.tasks[0].target == "detached-empty"


@pytest.mark.parametrize("container_count", [1, 7])
def test_receiver_unloads_then_returns_only_confirmed_empty_container(tmp_path, container_count):
    from src.data import DataEngine
    from src.operations.hub_receiving import HubReceivingService, stage_receipt, receipt_blockers, receipts
    engine = DataEngine(tmp_path / "receiving.sqlite")
    ops = operations([{"id":"relay","type":"scut_relay","containerSpace":.1,"container":{"id":"supply"}}],
                     attached=[{"id":"supply","usedCapacity":.1,"freeCapacity":.9}])
    ops.data_engine = engine
    ops.travel_safety.additional_container_count = lambda: container_count
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


def test_expansion_prepares_next_kit_while_away_and_reuses_request_on_return():
    config = settings()
    outbound = RelayCampaignService(operations(kit(), here=P(2,0,0))).decide(config)
    request = outbound.state['supplyRequest']
    assert request['prepareOnly']
    assert request['items'] == {'scut_relay':2,'integrated_circuit':2,'scut_transit_beacon':1}
    config['infrastructureCampaign'] = json.loads(json.dumps(outbound.state))
    config['infrastructureCampaign'].pop('target', None)
    returning = RelayCampaignService(operations(here=P(2,0,0))).decide(config)
    assert returning.state['supplyRequest']['id'] == request['id']
    assert returning.state['supplyRequest']['prepareOnly'] is False
    assert returning.state['restockGeneration'] == outbound.state['restockGeneration']


def test_prepared_future_kit_cannot_ship_until_refill_and_preserves_packing():
    request = {'id':'future','items':{'scut_relay':2},'prepareOnly':True}
    rows = [{'role':'relay_placement','asset_id':'2','settings':settings(infrastructureCampaign={'supplyRequest':request})}]
    boxes = [{'id':'box','capacity':1,'usedCapacity':.2,'freeCapacity':.8}]
    items = [{'id':f'r{i}','type':'scut_relay','containerSpace':.1,'container':{'id':'box'}} for i in range(2)]
    config = {'infrastructureEnabled':True,'infrastructureCampaign':{'packageQueue':[
        {**request,'targetProbeId':2,'containerId':'box'}]}}
    ops = operations(items,role='hub',attached=boxes)
    prepared = HubCampaignService(ops).decide(config,rows)
    assert not prepared.tasks
    assert prepared.packages[0]['receiverBlocker'] == 'awaiting_refill'
    config['infrastructureCampaign'] = json.loads(json.dumps(prepared.state))
    request['prepareOnly'] = False
    sending = HubCampaignService(ops).decide(config,rows)
    assert sending.tasks[0].action == 'Deliver Hub Container'
    assert sending.state['delivery']['containerId'] == 'box'
    assert sending.state['delivery']['id'] == 'future'


def test_hub_package_goal_precedes_bulk_stock_and_preserves_saved_goals(tmp_path):
    from dataclasses import replace
    from src.data import DataEngine
    from src.ui.controller import MissionControlDataService
    from src.planner.desired_state import DesiredState, ProductionGoal, ResourceGoal
    from src.planner.planner import Planner
    from tests.test_planner_missions import build_operations
    ops = build_operations(metals=0)
    ops.world.fleet = {'probes':[]}
    engine = ops.data_engine = DataEngine(tmp_path/'priority.sqlite3')
    engine.assign_fleet_role('probe',1,'hub',metadata={'infrastructureEnabled':True,
        'outputRequests':[{'id':'delivery','targetProbeId':2,'items':{'storage_container':2}}]})
    service = MissionControlDataService.__new__(MissionControlDataService)
    service.data_engine=engine
    service.recipes=ops.manufacturing.recipes
    desired = replace(DesiredState.unconfigured(), production=(ProductionGoal('manny',999,1),
        ProductionGoal('storage_container',50,1)), resources=(ResourceGoal('metals',100,2),))
    effective,_,_ = service._reconcile_infrastructure_campaign(ops,1,desired)
    goals={g.recipe_id:g for g in effective.production}
    assert goals['storage_container'] == ProductionGoal('storage_container',2,1)
    assert goals['manny'].priority == 2
    assert desired.production[1].quantity == 50
    tasks=Planner(ops,effective).tasks()
    mining=next(t for t in tasks if t.resource_type=='metals')
    assert mining.priority == 1 and mining.quantity == 1  # Next package unit, not 100 ECE.
    assert effective.resources == desired.resources  # Reserve still resumes later.
    ops.world.probe['inventory']['resourceStocks'][0]['amount']=1
    tasks=Planner(ops,effective).tasks()
    assert next(t for t in tasks if t.action=='Craft Item').target=='storage_container'


@pytest.mark.parametrize('mode', ['auto', 'signal', 'direction'])
def test_all_expansion_modes_require_union_edge_and_wait_without_frontier(mode):
    ops = operations(kit(), stars=(P(2,0,0), P(6,0,0)))
    network = ops.world.hazard_context['scutNetworks'][0]['network']
    network['relays'][0]['coverageRadiusSectors'] = 6
    state = {'signalDirection': {'origin':vars(P(0,0,0)), 'vector':{'x':1,'y':0,'z':0}}}
    config = settings(expansionMode=mode, direction=vars(P(20,0,0)), infrastructureCampaign=state)
    result = RelayCampaignService(ops).decide(config)
    assert result.destination == P(6,0,0)
    ops.galaxy.known_sectors = lambda: [SimpleNamespace(coordinates=P(2,0,0), observed={'objects':[{'type':'star'}]})]
    result = RelayCampaignService(ops).decide(config)
    assert result.phase == 'waiting_for_sites'
    assert not result.tasks and result.destination is None


def test_union_edge_rejects_seam_covered_by_another_relay():
    ops = operations(kit())
    relays = [(P(0,0,0),6), (P(6,0,0),6)]
    service = RelayCampaignService(ops)
    assert service.at_coverage_edge(P(6,0,0), relays[:1])
    assert not service.at_coverage_edge(P(6,0,0), relays)
    assert service.at_coverage_edge(P(12,0,0), relays)
    assert not service.at_coverage_edge(P(14,0,0), relays)


def test_changed_coverage_reselects_unbuilt_site_and_blocks_stale_deployment():
    target = P(2,0,0)
    ops = operations(kit(), here=target)
    config = settings(infrastructureCampaign={'target':vars(target)})
    planned = RelayCampaignService(ops).decide(config)
    config['infrastructureCampaign'] = planned.state
    command = TaskCommandTranslator(ops,1).translate(planned.tasks[0])
    ops.data_engine.fleet_roles = lambda _: [{'asset_id':'1','role':'relay_placement','metadata_json':json.dumps(config)}]
    ops.world.hazard_context['scutNetworks'][0]['network']['relays'][0]['coverageRadiusSectors'] = 6
    assert 'relay_site_not_at_coverage_edge' in command_blockers(ops, command)
    result = RelayCampaignService(ops).decide(config)
    assert result.phase == 'reselecting' and 'target' not in result.state
    ops.data_engine.action_was_successful = lambda _: True
    result = RelayCampaignService(ops).decide(config)
    assert result.phase != 'reselecting'  # Accepted deployment retains its identity.


@pytest.mark.parametrize('cargo_kind', ['manny', 'metals'])
def test_receiver_clears_remaining_cargo_before_returning_packaging(tmp_path, cargo_kind):
    from src.data import DataEngine
    from src.operations.hub_receiving import HubReceivingService, stage_receipt, receipt_blockers
    cargo = {'id':'cargo','type':'manny','containerSpace':.1,'container':{'id':'supply'}}
    supply = {'id':'supply','usedCapacity':.1,'freeCapacity':.9}
    ops = operations([cargo] if cargo_kind == 'manny' else [], attached=[supply])
    ops.data_engine = DataEngine(tmp_path/'receiving.sqlite')
    ops.world.probe['inventory']['containers'] = [{'id':'core','freeCapacity':1},supply]
    if cargo_kind == 'metals':
        ops.world.probe['inventory']['resourceStocks'] = [{'type':'metals','containers':[{'amount':.1,'container':{'id':'supply'}}]}]
    ops.world.mannies['mannies'] = [cargo] if cargo_kind == 'manny' else []
    ops.mining.idle_mannies = lambda: [{'id':'cargo'}, {'id':'worker'}]
    ops.travel_safety.additional_container_count = lambda: 1
    ops.travel_safety.container_break_threshold = lambda: 5
    stage_receipt(ops.data_engine,2,1,'supply','batch',vars(P(0,0,0)),'accepted')
    service = HubReceivingService(ops)
    result = service.reconcile()
    assert result.phase == 'unloading_supply'
    command = TaskCommandTranslator(ops,1).translate(result.tasks[0])
    assert command.payload['kind'] == ('manny' if cargo_kind == 'manny' else 'resource')
    if cargo_kind == 'manny':
        assert command.target_id == 'worker'
    assert not receipt_blockers(ops,command)
    assert not command_blockers(ops,command)
    repeated = TaskCommandTranslator(ops,1).translate(service.reconcile().tasks[0])
    assert repeated.fingerprint == command.fingerprint
    ops.world.probe['inventory']['containers'][0]['freeCapacity'] = 0
    assert receipt_blockers(ops,command) == ('hub_receipt_cleanup_changed',)
    assert not service.reconcile().tasks
    ops.world.probe['inventory']['containers'][0]['freeCapacity'] = 1
    if cargo_kind == 'manny':
        cargo['currentTask'] = 'mining'
        assert receipt_blockers(ops,command) == ('hub_receipt_cleanup_changed',)
        assert not service.reconcile().tasks
        cargo.pop('currentTask')
        cargo['container'] = {'id':'core'}
    else:
        ops.world.probe['inventory']['resourceStocks'] = []
    assert service.reconcile().phase == 'receipt_empty_wait'
    supply['usedCapacity'] = 0
    assert service.reconcile().tasks[0].action == 'Return Hub Container'


@pytest.mark.parametrize('kind', ['manny','additional_container'])
def test_hub_packages_craft_extra_assets_before_permanent_transfer(kind):
    items = [{'id':'asset','type':kind,'containerSpace':.05,'container':{'id':'core'}}]
    boxes = [{'id':'asset','kind':'container','usedCapacity':0,'freeCapacity':1}]
    ops = operations(items, role='hub', attached=boxes)
    ops.world.probe['inventory']['containers'] = boxes
    config = {'infrastructureEnabled':True,'outputRequests':[{'id':'p','targetProbeId':2,'items':{kind:1}}]}
    planned = HubCampaignService(ops).decide(config)
    assert planned.phase == 'producing' and not planned.tasks
    assert planned.production[kind] == 2
    assert planned.packages[0]['availableItems'][kind] == 0
    config['infrastructureCampaign'] = planned.state
    ops.manufacturing.available_inputs = lambda: ({},{kind:2})
    ops.mining.idle_mannies = lambda: [{'id':'asset'},{'id':'worker'}]
    transferred = HubCampaignService(ops).decide(config)
    task = transferred.tasks[0]
    assert task.metadata['hubAsset']
    assert 'containerId' not in transferred.state['delivery']  # No temporary receipt.
    command = TaskCommandTranslator(ops,1).translate(task)
    assert command.fingerprint == transferred.state['delivery']['assetShipment']['fingerprint']
    if kind == 'manny':
        calls = []
        CapabilityDispatcher(SimpleNamespace(mannies=SimpleNamespace(start_task=lambda *args:calls.append(args)))).dispatch(command)
        assert calls == [(1,'asset','transfer-to-probe',{'targetProbeId':2})]
    config['infrastructureCampaign'] = transferred.state
    ops.data_engine.fleet_roles = lambda _: [{'asset_id':'1','role':'hub','metadata_json':json.dumps(config)}]
    assert not command_blockers(ops,command)
    assert TaskCommandTranslator(ops,1).translate(HubCampaignService(ops).decide(config).tasks[0]).fingerprint == command.fingerprint
    invalidated = []
    ops.data_engine.set_preference = lambda key,value: invalidated.append((key,value))
    ops.data_engine.action_was_successful = lambda _: True
    assert not HubCampaignService(ops).decide(config).tasks  # Accepted, awaiting disappearance.
    ops.containers.attached = lambda: []
    ops.world.probe['inventory']['items'] = []
    done = HubCampaignService(ops).decide(config)
    assert done.phase == 'asset_delivered'
    assert invalidated == [('hub_receiving:2','{}')]
    config['infrastructureCampaign'] = done.state
    assert HubCampaignService(ops).decide(config).phase == 'delivered'


def test_permanent_container_package_honors_safe_limit_and_busy_manny_is_not_transferred():
    config = {'infrastructureEnabled':True,'infrastructureCampaign':{'packageQueue':[{
        'id':'p','targetProbeId':2,'items':{'additional_container':1},'assetBaseline':{'additional_container':0}}]}}
    ops = operations([{'id':'box','type':'additional_container'}],role='hub', attached=[{'id':'box','usedCapacity':0}])
    ops.data_engine.get_preference = lambda *_: json.dumps({'at':time.time(),'sector':vars(P(0,0,0)),
        'containerCount':4,'safeLimit':4,'freeCapacity':5,'storageFreeCapacities':[5]})
    assert HubCampaignService(ops).decide(config).phase == 'receiver_storage_limit'
    config['infrastructureCampaign']['packageQueue'][0].update(items={'manny':1},assetBaseline={'manny':0})
    ops.world.probe['inventory']['items'] = [{'id':'busy','type':'manny','containerSpace':.05}]
    ops.manufacturing.available_inputs = lambda: ({},{'manny':1})
    ops.mining.idle_mannies = lambda: []
    assert HubCampaignService(ops).decide(config).phase == 'asset_wait'


def test_asset_package_editor_validation_accepts_catalog_mannies_and_containers():
    from src.operations.infrastructure import merge_hub_settings
    recipes = SimpleNamespace(get=lambda kind: {'id':kind} if kind in {'manny','additional_container'} else None)
    merged = merge_hub_settings({}, {'enqueuePackage':{'id':'p','targetProbeId':2,
        'items':{'manny':3,'additional_container':2}}}, recipes)
    validate_settings('hub',{'infrastructureEnabled':True,**merged})
    assert merged['outputRequests'][0]['items'] == {'manny':3,'additional_container':2}
