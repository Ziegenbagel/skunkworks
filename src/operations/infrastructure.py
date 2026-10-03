"""Durable Hub supply and SCUT expansion decisions; no network mutations."""

from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from copy import deepcopy
from math import sqrt
import json
import re

from src.models.galaxy import SectorCoordinates
from src.planner.task import Task


def coordinates(value):
    try:
        return SectorCoordinates.from_api(value)
    except (KeyError, TypeError, ValueError):
        return None


def point(value):
    return {"x": value.x, "y": value.y, "z": value.z}


def objects(value):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from objects(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from objects(nested)


def has_star(value):
    return any(row.get("type") == "star" or row.get("stars") or row.get("star")
               for row in objects(value))


def role_rows(engine):
    if engine is None or not hasattr(engine, "fleet_roles"):
        return []
    result = []
    for row in engine.fleet_roles("probe"):
        row = dict(row)
        try:
            row["settings"] = json.loads(row.get("metadata_json") or "{}")
        except (TypeError, ValueError):
            row["settings"] = {}
        result.append(row)
    return result


def stock(operations):
    return operations.manufacturing.available_inputs()[1]


def inventory_items(operations):
    return operations.world.probe.get("inventory", {}).get("items", [])


def probe_id(value):
    """Normalize Qt's integral decimal IDs without truncating invalid values."""
    try:
        number = Decimal(str(value))
        if number.is_finite() and number > 0 and number == number.to_integral_value():
            return int(number)
    except (InvalidOperation, ValueError):
        pass
    raise ValueError("Choose a valid package receiver.")


def manual_packages(settings):
    requests = list(settings.get("outputRequests") or ())
    legacy = settings.get("outputRequest")
    if legacy and not any(r.get("id") == legacy.get("id") for r in requests):
        requests.insert(0, legacy)
    return requests


def merge_hub_settings(existing, submitted, recipes):
    """Append against persisted requests, never a stale UI copy of the queue."""
    saved = dict(submitted)
    request = saved.pop("enqueuePackage", None)
    saved.pop("outputRequest", None)
    saved["outputRequests"] = deepcopy(manual_packages(existing))
    if request:
        request = deepcopy(request)
        request["targetProbeId"] = probe_id(request.get("targetProbeId"))
        if not request.get("id") or not request.get("items"):
            raise ValueError("Choose a receiver and at least one component.")
        for kind, quantity in request["items"].items():
            if kind in {"manny", "additional_container"} or recipes is None or recipes.get(kind) is None:
                raise ValueError("Choose a component from the recipe list.")
            request["items"][kind] = probe_id(quantity)
        if not any(r["id"] == request["id"] for r in saved["outputRequests"]):
            saved["outputRequests"].append(request)
    return saved


def local_relays(operations):
    return {str(row["id"]): row for row in objects(operations.world.sector)
            if row.get("type") == "scut_relay" and row.get("id") is not None}


@dataclass(frozen=True)
class InfrastructureDecision:
    phase: str
    summary: str
    state: dict = field(default_factory=dict)
    tasks: tuple = ()
    destination: SectorCoordinates | None = None
    production: dict = field(default_factory=dict)
    packages: tuple = ()


class RelayCampaignService:
    def __init__(self, operations):
        self.operations = operations

    @staticmethod
    def signal_direction(alerts):
        for alert in reversed(list(alerts)):
            if alert.get("type") != "anomaly_detected":
                continue
            match = re.search(r"direction\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", alert.get("message", ""))
            origin = coordinates((alert.get("sector") or {}).get("relative"))
            if match and origin:
                vector = dict(zip(("x", "y", "z"), map(int, match.groups())))
                if any(vector.values()):
                    return {"origin": point(origin), "vector": vector}
        return None

    def candidates(self, settings, state):
        current = self.operations.travel.current_sector()
        relays = []
        for response in self.operations.world.hazard_context.get("scutNetworks", []):
            for relay in response.get("network", {}).get("relays", []):
                where = coordinates((relay.get("sector") or {}).get("relative"))
                if where and relay.get("status") == "on":
                    relays.append((where, int(relay.get("coverageRadiusSectors", 0))))
        if not current or not relays:
            return []
        radius = max(r for _, r in relays)
        # FCC volume offsets are reused for all candidate sites. Use the live
        # relay radius; never invent Euclidean coverage or an API range.
        offsets = [SectorCoordinates(x, y, z)
                   for x in range(-radius, radius + 1)
                   for y in range(-radius, radius + 1)
                   for z in range(-radius, radius + 1)
                   if (x + y + z) % 2 == 0 and max(abs(x), abs(y), abs(z), (abs(x)+abs(y)+abs(z))//2) <= radius]
        direction = state.get("signalDirection") if settings.get("expansionMode") == "signal" else None
        if settings.get("expansionMode") == "direction":
            home, target = coordinates(settings.get("home")), coordinates(settings.get("direction"))
            if home and target:
                direction = {"origin": point(home), "vector": {axis: getattr(target, axis)-getattr(home, axis) for axis in "xyz"}}
        if settings.get("expansionMode", "auto") != "auto" and not direction:
            return []
        reserved_sites = {coordinates((r["settings"].get("infrastructureCampaign") or {}).get("target"))
                          for r in role_rows(getattr(self.operations, "data_engine", None))
                          if r["role"] == "relay_placement" and str(r["asset_id"]) != str(self.operations.world.probe["id"])}
        result = []
        for record in self.operations.galaxy.known_sectors():
            site = record.coordinates
            if site in reserved_sites or point(site) in state.get("completedSites", []) or not has_star(record.observed) or any(site == r[0] for r in relays):
                continue
            route = self.operations.travel.route_to(site) if site != current else ()
            if site != current and (not route or self.operations.travel_safety.scut_route_covered(current, route) is not True):
                continue
            if not any(site.distance_to(where) <= r for where, r in relays):
                continue
            alignment = 1.0
            if direction:
                vector = [direction["vector"][a] for a in "xyz"]
                delta = [getattr(site, a)-getattr(current, a) for a in "xyz"]
                norm = sqrt(sum(v*v for v in vector))*sqrt(sum(v*v for v in delta))
                alignment = sum(a*b for a,b in zip(vector, delta))/norm if norm else 0
                if alignment <= 0:
                    continue
            gain = sum(not any(SectorCoordinates(site.x+offset.x, site.y+offset.y, site.z+offset.z).distance_to(where) <= r
                               for where, r in relays) for offset in offsets)
            if gain:
                result.append((gain*alignment, gain, -len(route), site))
        return sorted(result, reverse=True)

    def decide(self, settings, alerts=()):
        state = deepcopy(settings.get("infrastructureCampaign") or {})
        def decision(phase, summary, **kwargs):
            if phase == "returning" and settings.get("expansionMode") == "signal" and not state.get("resumePosition"):
                # Preserve the frontier across home resupply. This is a travel
                # waypoint, not a new deployment target at an existing relay.
                previous = current if current != home else coordinates(
                    (state.get("completedSites") or [None])[-1])
                if previous is not None and previous != home:
                    state["resumePosition"] = point(previous)
            if phase == "returning" and not state.get("supplyRequest"):
                available_now = stock(self.operations)
                missing = {k:max(0, n-int(available_now.get(k,0))) for k,n in kit.items()}
                if any(missing.values()):
                    state["restockGeneration"] = int(state.get("restockGeneration",0))+1
                    state["supplyRequest"] = {
                        "id":f"relay-{self.operations.world.probe['id']}-{state.get('cycle',0)}-{state['restockGeneration']}",
                        "items":{k:n for k,n in missing.items() if n}}
            return InfrastructureDecision(phase, summary, state=dict(state), **kwargs)
        if not settings.get("infrastructureEnabled"):
            return decision("paused", "SCUT Network Expansion is paused.")
        home = coordinates(settings.get("home"))
        current = self.operations.travel.current_sector()
        if home is None or current is None:
            return decision("blocked", "Set a valid home sector before enabling SCUT Network Expansion.")
        if (settings.get("expansionMode") == "signal" and state.get("returning")
                and not state.get("resumePosition")):
            previous = state.get("resumeTarget") or (state.get("completedSites") or [None])[-1]
            if coordinates(previous) is not None:
                state["resumePosition"] = deepcopy(previous)
        if settings.get("expansionMode") == "signal" and not state.get("signalDirection"):
            direction = self.signal_direction(alerts)
            if not direction:
                return decision("signal_missing", "No saved signal alert with an origin and direction is available.")
            state["signalDirection"] = direction
        available = stock(self.operations)
        beacon_mode = settings.get("beaconMode", "final")
        target_stock = max(1, int(settings.get("relayStock", 4)))
        kit = {"scut_relay": target_stock, "integrated_circuit": target_stock}
        refill_beacons = settings.get("refillBeacons", beacon_mode != "none")
        if refill_beacons:
            default_beacons = target_stock if beacon_mode == "every" else 1
            kit["scut_transit_beacon"] = int(settings.get("beaconStock", default_beacons))
        resume_position = coordinates(state.get("resumePosition"))
        if resume_position is not None and not state.get("returning"):
            if current != resume_position:
                return decision("resuming", "Returning to the previous expansion position; using direct beacon transit when available.",
                                destination=resume_position)
            state.pop("resumePosition", None)
        target = coordinates(state.get("target"))
        if target:
            if current != target:
                return decision("travelling", "Travelling to the selected relay site inside SCUT.", destination=target)
            relays = local_relays(self.operations)
            relay = relays.get(str(state.get("relayId")))
            engine = getattr(self.operations, "data_engine", None)
            deployed = bool(engine is not None and state.get("deployFingerprint")
                            and engine.action_was_successful(state["deployFingerprint"]))
            if relay is None and state.get("itemId") and deployed:
                candidates = [r for key, r in relays.items() if key not in state.get("existingRelays", [])]
                if len(candidates) == 1:
                    relay = candidates[0]
                    state["relayId"] = str(relay["id"])
                elif len(candidates) > 1:
                    return decision("ambiguous_relay", "Multiple new relays appeared; pause and review the selected site.")
            metadata = {"expectedSector": point(current), "relayCampaign": True}
            scope = f"relay:{state.get('cycle', 0)}:{target.x}:{target.y}:{target.z}"
            if relay is None:
                item_id = state.get("itemId")
                if not item_id:
                    item = next((i for i in inventory_items(self.operations) if i.get("type") == "scut_relay" and i.get("id")), None)
                    if item is None:
                        state["resumeTarget"] = state.pop("target")
                        state["returning"] = True
                        return decision("returning", "The selected relay kit is missing; returning home before continuing this site.", destination=home)
                    item_id = state["itemId"] = str(item["id"])
                    state["existingRelays"] = list(relays)
                if not any(str(i.get("id")) == item_id for i in inventory_items(self.operations)):
                    if deployed:
                        return decision("deploying", "Deployment accepted; waiting for the live relay object.")
                    state["resumeTarget"] = state.pop("target")
                    state.pop("itemId", None)
                    state["returning"] = True
                    return decision("returning", "Relay kit unavailable before deployment; returning home to restock.", destination=home)
                task = Task(action="Deploy SCUT Relay", target=item_id, category="infrastructure", priority=1,
                            reason="Deploy the reserved relay at the selected star.", workflow_authorized=True,
                            idempotency_scope=scope+":deploy", metadata=metadata)
                from src.execution.commands import Command, CommandType
                state["deployFingerprint"] = Command(CommandType.DEPLOY_SCUT_RELAY,self.operations.world.probe["id"],
                    {"itemId":item_id},task.reason,1,metadata={**metadata,"workflowAuthorized":True,"idempotencyScope":task.idempotency_scope}).fingerprint
                return decision("deploying", task.reason, tasks=(task,))
            if relay.get("status") != "on":
                action, explanation = "Activate SCUT Relay", "Activating the placed relay with an Integrated Circuit."
            elif beacon_mode != "none" and state.get("placeBeacon") and not relay.get("isTransitBeacon", relay.get("hasTransitBeacon", False)):
                action, explanation = "Install SCUT Beacon", "Installing the selected transit beacon before leaving this relay."
            else:
                state = {k: v for k, v in state.items() if k not in {"target", "relayId", "itemId", "existingRelays", "placeBeacon", "deployFingerprint"}}
                state.setdefault("completedSites", []).append(point(target))
                state["cycle"] = int(state.get("cycle", 0)) + 1
                return decision("site_complete", "Relay site complete; refreshing coverage before selecting the next site.")
            from src.execution.commands import Command, CommandType
            installation = Command(CommandType.MANNY_ACTIVATE_RELAY if action == "Activate SCUT Relay" else CommandType.MANNY_INSTALL_BEACON,
                self.operations.world.probe["id"], {"relayId":int(relay["id"])}, explanation, 1,
                metadata={**metadata,"idempotencyScope":scope+":"+action})
            installation_accepted = engine is not None and engine.action_was_successful(installation.fingerprint)
            if installation_accepted:
                return decision("installing", "Site installation accepted; waiting for live completion.")
            needed = "integrated_circuit" if action == "Activate SCUT Relay" else "scut_transit_beacon"
            if available.get(needed, 0) < 1:
                # An accepted install may already have consumed its item. Hold
                # while a Manny is still on the task before considering resupply.
                active = any("relay" in str(m.get("currentTask", "")) or "beacon" in str(m.get("currentTask", ""))
                             for m in self.operations.world.mannies.get("mannies", []))
                if not active and not installation_accepted:
                    state["resumeTarget"] = state.pop("target")
                    state["returning"] = True
                    return decision("returning", "Missing site components; returning home before finishing this relay.", destination=home)
            task = Task(action=action, target=str(relay["id"]), category="infrastructure", priority=1,
                        reason=explanation, workflow_authorized=True, idempotency_scope=scope+":"+action, metadata=metadata)
            return decision("activating" if action == "Activate SCUT Relay" else "beacon", explanation, tasks=(task,))
        if state.get("returning"):
            if current != home:
                return decision("returning", "Returning home for Hub restocking.", destination=home)
            missing = {k: max(0, n-int(available.get(k, 0))) for k, n in kit.items()}
            if any(missing.values()):
                request = state.get("supplyRequest") or {}
                completed = any(request.get("id") in (r["settings"].get("infrastructureCampaign") or {}).get("completedRequests", [])
                                for r in role_rows(getattr(self.operations, "data_engine", None)) if r["role"] == "hub")
                if not request or completed:
                    state["restockGeneration"] = int(state.get("restockGeneration", 0))+1
                    state["supplyRequest"] = {"id": f"relay-{self.operations.world.probe['id']}-{state.get('cycle', 0)}-{state['restockGeneration']}",
                                              "items": {k:n for k,n in missing.items() if n}}
                return decision("restocking", "At home, waiting for the Hub to supply the requested relay kit.")
            state.pop("supplyRequest", None)
            if not refill_beacons and beacon_mode != "none" and available.get("scut_transit_beacon", 0) < 1:
                return decision("beacon_refill_disabled", "At home with no beacons. Enable beacon refills, supply one manually, or choose no beacon placement.")
            state.pop("returning", None)
            if state.get("resumeTarget"):
                state["target"] = state.pop("resumeTarget")
            return decision("restocked", "Relay kit replenished; expansion will resume.")
        usable = min(int(available.get("scut_relay", 0)), int(available.get("integrated_circuit", 0)))
        if usable <= 0 or (beacon_mode != "none" and available.get("scut_transit_beacon", 0) < 1):
            state["returning"] = True
            return decision("returning", "Relay or beacon stock exhausted; returning home for resupply.", destination=home)
        candidates = self.candidates(settings, state)
        if not candidates:
            return decision("waiting_for_sites", "No mapped star offers covered expansion in this direction. Scan more sectors inside SCUT.")
        selected = candidates[0][3]
        state["target"] = point(selected)
        state["placeBeacon"] = beacon_mode == "every" or (beacon_mode == "final" and usable == 1)
        return decision("travelling", f"Selected {selected.x}:{selected.y}:{selected.z} for {candidates[0][1]} new covered sectors.", destination=selected)


class HubCampaignService:
    def __init__(self, operations):
        self.operations = operations

    def cleanup_task(self, delivery, excluded_container_ids=()):
        """Move only surplus/unrelated contents to unreserved onboard storage."""
        source = str(delivery["containerId"])
        inventory = self.operations.world.probe.get("inventory", {})
        destinations = [c for c in inventory.get("containers", [])
                        if c.get("id") is not None and str(c["id"]) not in {source, *excluded_container_ids}]
        from src.operations.hub_receiving import receipts
        incoming = {op.metadata["containerId"] for op in receipts(getattr(self.operations,"data_engine",None), self.operations.world.probe["id"])}
        destinations = [c for c in destinations if str(c["id"]) not in incoming]
        cargo = [i for i in inventory_items(self.operations) if str((i.get("container") or {}).get("id")) == source]
        represented = {str(i.get("mannyId") or i.get("id")) for i in cargo if i.get("type") == "manny"}
        recipes = getattr(self.operations.manufacturing, "recipes", None)
        manny_recipe = recipes.get("manny") if recipes else None
        for manny in self.operations.world.mannies.get("mannies", []):
            if str((manny.get("container") or {}).get("id")) == source and str(manny.get("id")) not in represented:
                cargo.append({**manny,"type":"manny","containerSpace":manny.get("containerSpace",
                    ((manny_recipe or {}).get("output") or {}).get("containerSpace"))})
        remaining = dict(delivery["items"])
        candidates = []
        for item in cargo:
            kind, quantity = item.get("type"), int(item.get("quantity",1))
            if remaining.get(kind,0) >= quantity:
                remaining[kind] -= quantity
                continue
            if item.get("currentTask") or kind == "additional_container":
                continue
            payload = {"kind":"item", "itemId":str(item["id"])}
            if kind == "manny":
                manny_id = str(item.get("mannyId") or item["id"])
                manny = next((m for m in self.operations.world.mannies.get("mannies",[]) if str(m.get("id")) == manny_id), {})
                if manny.get("currentTask"):
                    continue
                payload = {"kind":"manny", "targetMannyId":manny_id}
            if item.get("containerSpace") is not None:
                candidates.append((payload, float(item["containerSpace"]), kind))
        for row in inventory.get("resourceStocks", []):
            if row.get("type") not in {"metals", "ice", "carbon_compounds"}:
                continue
            for placement in row.get("containers", []):
                if str((placement.get("container") or {}).get("id")) == source and float(placement.get("amount",0)) > 0:
                    candidates.append(({"kind":"resource", "resourceType":row["type"], "fromContainerId":source},
                                       float(placement["amount"]), row["type"]))
        for payload, size, label in candidates:
            suitable = [c for c in destinations if self.operations.containers.free_capacity(c) >= (min(size,.01) if payload["kind"] == "resource" else size)]
            if not suitable:
                continue
            destination = min(suitable, key=self.operations.containers.free_capacity)
            payload = {**payload,"toContainerId":str(destination["id"])}
            if payload["kind"] == "resource":
                payload["amount"] = min(size,self.operations.containers.free_capacity(destination))
            signature = json.dumps(payload, sort_keys=True)
            if delivery.get("cleanupSignature") != signature:
                delivery["cleanupGeneration"] = int(delivery.get("cleanupGeneration",0))+1
                delivery["cleanupSignature"] = signature
            return Task(action="Clear Hub Container", category="infrastructure", priority=1,
                target=source, reason=f"Move unrelated {label.replace('_',' ')} into other Hub storage before packing.",
                workflow_authorized=True,
                idempotency_scope=f"hub:{delivery['id']}:{delivery.get('shipment',0)}:cleanup:{delivery['cleanupGeneration']}",
                metadata={"hubCampaign":True,"hubCleanup":True,"requestId":delivery["id"],
                    "expectedSector":point(self.operations.travel.current_sector()), "storageMove":payload})
        return None

    def receiver_state(self, target_id, fingerprint=None):
        from src.operations.hub_receiving import readiness, receipts
        ready = readiness(getattr(self.operations, "data_engine", None), probe_id(target_id))
        if not ready:
            return ready, "receiver_refresh", "Receiver telemetry needs refreshing before handoff."
        if coordinates(ready.get("sector")) != self.operations.travel.current_sector():
            return ready, "waiting_for_receiver", "Receiver has not arrived at the Hub sector."
        fleet = (self.operations.world.fleet or {}).get("probes", [])
        target = next((p for p in fleet if probe_id(p["id"]) == probe_id(target_id)), {})
        if ready.get("status", target.get("status")) not in {"idle", "arrived"}:
            return ready, "waiting_for_receiver", "Receiver is not stationary at the Hub."
        if any(op.metadata.get("handoffFingerprint") != fingerprint
               for op in receipts(getattr(self.operations, "data_engine", None), probe_id(target_id))):
            return ready, "receiver_unloading", "Receiver must unload and return its previous Hub container."
        count, limit = ready.get("containerCount", 0), ready.get("safeLimit", 0)
        if count >= limit:
            return ready, "", f"Temporary delivery allowed while stationary ({count} containers; travel-safe maximum {limit}). Unload and return delivery container before departure."
        return ready, "", f"Receiver at Hub: {count}/{limit} additional containers; {float(ready.get('freeCapacity',0)):.2f} ECE free for unloading."

    def production_targets(self, requested):
        targets = dict(requested)
        available = stock(self.operations)
        planner = getattr(self.operations.manufacturing, "production_plan", None)
        if planner is not None:
            for recipe, amount in requested.items():
                if available.get(recipe, 0) >= amount:
                    continue
                plan = planner(recipe, use_inventory_items=True, include_operational_constraints=False)
                for component, consumed in (plan or {}).get("consumed_inventory_items", {}).items():
                    if component in requested:
                        targets[component] = max(targets[component], requested[component] + consumed)
        for component, held in assembly_claims(self.operations).items():
            if component in targets:
                targets[component] += held
        return targets

    def decide(self, settings, roles=()):
        """Collect every package before deciding which shipment can advance."""
        state = deepcopy(settings.get("infrastructureCampaign") or {})
        if not settings.get("infrastructureEnabled"):
            return InfrastructureDecision("paused", "Hub automation is paused.", state=state)
        current = self.operations.travel.current_sector()
        queue = deepcopy(state.get("packageQueue") or [])
        legacy = state.get("delivery")
        if legacy and not any(r["id"] == legacy["id"] for r in queue):
            queue.insert(0, deepcopy(legacy))
        completed = list(state.get("completedRequests") or [])
        incoming = []
        for row in roles:
            config = row.get("settings", {})
            request = (config.get("infrastructureCampaign") or {}).get("supplyRequest")
            if (row["role"] == "relay_placement" and config.get("infrastructureEnabled")
                    and request and row.get("asset_id") is not None
                    and current is not None and coordinates(config.get("home")) == current):
                incoming.append({**request, "targetProbeId":probe_id(row["asset_id"]), "source":"automatic"})
        incoming.extend({**r, "source":"manual"} for r in manual_packages(settings))
        for request in incoming:
            if request["id"] not in completed and not any(r["id"] == request["id"] for r in queue):
                queue.append(deepcopy(request))
        queue = [r for r in queue if r["id"] not in completed]
        for request in queue:
            request["targetProbeId"] = probe_id(request["targetProbeId"])
            request.setdefault("requestedItems", dict(request["items"]))
        # Keep accepted shipments and their identities through receiver waits.
        # A blocked recipient must not prevent another package from progressing.
        chosen = None
        chosen_id = None
        evaluated = set()
        packaging_target = 0
        for request in list(queue):
            other_boxes = {str(r["containerId"]) for r in queue
                           if r["id"] != request["id"] and r.get("containerId")}
            projected = {**settings, "infrastructureCampaign":{**state, "delivery":request}}
            result = self._advance_delivery(projected, roles, excluded_container_ids=other_boxes)
            evaluated.add(request["id"])
            advanced = result.state.get("delivery")
            index = next(i for i,r in enumerate(queue) if r["id"] == request["id"])
            if advanced:
                queue[index] = {**advanced, "phase":result.phase, "summary":result.summary}
            else:
                queue.pop(index)
            completed = list(dict.fromkeys(completed + list(result.state.get("completedRequests", []))))
            packaging_target = max(packaging_target, result.production.get("additional_container", 0))
            if chosen is None or result.tasks or result.phase == "delivered":
                chosen, chosen_id = result, request["id"]
            if result.tasks or result.phase == "delivered":
                break
        if chosen is None:
            projected = {**settings, "infrastructureCampaign":{**state, "delivery":None}}
            chosen = self._advance_delivery(projected, roles)
        state["packageQueue"] = queue
        state["completedRequests"] = completed
        selected = next((r for r in queue if r["id"] == chosen_id), None)
        if selected:
            state["delivery"] = deepcopy(selected)
        else:
            state.pop("delivery", None)
        requested = {}
        for request in queue:
            for component, quantity in request["items"].items():
                requested[component] = requested.get(component, 0) + int(quantity)
        production = self.production_targets(requested)
        if packaging_target:
            production["additional_container"] = packaging_target
        fleet = {probe_id(p["id"]):p for p in (self.operations.world.fleet or {}).get("probes", [])}
        pool = dict(stock(self.operations))
        active_count = getattr(self.operations.manufacturing, "active_production_count", lambda _: 0)
        active_pool = {kind:active_count(kind) for r in queue for kind in r["items"]}
        loaded_by_id = {}
        for r in queue:
            loaded = {}
            for item in inventory_items(self.operations):
                if r.get("containerId") and str((item.get("container") or {}).get("id")) == r["containerId"]:
                    kind = item.get("type")
                    loaded[kind] = loaded.get(kind, 0) + int(item.get("quantity", 1))
            loaded_by_id[r["id"]] = loaded
            for kind, amount in loaded.items():
                pool[kind] = max(0, pool.get(kind, 0)-amount)
        packages = []
        for r in queue:
            loaded = loaded_by_id[r["id"]]
            available, missing, crafting = {}, {}, {}
            for kind, amount in r["items"].items():
                allocated = min(max(0, amount-loaded.get(kind,0)), pool.get(kind,0))
                pool[kind] = pool.get(kind,0)-allocated
                available[kind] = allocated
                shortage = max(0, amount-loaded.get(kind,0)-allocated)
                crafting[kind] = min(shortage, active_pool.get(kind,0))
                active_pool[kind] = active_pool.get(kind,0)-crafting[kind]
                missing[kind] = shortage-crafting[kind]
            ready, blocker, receiver_summary = self.receiver_state(r["targetProbeId"], r.get("dispatchFingerprint"))
            packages.append({"id":r["id"], "targetProbeId":r["targetProbeId"],
            "targetName":fleet.get(r["targetProbeId"], {}).get("name") or f"Probe {r['targetProbeId']}",
            "items":dict(r["items"]), "shipment":int(r.get("shipment",0)),
            "requestedItems":r["requestedItems"], "loadedItems":loaded, "availableItems":available,
            "missingItems":missing, "craftingItems":crafting, "containerId":r.get("containerId", ""),
            "receiverSummary":receiver_summary, "receiverBlocker":blocker,
            "source":r.get("source","manual"), "phase":r.get("phase","queued") if r["id"] in evaluated else "queued",
            "summary":r.get("summary","Queued for preparation.") if r["id"] in evaluated else "Waiting for the Hub's next packing turn."})
        return replace(chosen, state=state, production=production, packages=tuple(packages))

    def _advance_delivery(self, settings, roles=(), *, excluded_container_ids=()):
        state = deepcopy(settings.get("infrastructureCampaign") or {})
        def decision(phase, summary, **kwargs):
            return InfrastructureDecision(phase, summary, state=dict(state), **kwargs)
        if not settings.get("infrastructureEnabled"):
            return decision("paused", "Hub automation is paused.")
        current = self.operations.travel.current_sector()
        if current is None:
            return decision("waiting", "Waiting for the Hub's sector telemetry.")
        engine = getattr(self.operations, "data_engine", None)
        for row in roles:
            config = row.get("settings", {})
            if coordinates(config.get("home")) != current:
                continue
            returned_ids = (config.get("infrastructureCampaign") or {}).get("resupplyReturns", {})
            returned = next((c for c in self.operations.containers.detached()
                             if c.get("mode") == "drifting"
                             and str(c.get("containerId", c.get("id"))) in returned_ids), None)
            if returned:
                container_id = str(returned.get("containerId", returned.get("id")))
                task = Task(action="Recover Transport Container", category="infrastructure", priority=1,
                    target=str(returned["id"]), reason="Recover the empty container returned to open a resupply slot.",
                    workflow_authorized=True, idempotency_scope=returned_ids[container_id]+":slot:recover:"+container_id,
                    metadata={"source":"drifting", "expectedSector":point(current)})
                return decision("recovering_return", task.reason, tasks=(task,))
        if engine is not None and hasattr(engine, "operation_records"):
            from src.operations.mission import OperationStore, OperationState
            returns = {op.metadata["containerId"]: op for op in OperationStore(engine).all(OperationState.COMPLETED)
                       if op.objective == "hub_container_receipt" and op.state == OperationState.COMPLETED
                       and op.metadata.get("sourceProbeId") == self.operations.world.probe["id"]}
            returned = next((c for c in self.operations.containers.detached() if c.get("mode") == "drifting"
                             and str(c.get("containerId", c.get("id"))) in returns), None)
            if returned:
                receipt = returns[str(returned.get("containerId", returned.get("id")))]
                task = Task(action="Recover Transport Container", category="infrastructure", priority=1,
                            target=str(returned["id"]), reason="Recover the empty container returned by a stocked probe.",
                            workflow_authorized=True, idempotency_scope=receipt.id+":recover",
                            metadata={"source":"drifting", "expectedSector":point(current)})
                return decision("recovering_return", task.reason, tasks=(task,))
        delivery = state.get("delivery")
        completed = state.get("completedRequests", [])
        fleet = {probe_id(p["id"]): p for p in (self.operations.world.fleet or {}).get("probes", [])}
        if not delivery:
            # Transport routes drop resource containers at the Hub. Recover
            # them through the same authoritative container boundary.
            if settings.get("receiveContainers", True):
                drifting = next((c for c in self.operations.containers.detached()
                                 if c.get("mode") == "drifting"), None)
                if drifting:
                    task = Task(action="Recover Transport Container", category="transport", target=str(drifting["id"]),
                        reason="Recover an incoming Hub supply container.", priority=2, workflow_authorized=True,
                        metadata={"source": "drifting", "expectedSector": point(current)})
                    return decision("receiving", task.reason, tasks=(task,))
            return decision("producing", "Maintaining configured production targets; waiting for a delivery request.")
        requested = {k:int(n) for k,n in delivery.get("items", {}).items() if int(n) > 0}
        if not requested:
            return decision("blocked", "The output batch must contain at least one item.")
        attached = {str(c["id"]): c for c in self.operations.containers.attached()
                    if str(c["id"]) not in excluded_container_ids}
        container_id = delivery.get("containerId")
        if container_id and container_id not in attached:
            engine = getattr(self.operations, "data_engine", None)
            accepted = engine is not None and delivery.get("dispatchFingerprint") and engine.action_was_successful(delivery["dispatchFingerprint"])
            if not accepted:
                return decision("container_missing", "The delivery container is missing without an accepted handoff; review it before continuing.")
            remaining = {key: max(0, int(n)-int(delivery.get("shippedItems", {}).get(key, 0)))
                         for key,n in delivery.get("items", {}).items()}
            if any(remaining.values()):
                state["delivery"] = {"id":delivery["id"], "targetProbeId":delivery["targetProbeId"],
                                     "requestedItems":delivery.get("requestedItems", dict(delivery["items"])),
                                     "source":delivery.get("source","manual"),
                                     "items": {k:n for k,n in remaining.items() if n}, "shipment":int(delivery.get("shipment", 0))+1}
            else:
                state["completedRequests"] = completed + [delivery["id"]]
                state.pop("delivery", None)
            return decision("delivered", "Accepted output handoff confirmed; preparing any remaining items.")
        ready, receiver_blocker, receiver_summary = self.receiver_state(delivery["targetProbeId"], delivery.get("dispatchFingerprint"))
        if not container_id:
            container = next((c for c in attached.values() if float(c.get("usedCapacity", c.get("used", 0)) or 0) == 0
                              and float(c.get("capacity", 1)) >= 1), None)
            if not container:
                return decision("preparing_container", "Crafting an empty container for the output batch.",
                                production={**self.production_targets(requested), "additional_container": len(self.operations.containers.attached())+1})
            container_id = delivery["containerId"] = str(container["id"])
        items = [i for i in inventory_items(self.operations)
                 if str((i.get("container") or {}).get("id")) not in excluded_container_ids]
        cargo = [i for i in items if str((i.get("container") or {}).get("id")) == container_id]
        counts = {k: sum(int(i.get("quantity", 1)) for i in cargo if i.get("type") == k) for k in requested}
        # A container is never handed off with unrelated resources, Mannys, or
        # surplus items. Storage routing rules may have changed during loading.
        raw = self.operations.world.probe.get("inventory", {}).get("resourceStocks", [])
        extra_cargo = any(i.get("type") not in requested for i in cargo) or any(counts[k] > requested[k] for k in counts)
        extra_cargo |= any(float(p.get("amount", 0)) > 0 and str((p.get("container") or {}).get("id")) == container_id
                           for r in raw for p in r.get("containers", []))
        extra_cargo |= any(str((m.get("container") or {}).get("id")) == container_id
                           for m in self.operations.world.mannies.get("mannies", []))
        if extra_cargo:
            task = self.cleanup_task(delivery, excluded_container_ids)
            if task:
                return decision("clearing_container", task.reason, tasks=(task,))
            return decision("cargo_conflict", "Waiting to clear delivery cargo: suitable Hub storage, idle cargo, or cargo-size telemetry is unavailable.")
        delivery.pop("cleanupSignature", None)
        scope = f"hub:{delivery['id']}:{delivery.get('shipment', 0)}"
        metadata = {"hubCampaign": True, "expectedSector": point(current), "requestId": delivery["id"]}
        loaded_size = sum(float(i.get("containerSpace", 0) or 0) for i in cargo)
        receiver_free = max(0, float(ready.get("freeCapacity", 0))-loaded_size) if not receiver_blocker else float("inf")
        free = min(self.operations.containers.free_capacity(attached[container_id]), receiver_free)
        if not receiver_blocker and receiver_free <= .00001 and not cargo:
            return decision("receiver_storage_full", "Stock preparation continues; receiver has no permanent space to unload another shipment.")
        # Infer remaining component sizes from the live recipe or a stored
        # example even before the next unit finishes crafting.
        recipes = getattr(self.operations.manufacturing, "recipes", None)
        sizes = []
        for kind, quantity in requested.items():
            if counts[kind] >= quantity:
                continue
            recipe = recipes.get(kind) if recipes else None
            size = ((recipe or {}).get("output") or {}).get("containerSpace")
            if size is None:
                size = next((i.get("containerSpace",0) for i in items if i.get("type") == kind), 0)
            sizes.append(float(size or 0))
        full = bool(cargo) and (free <= 0.00001 or (sizes and all(size > free + .00001 for size in sizes)))
        if not receiver_blocker and loaded_size > float(ready.get("freeCapacity", 0)) + .00001:
            return decision("receiver_storage_full", "Receiver needs more permanent storage space to unload this batch.")
        if all(counts[k] >= requested[k] for k in requested) or full:
            if receiver_blocker:
                return decision(receiver_blocker, "Shipment packed. " + receiver_summary)
            from src.operations.hub_receiving import cargo_fits_storage
            if not cargo_fits_storage(cargo, ready):
                return decision("receiver_storage_full", "Shipment packed; its contents do not fit into the receiver's own storage slots. Free permanent space before handoff.")
            delivery["shippedItems"] = counts
            delivery["dispatching"] = True
            task = Task(action="Deliver Hub Container", target=container_id, category="infrastructure", priority=1,
                        reason="Hand the completed output batch to the selected probe.", workflow_authorized=True,
                        idempotency_scope=scope+":deliver", metadata={**metadata, "mode":"attach_to_probe", "objectId": str(delivery["targetProbeId"])})
            from src.execution.commands import Command, CommandType
            delivery["dispatchFingerprint"] = Command(type=CommandType.MANNY_DETACH_STORAGE_CONTAINER,
                probe_id=self.operations.world.probe["id"], payload={"containerId":container_id, "mode":"attach_to_probe", "objectId":str(delivery["targetProbeId"])},
                reason=task.reason, priority=1, metadata={**task.metadata, "idempotencyScope":task.idempotency_scope}).fingerprint
            return decision("delivering", task.reason, tasks=(task,), production=self.production_targets(requested))
        for item_type, count in requested.items():
            if counts[item_type] >= count:
                continue
            item = next((i for i in items if i.get("type") == item_type and i.get("id") and i not in cargo
                         and 0 < int(i.get("quantity", 1)) <= count-counts[item_type] and not i.get("currentTask")
                         and float(i.get("containerSpace", 0) or 0) <= free + 0.00001), None)
            if item:
                task = Task(action="Load Hub Output", target=str(item["id"]), category="infrastructure", priority=1,
                            reason=f"Load {item_type.replace('_', ' ')} into the reserved delivery container.", workflow_authorized=True,
                            idempotency_scope=scope+":load:"+str(item["id"]), metadata={**metadata, "toContainerId":container_id})
                return decision("loading", task.reason, tasks=(task,), production=self.production_targets(requested))
        return decision("producing", "Building the requested output batch from delivered resources.", production=self.production_targets(requested))


def protected_role_items(operations):
    """Physical infrastructure stock stays out of unrelated recursive crafts."""
    rows = role_rows(getattr(operations, "data_engine", None))
    if not rows:
        return {}
    probe_id = str(operations.world.probe.get("id"))
    row = next((r for r in rows if str(r["asset_id"]) == probe_id), None)
    if not row or not row["settings"].get("infrastructureEnabled"):
        return {}
    settings = row["settings"]
    if row["role"] == "relay_placement":
        # Protect all carried relays/beacons; activation is the only owner of ICs.
        available = stock(operations)
        return {key: available.get(key, 0) for key in ("scut_relay", "scut_transit_beacon", "integrated_circuit")}
    state = settings.get("infrastructureCampaign") or {}
    requests = state.get("packageQueue") or ([state["delivery"]] if state.get("delivery") else [])
    protected = {}
    if row["role"] == "hub":
        for request in requests:
            for kind, amount in request.get("items", {}).items():
                protected[kind] = protected.get(kind,0)+int(amount)
    return protected


def infrastructure_blockers(operations, command):
    from src.execution.commands import CommandType as C
    protected = protected_role_items(operations)
    if not protected:
        return ()
    needed = {}
    if command.type in {C.MANNY_CRAFT, C.ATOMIC_PRINTER_CRAFT}:
        plan = operations.manufacturing.production_plan(command.payload.get("recipe"), use_inventory_items=True,
                                                       include_operational_constraints=False)
        needed = (plan or {}).get("consumed_inventory_items", {})
    elif command.type == C.MANNY_ASSEMBLE_PROBE:
        from src.planner.assembly import PROBE_ASSEMBLY_REQUIREMENTS
        needed = dict(PROBE_ASSEMBLY_REQUIREMENTS.get(command.payload.get("model"), ()))
    elif command.type == C.MANNY_DETACH_STORAGE_CONTAINER and not (command.metadata.get("hubCampaign") or command.metadata.get("hubReceipt") or command.metadata.get("resupplySlot")):
        return ("cargo_reserved_by_infrastructure",)
    available = stock(operations)
    if any(available.get(key, 0)-min(n, available.get(key, 0)) < needed.get(key, 0) for key,n in protected.items()):
        return ("items_reserved_by_infrastructure",)
    return ()


def command_blockers(operations, command):
    """Recheck infrastructure mutations against authoritative current telemetry."""
    from src.execution.commands import CommandType as C
    kinds = {C.DEPLOY_SCUT_RELAY, C.MANNY_ACTIVATE_RELAY, C.MANNY_INSTALL_BEACON, C.MANNY_LOAD_HUB_OUTPUT}
    hub_delivery = command.type == C.MANNY_DETACH_STORAGE_CONTAINER and command.metadata.get("hubCampaign")
    resupply_slot = command.type == C.MANNY_DETACH_STORAGE_CONTAINER and command.metadata.get("resupplySlot")
    if command.type not in kinds and not hub_delivery and not resupply_slot:
        return ()
    blockers = []
    current = operations.travel.current_sector()
    if current != coordinates(command.metadata.get("expectedSector")):
        blockers.append("infrastructure_wrong_sector")
    rows = role_rows(getattr(operations, "data_engine", None))
    row = next((r for r in rows if str(r["asset_id"]) == str(command.probe_id)), None)
    if not command.metadata.get("hubReceipt") and (row is None or not row["settings"].get("infrastructureEnabled")):
        blockers.append("infrastructure_role_disabled")
    elif row and command.metadata.get("hubCampaign") and row["role"] != "hub":
        blockers.append("infrastructure_role_changed")
    elif row and command.metadata.get("relayCampaign") and row["role"] != "relay_placement":
        blockers.append("infrastructure_role_changed")
    if resupply_slot:
        from src.operations.hub_receiving import empty_container
        settings = row["settings"] if row else {}
        state = settings.get("infrastructureCampaign") or {}
        if (not row or row["role"] != "relay_placement" or not state.get("supplyRequest")
                or not state.get("returning") or coordinates(settings.get("home")) != current
                or str(command.payload.get("containerId")) != str(state.get("resupplySlotContainer"))
                or command.payload.get("mode") != "drifting"
                or not empty_container(operations, str(command.payload.get("containerId")))):
            blockers.append("resupply_slot_container_unavailable")
    if row and command.metadata.get("relayCampaign"):
        state = row["settings"].get("infrastructureCampaign") or {}
        if coordinates(state.get("target")) != current:
            blockers.append("relay_site_changed")
        if command.type == C.DEPLOY_SCUT_RELAY and str(state.get("itemId")) != str(command.payload.get("itemId")):
            blockers.append("relay_kit_changed")
        if command.type in {C.MANNY_ACTIVATE_RELAY, C.MANNY_INSTALL_BEACON} and str(state.get("relayId")) != str(command.payload.get("relayId")):
            blockers.append("relay_target_changed")
    items = inventory_items(operations)
    available = stock(operations)
    claims = assembly_claims(operations)
    outgoing = {}
    if not command.metadata.get("hubReceipt"):
        if command.type in {C.MANNY_LOAD_HUB_OUTPUT, C.DEPLOY_SCUT_RELAY}:
            item = next((i for i in items if str(i.get("id")) == str(command.payload.get("itemId"))), {})
            outgoing[item.get("type")] = int(item.get("quantity", 1))
        elif command.type == C.MANNY_ACTIVATE_RELAY:
            outgoing = {"integrated_circuit":1}
        elif command.type == C.MANNY_INSTALL_BEACON:
            outgoing = {"scut_transit_beacon":1}
        elif hub_delivery:
            for item in items:
                if str((item.get("container") or {}).get("id")) == str(command.payload.get("containerId")):
                    outgoing[item["type"]] = outgoing.get(item["type"], 0)+int(item.get("quantity",1))
    if any(available.get(k,0)-n < claims.get(k,0) for k,n in outgoing.items() if claims.get(k,0)):
        blockers.append("items_reserved_by_probe_assembly")
    if command.type == C.DEPLOY_SCUT_RELAY:
        if not has_star(operations.world.sector):
            blockers.append("relay_requires_star")
        item = next((i for i in items if str(i.get("id")) == str(command.payload.get("itemId"))), None)
        if item is None or item.get("type") != "scut_relay":
            blockers.append("relay_item_unavailable")
    if command.type in {C.MANNY_ACTIVATE_RELAY, C.MANNY_INSTALL_BEACON}:
        relay = local_relays(operations).get(str(command.payload.get("relayId")))
        if relay is None:
            blockers.append("relay_unavailable")
        elif command.type == C.MANNY_ACTIVATE_RELAY:
            if relay.get("status") == "on" or not has_star(operations.world.sector):
                blockers.append("relay_not_activatable")
            if available.get("integrated_circuit", 0) < 1:
                blockers.append("relay_circuit_missing")
        else:
            if relay.get("status") != "on" or relay.get("isTransitBeacon", relay.get("hasTransitBeacon", False)):
                blockers.append("relay_not_beacon_ready")
            if available.get("scut_transit_beacon", 0) < 1:
                blockers.append("relay_beacon_missing")
    if command.type == C.MANNY_LOAD_HUB_OUTPUT and command.metadata.get("hubCleanup"):
        expected = HubCampaignService(operations).decide(row["settings"], rows) if row else InfrastructureDecision("", "")
        if not any(t.action == "Clear Hub Container" and t.metadata.get("storageMove") == command.payload
                   and t.idempotency_scope == command.metadata.get("idempotencyScope") for t in expected.tasks):
            blockers.append("hub_cleanup_changed")
        if str(command.target_id) == str(command.payload.get("targetMannyId")):
            blockers.append("hub_cleanup_actor_is_cargo")
    elif command.type == C.MANNY_LOAD_HUB_OUTPUT:
        item = next((i for i in items if str(i.get("id")) == str(command.payload.get("itemId"))), None)
        container = next((c for c in operations.world.probe.get("inventory", {}).get("containers", [])
                          if str(c["id"]) == str(command.payload.get("toContainerId"))), None)
        if not item or item.get("type") in {"manny", "additional_container"} or item.get("currentTask"):
            blockers.append("hub_item_unavailable")
        elif not container or operations.containers.free_capacity(container) + 0.00001 < float(item.get("containerSpace", 0) or 0):
            blockers.append("hub_container_capacity")
        if item and str((item.get("container") or {}).get("id")) == str(command.payload.get("toContainerId")):
            blockers.append("hub_item_already_loaded")
    if hub_delivery:
        if row:
            expected = HubCampaignService(operations).decide(row["settings"], rows)
            if not any(t.action == "Deliver Hub Container" and t.target == command.payload.get("containerId")
                       and t.metadata.get("objectId") == command.payload.get("objectId") for t in expected.tasks):
                blockers.append("hub_delivery_changed")
    return tuple(blockers)


def validate_settings(role, settings):
    if not settings.get("infrastructureEnabled"):
        return
    if role == "relay_placement":
        home = coordinates(settings.get("home"))
        if home is None:
            raise ValueError("Home requires valid FCC sector coordinates (even X+Y+Z).")
        if settings.get("expansionMode", "auto") not in {"auto", "signal", "direction"}:
            raise ValueError("Choose automatic, signal, or coordinate expansion.")
        if settings.get("expansionMode") == "direction":
            direction = coordinates(settings.get("direction"))
            if direction is None or direction == home:
                raise ValueError("Set valid direction coordinates different from home.")
        if settings.get("beaconMode", "final") not in {"final", "every", "none"}:
            raise ValueError("Choose final-relay, every-relay, or no beacons.")
        if not 1 <= int(settings.get("relayStock", 4)) <= 20:
            raise ValueError("Relay restock quantity must be between 1 and 20.")
        if settings.get("refillBeacons", settings.get("beaconMode", "final") != "none"):
            if not 1 <= int(settings.get("beaconStock", 1)) <= 20:
                raise ValueError("Beacon restock quantity must be between 1 and 20.")
    for request in manual_packages(settings) if role == "hub" else ():
        if not request.get("id"):
            raise ValueError("Choose an output receiver.")
        probe_id(request.get("targetProbeId"))
        if not request.get("items") or any(k in {"manny", "additional_container"} for k in request["items"]):
            raise ValueError("Choose a positive crafted-item quantity for the output batch.")
        for amount in request["items"].values():
            probe_id(amount)


def assembly_claims(operations):
    engine = getattr(operations, "data_engine", None)
    if engine is None or not hasattr(engine, "path"):
        return {}
    from src.planner.desired_state_store import DesiredStateStore
    from src.planner.rules.fleet import plan
    desired = DesiredStateStore(engine).load(operations.world.probe["id"])
    if not desired.fleet:
        return {}
    claims = {}
    for task in plan(operations, desired):
        for component, amount in task.reserved_items:
            claims[component] = max(claims.get(component, 0), amount)
    return claims
