"""Receiver-side unloading and return of temporary Hub delivery containers."""

from dataclasses import replace
import json
import time
from datetime import datetime

from src.operations.infrastructure import coordinates, point, inventory_items, InfrastructureDecision
from src.operations.mission import Operation, OperationStep, OperationState, OperationStore
from src.planner.task import Task


def receipts(engine, probe_id=None):
    if engine is None or not hasattr(engine, "operation_records"):
        return ()
    return tuple(op for op in OperationStore(engine).all(OperationState.ACTIVE)
                 if op.objective == "hub_container_receipt" and op.state == OperationState.ACTIVE
                 and (probe_id is None or op.probe_id == probe_id))


def readiness(engine, probe_id):
    if engine is None or not hasattr(engine, "get_preference"):
        return {}
    try:
        value = json.loads(engine.get_preference(f"hub_receiving:{probe_id}", "{}"))
        if time.time() - value.get("at", 0) <= 120:
            return value
    except (TypeError, ValueError):
        pass
    return {}


def publish_live_readiness(engine, probe, hazard_context=None):
    """Publish one coherent live receiver observation, including its upgrades."""
    from types import SimpleNamespace
    from src.operations.containers import ContainerService
    from src.safety.travel import TravelSafetyService
    world = SimpleNamespace(probe=probe, hazard_context=hazard_context or {})
    containers = ContainerService(world)
    safety = TravelSafetyService(world, None, None)
    pending = receipts(engine, int(probe["id"]))
    incoming = {op.metadata["containerId"] for op in pending}
    sector = probe.get("sector") or {}
    where = coordinates(sector.get("relative") or sector.get("relativeCoordinates"))
    engine.set_preference(f"hub_receiving:{int(probe['id'])}", json.dumps({
        "at": time.time(), "sector": point(where) if where else None,
        "status": probe.get("status"),
        "freeCapacity": sum(containers.free_capacity(c) for c in probe["inventory"].get("containers", [])
                            if str(c.get("id")) not in incoming),
        "storageFreeCapacities": [containers.free_capacity(c) for c in probe["inventory"].get("containers", [])
                                  if c.get("id") is not None and str(c["id"]) not in incoming],
        "containerCount": safety.additional_container_count(),
        "safeLimit": max(0, safety.container_break_threshold()-1),
        "receiving": bool(pending),
    }))


def stage_receipt(engine, source_id, target_id, container_id, request_id, sector, fingerprint):
    if engine is None or not hasattr(engine, "operation_records"):
        return
    identifier = f"hub-receipt:{source_id}:{request_id}:{container_id}"
    store = OperationStore(engine)
    if store.get(identifier) is not None:
        return
    store.save(Operation(id=identifier, name="Unload Hub supply and return container",
        objective="hub_container_receipt", probe_id=int(target_id), state=OperationState.ACTIVE,
        steps=(OperationStep("Unload Hub Supply"), OperationStep("Return Hub Container")),
        metadata={"sourceProbeId":source_id, "containerId":container_id, "sector":sector,
                  "handoffFingerprint":fingerprint, "received":False}))


