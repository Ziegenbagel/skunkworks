"""Durable combat and salvage campaigns using the common execution boundary."""
from copy import deepcopy
import json

from src.operations.infrastructure import (InfrastructureDecision, coordinates, point,
    objects, role_rows, inventory_items, stock)
from src.planner.task import Task

ROLES = {"missile_destroyer", "salvage"}


def record(engine, key):
    try:
        return json.loads(engine.get_preference(key, "{}")) if engine else {}
    except (TypeError, ValueError):
        return {}


def local_objects(operations):
    sector = operations.world.sector
    return list(objects((sector.get("snapshot") or {}).get("sector", sector)))


def ship_targets(operations):
    return {str(o["id"]): o for o in local_objects(operations)
            if o.get("id") and (o.get("type") == "others_ship"
                or o.get("observedClass") in {"ship", "large_ship"})
            and o.get("status") not in {"destroyed", "dead"}
            and "wreck" not in str(o.get("type", ""))}


def claimed_ids(operations):
    """Conservatively protect identifiers owned by other persisted workflows."""
    def strings(value):
        if isinstance(value, dict):
            for v in value.values():
                yield from strings(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                yield from strings(v)
        elif isinstance(value, str):
            yield value
    engine = getattr(operations, "data_engine", None)
    own = str(operations.world.probe["id"])
    claimed = set()
    for row in role_rows(engine):
        if str(row["asset_id"]) != own:
            claimed.update(strings(row["settings"]))
    if engine and hasattr(engine, "operation_records"):
        from src.operations.mission import OperationStore, OperationState
        for op in OperationStore(engine).all(OperationState.ACTIVE):
            claimed.update(strings(op.metadata))
    for m in operations.world.mannies.get("mannies", []):
        if m.get("currentTask"):
            claimed.update(strings(m.get("task", {})))
    return claimed


def validate_settings(role, settings):
    if not settings.get("infrastructureEnabled"):
        return
    if coordinates(settings.get("home")) is None:
        raise ValueError("Choose a valid home sector (even X+Y+Z).")
    from src.operations.infrastructure import probe_id
    settings["hubProbeId"] = probe_id(settings.get("hubProbeId"))
    if role == "missile_destroyer":
        if not settings.get("combatAuthorized"):
            raise ValueError("Enable combat authorization before starting the destroyer.")
        if not 1 <= int(settings.get("missileStock", 1)) <= 100:
            raise ValueError("Missile refill target must be between 1 and 100.")
        if settings.get("missionId") and coordinates(settings.get("targetSector")) is None:
            raise ValueError("Choose a valid mission sector (even X+Y+Z).")


class SpecialistCampaignService:
    def __init__(self, operations):
        self.ops = operations
        self.engine = getattr(operations, "data_engine", None)

    def decide(self, role, settings):
        state = deepcopy(settings.get("infrastructureCampaign") or {})
        current = self.ops.travel.current_sector()
        home = coordinates(settings.get("home"))
        def result(phase, summary, destination=None, tasks=()):
            return InfrastructureDecision(phase, summary, destination=destination, tasks=tuple(tasks), state=state)
        if not settings.get("infrastructureEnabled"):
            return result("paused", "Role paused; its mission state is retained.")
        if current is None or home is None:
            return result("telemetry_hold", "Current or home sector is unavailable.")
        if self.ops.world.probe.get("status") not in {"idle", "arrived"}:
            return result("traveling", "Following the current mission route.")
        if role == "missile_destroyer":
            return self._combat(settings, state, current, home, result)
        return self._salvage(settings, state, current, home, result)

    def _travel(self, target, state, result, summary):
        current = self.ops.travel.current_sector()
        route = self.ops.travel.route_to(target)
        if not route or not self.ops.travel_safety.scut_route_covered(current, route):
            return result("coverage_hold", "No verified SCUT-covered route to the mission destination.")
        return result("traveling", summary, destination=target)

    def _task(self, action, target, state, **metadata):
        scope = f"specialist:{self.ops.world.probe['id']}:{state.get('missionId', 'salvage')}:{state.get('sequence', 0)}:{action}:{target}"
        return Task(action=action, target=str(target), category="specialist", priority=1,
                    workflow_authorized=True, reason=action, idempotency_scope=scope,
                    metadata={"specialistCampaign":True, "expectedSector":point(self.ops.travel.current_sector()), **metadata})

    def _fingerprint(self, task):
        from src.execution.commands import Command, CommandType as C
        payload = ({"missileItemId":task.target, "targetId":task.metadata["targetId"]}
                   if task.action == "Launch Mission Missile" else {"objectId":task.target})
        kind = C.MANNY_LAUNCH_MISSILE if task.action == "Launch Mission Missile" else C.MANNY_SALVAGE
        return Command(kind, self.ops.world.probe["id"], payload, task.reason, 1,
                       metadata={**task.metadata, "idempotencyScope":task.idempotency_scope,
                                 "workflowAuthorized":True}).fingerprint

    def _defend(self, state, result):
        # Threat identifiers are server-owned. Never infer hostility from a
        # missile-shaped object or attack projectiles targeting another asset.
        threats = [o for o in local_objects(self.ops)
                   if o.get("id") and o.get("type") == "missile"
                   and o.get("targetsCurrentProbe") is True
                   and o.get("status") not in {"resolved", "failed", "cancelled", "intercepted"}]
        if not threats:
            return None
        defenses = state.setdefault("interceptions", {})
        reserved = {d["itemId"] for d in defenses.values() if d.get("itemId")}
        if (state.get("launch") or {}).get("itemId"):
            reserved.add(state["launch"]["itemId"])
        ammo = [i for i in inventory_items(self.ops) if i.get("type") == "missile"
                and not i.get("currentTask") and str(i["id"]) not in reserved]
        for threat in sorted(threats, key=lambda o:(str(o.get("impactAt") or "9999"), str(o["id"]))):
            target = str(threat["id"])
            pending = defenses.get(target)
            if pending and (self.engine.action_was_successful(pending["fingerprint"])
                            or record(self.engine, "specialist_launch:"+pending["fingerprint"]).get("missile")):
                continue
            item = next((i for i in inventory_items(self.ops)
                         if pending and str(i["id"]) == pending["itemId"] and not i.get("currentTask")), None)
            if item is None:
                item = sorted(ammo, key=lambda i:str(i["id"]))[0] if ammo else None
            if item is None:
                return result("defense_hold", "Incoming missile; no available interceptor. Emergency escape remains a separate safety setting.")
            task = self._task("Launch Mission Missile", item["id"],
                              {"missionId":"defense-"+target, "sequence":0}, targetId=target)
            defenses[target] = {"itemId":str(item["id"]), "fingerprint":self._fingerprint(task)}
            return result("intercepting", "Intercepting an incoming missile targeting this probe; interception is not guaranteed.", tasks=(task,))
        return result("defending", "Interceptors accepted; waiting for incoming missiles to clear. This is not confirmation of interception.")

    def _combat(self, settings, state, current, home, result):
        if not settings.get("combatAuthorized"):
            return result("combat_hold", "Combat authorization is disabled.")
        defense = self._defend(state, result)
        if defense is not None:
            return defense
        # Accepted launches are reconciled before return or mission replacement.
        pending = state.get("launch")
        if pending and (self.engine.action_was_successful(pending["fingerprint"])
                        or record(self.engine, "specialist_launch:"+pending["fingerprint"]).get("missile")):
            observed = record(self.engine, "specialist_missile:"+pending["fingerprint"])
            missile = observed.get("missile", {})
            if missile.get("status") not in {"resolved", "failed", "cancelled"}:
                return result("missile_pending", "Awaiting authoritative missile preparation/flight result.")
            if missile.get("status") == "failed" and str(settings.get("missionId") or "") == state.get("missionId"):
                if settings.get("returnHome") and current != home:
                    return self._travel(home, state, result, "Returning after failed preparation.")
                return result("launch_failed", "Missile preparation failed. Review Combat Control, then assign a new mission.")
            if (missile.get("details") or {}).get("destroyed"):
                state.setdefault("destroyed", []).append(pending["targetId"])
            if pending.get("lastMissile"):
                state["completedMission"] = state.get("missionId")
            state["sequence"] = int(state.get("sequence", 0))+1
            state.pop("launch", None)
        mission = str(settings.get("missionId") or "")
        if mission and mission != state.get("missionId"):
            state.update(missionId=mission, returning=False, destroyed=[], launch=None)
        defensive_items = {d.get("itemId") for d in state.get("interceptions", {}).values()}
        ammo = [i for i in inventory_items(self.ops) if i.get("type") == "missile"
                and not i.get("currentTask") and str(i["id"]) not in defensive_items]
        amount = sum(int(i.get("quantity", 1)) for i in ammo)
        target_stock = int(settings.get("missileStock", 1))
        if (settings.get("returnHome") or not mission or state.get("completedMission") == mission or not ammo
                or (current == home and amount < target_stock)):
            state["returning"] = True
        if state.get("returning"):
            shortage = max(0, target_stock-amount)
            if shortage:
                request = state.get("supplyRequest")
                completed = any((request or {}).get("id") in (r["settings"].get("infrastructureCampaign") or {}).get("completedRequests", [])
                                for r in role_rows(self.engine) if r["role"] == "hub")
                if not request or completed:
                    state["refillGeneration"] = int(state.get("refillGeneration", 0))+1
                    state["supplyRequest"] = {"id":f"destroyer-{self.ops.world.probe['id']}-{state['refillGeneration']}", "items":{"missile":shortage}}
            else:
                state.pop("supplyRequest", None)
            if current != home:
                return self._travel(home, state, result, "Returning to the Hub for ammunition.")
            if shortage:
                return result("restocking", f"At home; waiting for {shortage} missiles from the Hub.")
            if mission and state.get("completedMission") != mission and not settings.get("returnHome"):
                state["returning"] = False
            else:
                return result("ready", "Refilled at home; waiting for a new sector mission.")
        target = coordinates(settings.get("targetSector"))
        if target is None:
            return result("awaiting_mission", "Choose a target sector and start a mission.")
        if current != target:
            return self._travel(target, state, result, "Traveling to the assigned combat sector.")
        targets = ship_targets(self.ops)
        targets = {k:v for k,v in targets.items() if k not in state.get("destroyed", [])}
        if not targets:
            scan = (self.ops.world.sector.get("snapshot") or {}).get("sector", self.ops.world.sector)
            if scan.get("knowledgeLevel") != "detailed" or scan.get("sensorMode", "normal") != "normal":
                return result("sensor_hold", "A detailed normal-sensor scan is required before concluding there are no targets.")
            state.update(returning=True, completedMission=mission)
            if current != home:
                return self._travel(home, state, result, "No eligible Others ships remain visible; returning home. Missing targets are not recorded as destroyed.")
            return result("ready", "No eligible Others ships remain visible; awaiting the next mission.")
        item = sorted(ammo, key=lambda i:str(i["id"]))[0]
        task = self._task("Launch Mission Missile", item["id"], state, targetId=sorted(targets)[0])
        state["launch"] = {"fingerprint":self._fingerprint(task), "targetId":task.metadata["targetId"], "lastMissile":amount == 1, "itemId":str(item["id"])}
        return result("engaging", "Preparing one missile against an identified Others ship.", tasks=(task,))

    def _salvage(self, settings, state, current, home, result):
        items = inventory_items(self.ops)
        claims = claimed_ids(self.ops)
        attached = {str(c["id"]):c for c in self.ops.containers.attached()}
        state.setdefault("baselineContainers", list(attached))
        state.setdefault("baselineItems", [str(i["id"]) for i in items])
        cargo = [c for c in attached if c in state.get("cargoContainers", [])
                 or (c == state.get("packingContainer") and float(attached[c].get("usedCapacity", 0)) > 0)]
        loose = [i for i in items if str(i["id"]) in state.get("cargoItems", []) and i.get("type") != "additional_container"]
        pending = state.get("pickup")
        if pending and self.engine.action_was_successful(pending["fingerprint"]):
            workers = self.ops.world.mannies.get("mannies", [])
            busy = any(m.get("currentTask") for m in workers)
            if busy:
                state["pickupObserved"] = True
                return result("recovering", "Waiting for the accepted recovery to complete.")
            gained_boxes = [c for c in attached if c not in pending.get("beforeContainers", [])]
            gained_items = [str(i["id"]) for i in items if str(i["id"]) not in pending.get("beforeItems", [])]
            if not state.pop("pickupObserved", False) and not gained_boxes and not gained_items:
                return result("recovering", "Waiting for recovery inventory telemetry.")
            state["cargoContainers"] = list(dict.fromkeys(state.get("cargoContainers", [])+gained_boxes))
            state["cargoItems"] = list(dict.fromkeys(state.get("cargoItems", [])+gained_items))
            cargo = [c for c in attached if c in state["cargoContainers"]]
            loose = [i for i in items if str(i["id"]) in state["cargoItems"] and i.get("type") != "additional_container"]
            state.setdefault("visitedTargets", []).append(pending["objectId"])
            state.pop("pickup", None)
            state["sequence"] = int(state.get("sequence", 0))+1
            state["returning"] = bool(cargo or loose)
        if settings.get("returnHome"):
            state["returning"] = True
        if state.get("returning"):
            if current != home:
                return self._travel(home, state, result, "Returning recovered cargo to the Hub.")
            from src.operations.hub_receiving import readiness
            ready = readiness(self.engine, settings.get("hubProbeId"))
            if cargo or loose:
                if coordinates(ready.get("sector")) != home or ready.get("status") not in {"idle", "arrived"}:
                    return result("hub_wait", "Waiting for fresh stationary Hub telemetry at home.")
                if cargo:
                    box = cargo[0]
                    if box in claims:
                        return result("cargo_hold", "Recovered container is now claimed by another workflow.")
                    occupant = next((i for i in items if i.get("type") == "manny" and (i.get("container") or {}).get("id") == box), None)
                    if occupant:
                        if float(ready.get("freeCapacity", 0)) < float(occupant.get("containerSpace", .05)):
                            return result("cargo_hold", "Hub needs storage for the recovered Manny.")
                        task = self._task("Transfer Salvage Manny", occupant["id"], state, targetProbeId=int(settings["hubProbeId"]))
                        return result("unloading", task.reason, tasks=(task,))
                    task = self._task("Deliver Salvage Container", box, state, mode="attach_to_probe", objectId=str(settings["hubProbeId"]))
                else:
                    extra = loose[0]
                    if extra.get("type") == "manny":
                        if extra.get("currentTask") or float(ready.get("freeCapacity", 0)) < float(extra.get("containerSpace", .05)):
                            return result("cargo_hold", "Waiting for idle recovered Manny and Hub storage.")
                        task = self._task("Transfer Salvage Manny", extra["id"], state, targetProbeId=int(settings["hubProbeId"]))
                    else:
                        box = next((c for c in attached.values() if str(c["id"]) not in claims and float(c.get("usedCapacity", 0)) == 0
                                    and self.ops.containers.free_capacity(c) >= float(extra.get("containerSpace", 0))), None)
                        if not box:
                            return result("cargo_hold", "An empty onboard container is needed to deliver recovered items.")
                        state["packingContainer"] = str(box["id"])
                        task = self._task("Load Hub Output", extra["id"], state, toContainerId=str(box["id"]))
                return result("unloading", task.reason, tasks=(task,))
            state["returning"] = False
            state.pop("targetSector", None)
            if settings.get("returnHome"):
                return result("ready", "At home; resume salvage when ready.")
        claims = claimed_ids(self.ops)
        lost = set(settings.get("lostObjectIds") or [])
        def eligible(o):
            identifier = str(o.get("id", ""))
            container = str(o.get("containerId", identifier.removeprefix("detached-container-")))
            return (identifier and o.get("salvageable") is True and identifier not in claims and container not in claims
                    and identifier not in state.get("visitedTargets", []) and not o.get("reserved")
                    and not o.get("currentTask") and o.get("type") != "scut_relay")
        candidates = []
        for o in local_objects(self.ops):
            if eligible(o):
                candidates.append((0 if str(o["id"]) in lost else 1, 0, str(o["id"]), current, o))
        for sector in self.ops.galaxy.known_sectors():
            if sector.coordinates == current:
                continue
            for o in objects(sector.observed):
                if eligible(o):
                    route = self.ops.travel.route_to(sector.coordinates)
                    if route and self.ops.travel_safety.scut_route_covered(current, route):
                        candidates.append((0 if str(o["id"]) in lost else 1, current.distance_to(sector.coordinates), str(o["id"]), sector.coordinates, o))
        if not candidates:
            return result("waiting", "No unclaimed recoverable cargo is known inside verified SCUT coverage.")
        _, _, identifier, target, obj = min(candidates, key=lambda c:c[:3])
        if target != current:
            state["targetSector"] = point(target)
            return self._travel(target, state, result, "Traveling to recover observed cargo.")
        is_container = "container" in str(obj.get("type", ""))
        if is_container and self.ops.travel_safety.additional_container_count() >= self.ops.travel_safety.container_break_threshold()-1:
            return result("capacity_hold", "No travel-safe container slot is available for salvage.")
        if not is_container and float(self.ops.world.probe.get("inventory", {}).get("freeCapacity", 0)) < .05:
            return result("capacity_hold", "Insufficient onboard storage for a salvage trip.")
        task = self._task("Recover Salvage", identifier, state, enforceSafeContainerLimit=is_container)
        state["pickup"] = {"objectId":identifier, "fingerprint":self._fingerprint(task),
                           "beforeContainers":list(attached), "beforeItems":[str(i["id"]) for i in items]}
        return result("recovering", "Recovering unclaimed local cargo with one Manny.", tasks=(task,))


def command_blockers(operations, command):
    from src.execution.commands import CommandType as C
    if not command.metadata.get("specialistCampaign"):
        return ("specialist_authorization_required",) if command.type in {C.MANNY_LAUNCH_MISSILE, C.MANNY_SALVAGE} else ()
    from src.execution.translator import TaskCommandTranslator
    row = next((r for r in role_rows(getattr(operations, "data_engine", None))
                if str(r["asset_id"]) == str(command.probe_id)), None)
    if not row or row["role"] not in ROLES:
        return ("specialist_role_changed",)
    decision = SpecialistCampaignService(operations).decide(row["role"], row["settings"])
    for task in decision.tasks:
        proposed = TaskCommandTranslator(operations, command.probe_id).translate(task)
        if proposed and proposed.fingerprint == command.fingerprint:
            return ()
    return ("specialist_state_changed",)