class HubReceivingService:
    def __init__(self, operations):
        self.operations = operations
        self.engine = getattr(operations, "data_engine", None)

    def reconcile(self):
        if self.engine is None or not hasattr(self.engine, "operation_records"):
            return InfrastructureDecision("", "")
        probe_id = self.operations.world.probe["id"]
        current = self.operations.travel.current_sector()
        pending = receipts(self.engine, probe_id)
        incoming_ids = {op.metadata["containerId"] for op in pending}
        containers = self.operations.world.probe.get("inventory", {}).get("containers", [])
        storage = [c for c in containers if str(c.get("id")) not in incoming_ids]
        free = sum(self.operations.containers.free_capacity(c) for c in storage)
        count = self.operations.travel_safety.additional_container_count()
        safe_limit = max(0, self.operations.travel_safety.container_break_threshold()-1)
        snapshot = getattr(self.operations.world, "snapshot", None) or {}
        observed_at = time.time() - float(snapshot.get("age_seconds", 0) or 0)
        if snapshot.get("last_refresh"):
            try:
                observed_at = datetime.strptime(snapshot["last_refresh"], "%Y-%m-%d %H:%M:%S").timestamp()
            except (TypeError, ValueError):
                observed_at = 0
        if snapshot.get("fresh") is False:
            observed_at = 0
        self.engine.set_preference(f"hub_receiving:{probe_id}", json.dumps({
            "at":observed_at, "sector":point(current) if current else None,
            "status":self.operations.world.probe.get("status"),
            "freeCapacity":free, "containerCount":count, "safeLimit":safe_limit,
            "storageFreeCapacities":[self.operations.containers.free_capacity(c) for c in storage if c.get("id") is not None],
            "receiving":bool(pending),
        }))
        if not pending:
            return InfrastructureDecision("", "")
        op = pending[0]
        data = dict(op.metadata)
        container_id = data["containerId"]
        from src.operations.infrastructure import role_rows
        source = next((r for r in role_rows(self.engine) if str(r["asset_id"]) == str(data["sourceProbeId"])), None)
        if (not data.get("received") and source is not None
                and (source["role"] != "hub" or not source["settings"].get("infrastructureEnabled"))
                and not self.engine.action_was_successful(data["handoffFingerprint"])):
            OperationStore(self.engine).save(replace(op, state=OperationState.CANCELLED))
            return InfrastructureDecision("receipt_cancelled", "Unsent Hub delivery cancelled; receiver is released.")
        if current != coordinates(data["sector"]):
            return InfrastructureDecision("receipt_hold", "Return to the Hub sector to unload and return its delivery container.")
        attached = {str(c["id"]):c for c in self.operations.containers.attached()}
        if container_id not in attached:
            if data.get("received") and data.get("returnFingerprint") and self.engine.action_was_successful(data["returnFingerprint"]):
                OperationStore(self.engine).save(replace(op, state=OperationState.COMPLETED))
                return InfrastructureDecision("receipt_complete", "Empty Hub container returned for recovery.")
            return InfrastructureDecision("receipt_wait", "Waiting for the Hub container handoff to appear in live inventory.")
        if not data.get("received"):
            data["received"] = True
            op = replace(op, metadata=data)
            OperationStore(self.engine).save(op)
        items = [i for i in inventory_items(self.operations) if str((i.get("container") or {}).get("id")) == container_id]
        metadata = {"hubReceipt":op.id, "expectedSector":data["sector"]}
        if items:
            for item in sorted(items, key=lambda i: float(i.get("containerSpace",0) or 0), reverse=True):
                if item.get("currentTask") or item.get("type") in {"manny", "additional_container"}:
                    continue
                size = float(item.get("containerSpace", 0) or 0)
                target = min((c for c in storage if c.get("id") is not None and self.operations.containers.free_capacity(c) + .00001 >= size),
                             key=self.operations.containers.free_capacity, default=None)
                if target:
                    task = Task(action="Unload Hub Supply", category="infrastructure", priority=1, target=str(item["id"]),
                        reason="Move supplied stock into the receiving probe's own storage.", workflow_authorized=True,
                        idempotency_scope=op.id+":unload:"+str(item["id"]),
                        metadata={**metadata,"toContainerId":str(target["id"])})
                    return InfrastructureDecision("unloading_supply", task.reason, tasks=(task,))
            return InfrastructureDecision("receipt_capacity_hold", "Not enough permanent storage to unload this supply container; free space before continuing.")
        if not empty_container(self.operations, container_id):
            return InfrastructureDecision("receipt_empty_wait", "Waiting for authoritative empty-container telemetry before returning it.")
        task = Task(action="Return Hub Container", category="infrastructure", priority=1, target=container_id,
                    reason="Jettison the emptied temporary container for the Hub to recover.", workflow_authorized=True,
                    idempotency_scope=op.id+":return", metadata={**metadata,"mode":"drifting"})
        from src.execution.commands import Command, CommandType
        data["returnFingerprint"] = Command(CommandType.MANNY_DETACH_STORAGE_CONTAINER,probe_id,
            {"containerId":container_id,"mode":"drifting"},task.reason,1,
            metadata={**task.metadata,"idempotencyScope":task.idempotency_scope}).fingerprint
        OperationStore(self.engine).save(replace(op, metadata=data))
        return InfrastructureDecision("returning_container",task.reason,tasks=(task,))


def cargo_fits_storage(items, ready):
    """Conservative best-fit placement into permanent receiver storage only."""
    capacities = list(ready.get("storageFreeCapacities") or [])
    if not capacities:
        return False
    for item in sorted(items, key=lambda i: float(i.get("containerSpace",0) or 0), reverse=True):
        size = float(item.get("containerSpace",0) or 0)
        candidates = [i for i, free in enumerate(capacities) if free + .00001 >= size]
        if not candidates:
            return False
        slot = min(candidates, key=lambda i: capacities[i])
        capacities[slot] -= size
    return True


def empty_container(operations, container_id):
    container = next((c for c in operations.containers.attached() if str(c["id"]) == container_id), None)
    if container is None or float(container.get("usedCapacity", container.get("used", -1))) != 0:
        return False
    if any(str((i.get("container") or {}).get("id")) == container_id for i in inventory_items(operations)):
        return False
    if any(str((m.get("container") or {}).get("id")) == container_id for m in operations.world.mannies.get("mannies", [])):
        return False
    return not any(str((p.get("container") or {}).get("id")) == container_id and float(p.get("amount", 0)) > 0
                   for r in operations.world.probe.get("inventory", {}).get("resourceStocks", []) for p in r.get("containers", []))


def receipt_blockers(operations, command):
    from src.execution.commands import CommandType as C
    pending = receipts(getattr(operations, "data_engine", None), command.probe_id)
    if command.type == C.MOVE_PROBE and pending:
        return ("hub_container_return_pending",)
    identifier = command.metadata.get("hubReceipt")
    if not identifier:
        return ()
    op = next((op for op in pending if op.id == identifier), None)
    if op is None or operations.travel.current_sector() != coordinates(op.metadata["sector"]):
        return ("hub_receipt_unavailable",)
    if command.type == C.MANNY_DETACH_STORAGE_CONTAINER:
        if command.payload.get("containerId") != op.metadata["containerId"] or command.payload.get("mode") != "drifting" or not empty_container(operations,op.metadata["containerId"]):
            return ("hub_return_container_not_empty",)
    elif command.type == C.MANNY_LOAD_HUB_OUTPUT:
        item = next((i for i in inventory_items(operations) if str(i.get("id")) == str(command.payload.get("itemId"))), {})
        if str((item.get("container") or {}).get("id")) != op.metadata["containerId"] or command.payload.get("toContainerId") in {p.metadata["containerId"] for p in pending}:
            return ("hub_receipt_item_changed",)
    return ()
